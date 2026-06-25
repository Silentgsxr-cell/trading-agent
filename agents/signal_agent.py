"""
ORB Signal Agent.

Read-only with respect to trading: this agent only emits candidate
signals. It never sizes positions and never touches an order. Risk
Engine has final say on every candidate this emits.

Input: a stream of completed bars for SIGNAL_TIMEFRAME_MIN, each bar:
    {
        "timestamp": datetime,
        "open": float, "high": float, "low": float, "close": float,
        "volume": int,
    }
This agent does not fetch data itself — that's the Data Agent's job
(not yet built). For now it accepts bars passed in, so it can be
tested against historical/replay data independently.

Output signal shape:
    {
        "symbol": str,
        "direction": "long" | "short",
        "entry_trigger": float,   # breakout close price
        "or_high": float,
        "or_low": float,
        "volume_ratio": float,    # breakout volume / rolling avg
        "body_ratio": float,
        "timestamp": datetime,
    }
"""

from datetime import datetime, time, timedelta
from typing import Optional

from config import strategy_config as cfg


def _time_of(bar: dict) -> time:
    return bar["timestamp"].time()


class ORBSignalAgent:
    def __init__(self, symbol: str = cfg.SYMBOL):
        self.symbol = symbol
        self.bars: list[dict] = []
        self.or_high: Optional[float] = None
        self.or_low: Optional[float] = None
        self.or_locked = False
        self.signal_emitted_today = False

        self._or_start = datetime.strptime(cfg.OR_START_TIME, "%H:%M").time()
        self._or_end = (
            datetime.combine(datetime.today(), self._or_start)
            + timedelta(minutes=cfg.OR_DURATION_MIN)
        ).time()
        self._trade_window_end = (
            datetime.combine(datetime.today(), self._or_start)
            + timedelta(minutes=cfg.TRADE_WINDOW_DURATION_MIN)
        ).time()

    def reset_session(self):
        self.bars = []
        self.or_high = None
        self.or_low = None
        self.or_locked = False
        self.signal_emitted_today = False

    def on_bar(self, bar: dict) -> Optional[dict]:
        """
        Feed one completed bar in. Returns a signal dict if this bar
        qualifies as a confirmed ORB breakout, else None.
        """
        self.bars.append(bar)
        bar_time = _time_of(bar)

        # Still inside the opening range window: update OR high/low, no signals.
        if self._or_start <= bar_time < self._or_end:
            self.or_high = bar["high"] if self.or_high is None else max(self.or_high, bar["high"])
            self.or_low = bar["low"] if self.or_low is None else min(self.or_low, bar["low"])
            return None

        # OR window just closed — lock it in.
        if not self.or_locked and self.or_high is not None:
            self.or_locked = True

        if not self.or_locked:
            # No OR established yet (e.g. gap in data) — can't evaluate breakouts.
            return None

        # Outside the trade window: no new signals, even on a valid breakout.
        if bar_time >= self._trade_window_end:
            return None

        if self.signal_emitted_today:
            # Stage 1 build: one signal per session, max one concurrent
            # position anyway per risk engine. Revisit if multi-entry
            # per day is ever wanted.
            return None

        return self._check_breakout(bar)

    def _check_breakout(self, bar: dict) -> Optional[dict]:
        direction = None
        if bar["close"] > self.or_high:
            direction = "long"
        elif bar["close"] < self.or_low:
            direction = "short"
        else:
            return None

        volume_ratio = self._volume_ratio(bar)
        if volume_ratio is None or volume_ratio < cfg.VOLUME_MULTIPLIER:
            return None

        body_ratio = self._body_ratio(bar)
        if body_ratio < cfg.MIN_BODY_RATIO:
            return None

        self.signal_emitted_today = True
        return {
            "symbol": self.symbol,
            "direction": direction,
            "entry_trigger": bar["close"],
            "or_high": self.or_high,
            "or_low": self.or_low,
            "volume_ratio": round(volume_ratio, 2),
            "body_ratio": round(body_ratio, 2),
            "timestamp": bar["timestamp"],
        }

    def _volume_ratio(self, bar: dict) -> Optional[float]:
        lookback = self.bars[-(cfg.VOLUME_LOOKBACK_BARS + 1):-1]
        if len(lookback) < cfg.VOLUME_LOOKBACK_BARS:
            return None  # not enough history yet this session
        avg_volume = sum(b["volume"] for b in lookback) / len(lookback)
        if avg_volume <= 0:
            return None
        return bar["volume"] / avg_volume

    def _body_ratio(self, bar: dict) -> float:
        full_range = bar["high"] - bar["low"]
        if full_range <= 0:
            return 0.0
        body = abs(bar["close"] - bar["open"])
        return body / full_range
