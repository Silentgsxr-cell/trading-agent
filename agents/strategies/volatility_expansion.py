"""
Volatility Expansion Strategy.

Active window : full session (9:30 – 16:00 ET)
Signal cap    : 3 per session

Purpose:
  Identify when options are becoming attractive due to a volatility regime
  change — either IV is cheap before a catalyst (buy vol) or price is
  breaking out of a compression pattern (momentum play with expanding range).

Two modes:

  Mode 1 — Compression Breakout:
    Price has been in a tight range (low ATR relative to 20-day avg).
    ATR begins expanding — range per bar is growing.
    Volume confirms the expansion (not just random noise).
    → Potential for a directional move; options become attractive.

  Mode 2 — IV Dislocation (options-specific):
    IV is notably low relative to 30-day HV (historical vol).
    Upcoming catalyst known (earnings, FOMC, delivery report).
    → Long vol / long straddle or strangle setup.
    This mode is direction-agnostic — direction = "neutral" is valid here.

Inputs needed:
  - ATR (true range history): computable from bars available now
  - IV data: requires options chain from Data Agent (not yet built)
  - 30-day historical volatility: requires longer price history
  - Upcoming catalyst calendar: requires external feed

Phase 1 (when Data Agent provides bars):
  ATR-based compression detection is implementable immediately.
  IV-based mode is blocked on options chain data.

Compression detection logic (draft):
  1. Compute ATR(14) from 2-min bars.
  2. Compare to ATR average over last 3 sessions (rolling baseline).
  3. If current ATR < 0.7x baseline for >= 10 consecutive bars: compression.
  4. On first bar that breaks the compression range with >1.5x volume: signal.
  5. Direction: long if breakout is up, short if breakout is down.
"""

from datetime import time
from typing import Optional

from .base import BaseStrategy, EvalContext, SignalOutput

_SESSION_OPEN  = time(9, 30)
_SESSION_CLOSE = time(16, 0)


class VolatilityExpansionStrategy(BaseStrategy):
    name        = "VolatilityExpansion"
    max_signals = 3
    window      = (_SESSION_OPEN, _SESSION_CLOSE)

    def update(self, context: EvalContext) -> Optional[SignalOutput]:
        raise NotImplementedError(
            "VolatilityExpansionStrategy not yet implemented. "
            "ATR compression mode: implementable once multi-session bar "
            "history is available from Data Agent. "
            "IV mode: blocked on options chain data."
        )

    def reset_session(self) -> None:
        super().reset_session()
