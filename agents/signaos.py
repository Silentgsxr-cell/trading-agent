"""
Signaos — Signal Agent Orchestrator.

Responsibilities:
  1. Maintain the strategy registry
  2. Call every active, non-capped strategy on each poll
  3. Normalize outputs to a common schema
  4. Score each signal (Technical + News + Macro + Risk)
  5. Assign conviction tier (S / A / B / C)
  6. Return ranked list to the runner

Signaos does not place orders, manage risk, or talk to brokers.
It hands ranked signals to:
  - Risk Officer (risk_engine.py)
  - Mission Control (via runner → state files)
  - Discord (when wired up)
  - Chief of Staff (when built)

Only S and A tier signals are routed to Discord by default.
All signals (including B and C) are written to state/signals.jsonl.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .strategies import (
    BaseStrategy,
    EvalContext,
    NewsCatalystStrategy,
    ORBStrategy,
    PullbackStrategy,
    RelativeStrengthStrategy,
    SignalOutput,
    TrendContinuationStrategy,
    VolatilityExpansionStrategy,
)


# ---------------------------------------------------------------------------
# Scored / ranked signal shape
# ---------------------------------------------------------------------------

@dataclass
class RankedSignal:
    signal:          SignalOutput
    technical_score: float
    news_score:      float
    macro_score:     float
    risk_score:      float
    final_score:     float
    conviction_tier: str        # "S" | "A" | "B" | "C"
    timestamp:       datetime
    notify_discord:  bool       # True for S and A tiers by default

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_name":   self.signal.strategy_name,
            "ticker":          self.signal.ticker,
            "direction":       self.signal.direction,
            "confidence":      self.signal.confidence,
            "reasoning":       self.signal.reasoning,
            "risk_notes":      self.signal.risk_notes,
            "metadata":        self.signal.metadata,
            "technical_score": self.technical_score,
            "news_score":      self.news_score,
            "macro_score":     self.macro_score,
            "risk_score":      self.risk_score,
            "final_score":     self.final_score,
            "conviction_tier": self.conviction_tier,
            "notify_discord":  self.notify_discord,
            "timestamp":       self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# Signaos
# ---------------------------------------------------------------------------

class Signaos:
    """
    The Signal Agent.

    Usage:
        signaos = Signaos()
        ranked = signaos.poll(context)   # list[RankedSignal], best first
        signaos.reset_session()          # call at daily roll-over
    """

    def __init__(self) -> None:
        self.strategies: List[BaseStrategy] = [
            ORBStrategy(),
            TrendContinuationStrategy(),
            PullbackStrategy(),
            NewsCatalystStrategy(),
            RelativeStrengthStrategy(),
            VolatilityExpansionStrategy(),
        ]

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def poll(self, context: EvalContext) -> List[RankedSignal]:
        """
        Called by the runner every poll interval.
        Returns all signals generated this tick, ranked by final_score.
        Returns an empty list if nothing qualified.
        """
        raw: List[SignalOutput] = []

        for strategy in self.strategies:
            if not strategy.is_active(context.now):
                continue
            if not strategy.can_signal():
                continue
            try:
                result = strategy.update(context)
                if result is not None:
                    raw.append(result)
            except NotImplementedError:
                pass    # stub strategy — skip silently
            except Exception as exc:
                # Don't let one broken strategy crash the loop.
                print(f"[signaos] {strategy.name} error: {exc}")

        ranked = [self._score(sig, context) for sig in raw]
        ranked.sort(key=lambda r: r.final_score, reverse=True)
        return ranked

    # ------------------------------------------------------------------
    # Introspection helpers for Mission Control / logging
    # ------------------------------------------------------------------

    def strategy_status(self, now: datetime) -> List[Dict[str, Any]]:
        """
        Returns per-strategy status for the cockpit / logs page.
        """
        statuses = []
        for s in self.strategies:
            statuses.append({
                "name":            s.name,
                "active":          s.is_active(now),
                "can_signal":      s.can_signal(),
                "signals_today":   s._signals_today,
                "max_signals":     s.max_signals,
                "window":          (
                    f"{s.window[0].strftime('%H:%M')}–{s.window[1].strftime('%H:%M')} ET"
                    if s.window else "24/7"
                ),
                "implemented":     self._is_implemented(s),
            })
        return statuses

    def reset_session(self) -> None:
        for s in self.strategies:
            s.reset_session()

    # ------------------------------------------------------------------
    # Scoring model
    # ------------------------------------------------------------------

    def _score(self, signal: SignalOutput, context: EvalContext) -> RankedSignal:
        """
        Four-component score → weighted final → conviction tier.

        Weights (must sum to 1.0):
          Technical : 0.40  (strategy's own confidence)
          News      : 0.15  (placeholder 0.5 until News Agent is built)
          Macro     : 0.25  (SPY bias alignment)
          Risk      : 0.20  (placeholder 0.8 — tightened once Risk Engine integrates)

        Tier thresholds:
          S  ≥ 0.85  — highest conviction, Discord alert
          A  ≥ 0.70  — strong setup, Discord alert
          B  ≥ 0.50  — valid but not high-conviction, logged only
          C  < 0.50  — low confidence, logged only
        """
        technical = signal.confidence

        news = 0.50     # placeholder — no live news scoring yet

        macro = _macro_score(signal.direction, context.spy_bias)

        risk = 0.80     # placeholder — Risk Engine integration pending

        final = round(
            technical * 0.40
            + news    * 0.15
            + macro   * 0.25
            + risk    * 0.20,
            3,
        )

        tier = (
            "S" if final >= 0.85 else
            "A" if final >= 0.70 else
            "B" if final >= 0.50 else
            "C"
        )

        return RankedSignal(
            signal          = signal,
            technical_score = round(technical, 3),
            news_score      = round(news, 3),
            macro_score     = round(macro, 3),
            risk_score      = round(risk, 3),
            final_score     = final,
            conviction_tier = tier,
            timestamp       = context.now,
            notify_discord  = tier in ("S", "A"),
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _is_implemented(strategy: BaseStrategy) -> bool:
        """
        Check if the strategy is live by probing update() without a
        real context — catches NotImplementedError from stubs.
        """
        try:
            # Probe with a minimal dummy context.
            dummy = EvalContext(
                now=datetime.now(), symbol="", bars=[], new_bars=[],
                news=[], spy_bias="Neutral",
            )
            strategy.update(dummy)
            return True
        except NotImplementedError:
            return False
        except Exception:
            return True   # errored for another reason — treat as implemented


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _macro_score(direction: str, spy_bias: str) -> float:
    """
    How well does SPY bias align with the trade direction?
    Aligned bias = 0.75, neutral = 0.60, opposing = 0.35.
    """
    if (spy_bias == "Bullish" and direction == "long") or \
       (spy_bias == "Bearish" and direction == "short"):
        return 0.75
    if spy_bias == "Neutral":
        return 0.60
    return 0.35   # opposing bias — not a blocker, but dampens score
