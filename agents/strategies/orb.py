"""
ORB Strategy — Opening Range Breakout.

Active window : 9:30 – 11:00 ET
Signal cap    : 1 per session
Timeframe     : 2-min bars

Logic (unchanged from original signal_agent.py):
  1. Build OR high/low from 9:30–10:00 bars.
  2. Lock the range at 10:00.
  3. After lockout, watch for a bar that closes BEYOND the OR boundary.
  4. Confirm with volume ratio (>1.5x 20-bar avg) and body ratio (>=60%).
  5. Emit exactly one signal. No second entries.

Confidence formula:
  0.50 base + bonus for excess volume + bonus for strong body.
  Capped at 1.0.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from config import strategy_config as cfg

from .base import BaseStrategy, EvalContext, SignalOutput

_OR_START   = datetime.strptime(cfg.OR_START_TIME, "%H:%M").time()
_OR_END     = (
    datetime.combine(datetime.today(), _OR_START)
    + timedelta(minutes=cfg.OR_DURATION_MIN)
).time()
_WINDOW_END = (
    datetime.combine(datetime.today(), _OR_START)
    + timedelta(minutes=cfg.TRADE_WINDOW_DURATION_MIN)
).time()


class ORBStrategy(BaseStrategy):
    name        = "ORB"
    max_signals = 1
    window      = (_OR_START, _WINDOW_END)

    def __init__(self) -> None:
        super().__init__()
        self._or_high:  Optional[float]    = None
        self._or_low:   Optional[float]    = None
        self._or_locked: bool              = False

    def reset_session(self) -> None:
        super().reset_session()
        self._or_high   = None
        self._or_low    = None
        self._or_locked = False

    def update(self, context: EvalContext) -> Optional[SignalOutput]:
        if not self.can_signal():
            return None
        for bar in context.new_bars:
            result = self._on_bar(bar, context.bars)
            if result:
                return self._emit(result)
        return None

    # ------------------------------------------------------------------

    def _on_bar(self, bar: dict, all_bars: List[dict]) -> Optional[SignalOutput]:
        t = bar["timestamp"].time()

        # Inside OR window — just track the range.
        if _OR_START <= t < _OR_END:
            self._or_high = (
                bar["high"] if self._or_high is None else max(self._or_high, bar["high"])
            )
            self._or_low = (
                bar["low"] if self._or_low is None else min(self._or_low, bar["low"])
            )
            return None

        # First bar after OR window — lock the range in.
        if not self._or_locked and self._or_high is not None:
            self._or_locked = True

        if not self._or_locked:
            return None     # no OR data (gap in feed)

        if t >= _WINDOW_END:
            return None     # outside the signal window

        return self._check_breakout(bar, all_bars)

    def _check_breakout(self, bar: dict, all_bars: List[dict]) -> Optional[SignalOutput]:
        if bar["close"] > self._or_high:
            direction = "long"
            level     = self._or_high
            label     = "OR high"
        elif bar["close"] < self._or_low:
            direction = "short"
            level     = self._or_low
            label     = "OR low"
        else:
            return None

        vol_ratio = _volume_ratio(bar, all_bars)
        if vol_ratio is None or vol_ratio < cfg.VOLUME_MULTIPLIER:
            return None

        body = _body_ratio(bar)
        if body < cfg.MIN_BODY_RATIO:
            return None

        confidence = min(
            1.0,
            0.50
            + (vol_ratio - cfg.VOLUME_MULTIPLIER) * 0.10
            + (body - cfg.MIN_BODY_RATIO)          * 0.50,
        )

        return SignalOutput(
            strategy_name = "ORB",
            ticker        = cfg.SYMBOL,
            direction     = direction,
            confidence    = round(confidence, 3),
            reasoning     = (
                f"Breakout {'above' if direction == 'long' else 'below'} {label} "
                f"{level:.2f} — close {bar['close']:.2f}, "
                f"vol {vol_ratio:.2f}x avg, body {body:.0%}."
            ),
            risk_notes = [],
            metadata   = {
                "entry_trigger": bar["close"],
                "or_high":       self._or_high,
                "or_low":        self._or_low,
                "volume_ratio":  round(vol_ratio, 2),
                "body_ratio":    round(body, 2),
                "bar_ts":        bar["timestamp"].isoformat(),
            },
        )


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def _volume_ratio(bar: dict, all_bars: List[dict]) -> Optional[float]:
    lookback = all_bars[-(cfg.VOLUME_LOOKBACK_BARS + 1):-1]
    if len(lookback) < cfg.VOLUME_LOOKBACK_BARS:
        return None
    avg = sum(b["volume"] for b in lookback) / len(lookback)
    return bar["volume"] / avg if avg > 0 else None


def _body_ratio(bar: dict) -> float:
    full = bar["high"] - bar["low"]
    return abs(bar["close"] - bar["open"]) / full if full > 0 else 0.0
