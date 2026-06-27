"""
Pullback Strategy.

Active window : full session (9:30 – 16:00 ET)
Signal cap    : 3 per session

Purpose:
  Find better entries on trending names.
  Rather than buying a breakout, wait for price to pull back into a
  key level (VWAP, prior OR high/low, EMA support) and confirm a
  stabilization before re-entering.

Classic setup example:
  TSLA trending up after an ORB breakout.
  Price retraces into VWAP or the old OR high (now support).
  Volume contracts during the pullback (sellers drying up).
  A 2-min candle closes back above VWAP with expanding volume.
  → Long signal.

Inputs needed (not yet available — blocked on Data Agent):
  - Real-time VWAP
  - Prior OR high/low levels (passed via metadata from ORBStrategy if fired)
  - Volume trend during pullback (contraction = healthy)
  - Momentum indicator: RSI or MACD on 2-min bars

Signal criteria (draft):
  Long pullback:
    Prior trend was up (higher highs on 5-min)
    Price pulled back to VWAP or prior support level
    Volume contracted >= 2 consecutive bars during pullback
    Candle closes back above the support level with volume expansion
    RSI recovering from below 50 (not required but a strong bonus)

  Short: mirror conditions, price bouncing into resistance then rejecting.

Confidence factors:
  - How clean the pullback was (fewer bars = cleaner)
  - How close to VWAP vs a looser MA level
  - Whether volume expansion on the reversal candle is >1.3x avg
"""

from datetime import time
from typing import Optional

from .base import BaseStrategy, EvalContext, SignalOutput

_SESSION_OPEN  = time(9, 30)
_SESSION_CLOSE = time(16, 0)


class PullbackStrategy(BaseStrategy):
    name        = "Pullback"
    max_signals = 3
    window      = (_SESSION_OPEN, _SESSION_CLOSE)

    def update(self, context: EvalContext) -> Optional[SignalOutput]:
        raise NotImplementedError(
            "PullbackStrategy not yet implemented. "
            "Blocked on: live VWAP, support-level detection, "
            "volume contraction/expansion analysis across bar sequences."
        )

    def reset_session(self) -> None:
        super().reset_session()
