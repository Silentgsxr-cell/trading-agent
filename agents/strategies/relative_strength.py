"""
Relative Strength Strategy.

Active window : full session (9:30 – 16:00 ET)
Signal cap    : 3 per session

Purpose:
  Compare watchlist names against each other and against QQQ/SPY.
  Identify which symbol is showing the most strength (or weakness)
  relative to the overall market, then surface the strongest name
  as a high-confidence candidate.

Watchlist:
  TSLA, NVDA, AAPL, MSFT, QQQ, SPY  (from strategy_config)

Logic:
  - Compute % change from today's open for each symbol
  - Compute % change relative to SPY (alpha)
  - Rank by alpha, not raw % move
  - If a symbol is up 3% on a day SPY is flat → strong relative strength
  - If a symbol is up 1% on a day SPY is up 2% → relative weakness

Signal criteria (draft):
  Long:
    Symbol alpha vs SPY > +1.5% and accelerating (last 3 bars trending up)
    Relative volume > 1.5x (confirming real buying, not just drift)
    Price above VWAP

  Short: mirror — symbol lagging SPY by > -1.5%, below VWAP

Output includes which symbol, its alpha vs SPY, and relative volume score.

Inputs needed:
  - Multi-symbol bar data from Data Agent (currently only single-symbol)
  - VWAP per symbol (computed from session open bars)
  - Relative volume baseline per symbol

Current blocker:
  Data Agent only provides single-symbol bars (TSLA).
  Multi-symbol support must be added to the data layer first.
"""

from datetime import time
from typing import Optional

from .base import BaseStrategy, EvalContext, SignalOutput

_SESSION_OPEN  = time(9, 30)
_SESSION_CLOSE = time(16, 0)


class RelativeStrengthStrategy(BaseStrategy):
    name        = "RelativeStrength"
    max_signals = 3
    window      = (_SESSION_OPEN, _SESSION_CLOSE)

    def update(self, context: EvalContext) -> Optional[SignalOutput]:
        raise NotImplementedError(
            "RelativeStrengthStrategy not yet implemented. "
            "Blocked on: multi-symbol bar feed from Data Agent, "
            "per-symbol VWAP, relative volume baselines."
        )

    def reset_session(self) -> None:
        super().reset_session()
