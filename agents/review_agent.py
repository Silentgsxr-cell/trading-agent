"""
Review Agent — STUB. Not yet implemented.

Responsibility: closes the daily feedback loop. Summarizes each
session — what signal fired, whether risk approved it, whether
execution matched the plan, whether rules were followed. This is
also where "self-learning" lives, scoped narrowly:

  - Tracks win rate, expectancy, and drawdown PER SETUP TYPE over time
  - Flags when a strategy's edge looks like it's decayed
  - Can adjust confidence weighting on future signals

  - CANNOT modify risk_config.py values. Any change to hard risk
    limits requires Silent's manual approval — the learning loop is
    only allowed to make the system pickier, never braver.

TODO:
  - Define daily summary schema (signal fired / risk decision / fill
    quality / rule compliance / grade) — basically the existing
    Journal tab logic from the terminal build, extended to include
    risk-engine decisions, not just manually-entered trades
  - Decide storage: flat file (CSV/JSON) vs lightweight DB. CSV is
    fine for solo paper trading volume, revisit if this scales
  - Build the win-rate/expectancy-by-setup-type rollup

Interface this agent must satisfy:

    def log_session(session: SessionState) -> None
    def get_setup_performance(setup_type: str) -> dict
    def flag_edge_decay() -> list[str]   # setup types showing degraded performance
"""


class ReviewAgent:
    def __init__(self, log_path: str = "logs/journal.csv"):
        self.log_path = log_path
        raise NotImplementedError(
            "Review Agent not yet built — spec it after execution agent "
            "so we know what real fill/order data looks like to log."
        )
