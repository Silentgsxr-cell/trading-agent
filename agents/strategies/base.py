"""
Base contract every strategy must implement.

Signaos calls strategy.update(context) on every poll.
Strategies return a SignalOutput or None — never place orders, never touch money.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SignalOutput:
    """Normalized signal shape returned by every strategy."""
    strategy_name: str
    ticker:        str
    direction:     str          # "long" | "short"
    confidence:    float        # 0.0 – 1.0  (strategy's own raw estimate)
    reasoning:     str          # human-readable sentence explaining the setup
    risk_notes:    List[str] = field(default_factory=list)
    metadata:      Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalContext:
    """
    Everything a strategy might need on a given poll.
    Built by Signaos from live data and passed to every strategy.
    """
    now:         datetime
    symbol:      str
    bars:        List[dict]          # all completed 2-min bars this session
    new_bars:    List[dict]          # bars Signaos hasn't fed to strategies yet
    news:        List[dict]          # recent news items (empty until News Agent built)
    spy_bias:    str                 # "Bullish" | "Bearish" | "Neutral"
    market_data: Dict[str, Any] = field(default_factory=dict)


class BaseStrategy(ABC):
    """
    All strategies inherit from this.

    Class-level attributes to set per strategy:
      name          human-readable strategy name (str)
      max_signals   daily signal cap, None = unlimited (Optional[int])
      window        active trading window as (start, end) time tuple,
                    None = 24/7 (Optional[Tuple[time, time]])
    """
    name:        str = ""
    max_signals: Optional[int] = 1
    window:      Optional[Tuple[time, time]] = None

    def __init__(self) -> None:
        self._signals_today: int = 0

    # ------------------------------------------------------------------
    # Gate checks — Signaos calls these before calling update()
    # ------------------------------------------------------------------

    def is_active(self, now: datetime) -> bool:
        """True when this strategy's time window is currently open."""
        if self.window is None:
            return True          # 24/7 strategy (e.g. News)
        if now.weekday() >= 5:
            return False         # windowed strategies never fire on weekends
        t = now.time().replace(tzinfo=None)
        return self.window[0] <= t < self.window[1]

    def can_signal(self) -> bool:
        """True when the strategy hasn't hit its daily cap."""
        if self.max_signals is None:
            return True
        return self._signals_today < self.max_signals

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    @abstractmethod
    def update(self, context: EvalContext) -> Optional[SignalOutput]:
        """
        Called by Signaos on every poll (only when is_active and can_signal
        are both True). Return a SignalOutput if a qualifying setup is
        detected, else None.
        Always call self._emit(output) before returning so the counter ticks.
        """

    def reset_session(self) -> None:
        """Called at session roll-over (new trading day)."""
        self._signals_today = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit(self, output: SignalOutput) -> SignalOutput:
        """Register the signal (increments counter) and return it unchanged."""
        self._signals_today += 1
        return output
