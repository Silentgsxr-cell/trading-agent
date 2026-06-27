"""
Trend Continuation Strategy.

Active window : full session (9:30 – 16:00 ET)
Signal cap    : 3 per session

Purpose:
  Find stocks already trending strongly and confirm entries on pullbacks
  into strength — not chasing, but joining momentum with structure.

Inputs needed (not yet available — blocked on Data Agent / live feed):
  - VWAP (computed from 1-min bars: cumsum(price*volume) / cumsum(volume))
  - Relative volume vs 20-day average session volume
  - Higher-highs / higher-lows structure on 5-min bars
  - EMA alignment (9 EMA > 21 EMA > VWAP for long bias)
  - Trend slope (linear regression over last N bars)

Signal criteria (draft — confirm with Silent before implementing):
  Long:
    price > VWAP
    9 EMA > 21 EMA
    higher highs on 5-min
    relative volume > 1.2x session average
    current bar closes above prior high
  Short: mirror conditions

Confidence boosters:
  - Price reclaiming VWAP after a dip (not just above it)
  - Volume expanding on the continuation candle
  - SPY bias aligned with direction
"""

from datetime import time
from typing import Optional

from .base import BaseStrategy, EvalContext, SignalOutput

_SESSION_OPEN  = time(9, 30)
_SESSION_CLOSE = time(16, 0)


class TrendContinuationStrategy(BaseStrategy):
    name        = "TrendContinuation"
    max_signals = 3
    window      = (_SESSION_OPEN, _SESSION_CLOSE)

    def update(self, context: EvalContext) -> Optional[SignalOutput]:
        raise NotImplementedError(
            "TrendContinuationStrategy not yet implemented. "
            "Blocked on: live VWAP feed from Data Agent, "
            "multi-timeframe bar access (5-min + 2-min), "
            "relative volume vs historical session baseline."
        )

    def reset_session(self) -> None:
        super().reset_session()
