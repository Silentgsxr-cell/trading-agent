"""
Execution Agent — STUB. Not yet implemented.

Responsibility: the ONLY agent allowed to submit, modify, or cancel a
real order. Never calculates position size or decides direction —
both arrive pre-approved from the Risk Engine. Paper mode only until
Silent explicitly approves a move to live.

Known platform constraints to design around (confirmed from Webull
OpenAPI docs):
  - Options orders only support order_type LIMIT. No MARKET, no
    TRAILING_STOP_LOSS for options. This means the premium-stop and
    time-based force-close in risk_engine.py cannot rely on a resting
    stop order sitting on the book — this agent must actively detect
    the trigger (poll current premium / clock) and fire a marketable
    limit order itself when triggered.
  - Two environments: UAT (test) and prod, swapped via endpoint config.
    UAT shared credentials connect to a PUBLICLY SHARED test account —
    do not treat UAT order/position state as this system's paper
    trading record of truth. Paper trading state should be tracked in
    this system's own database, with UAT used only to verify API
    plumbing works.
  - Webull's own "Agent Skills" CLI already implements symbol
    whitelist, max order notional, and max order quantity guardrails.
    Consider reusing that pattern as a second backstop layer here,
    independent of risk_engine.py.

TODO:
  - Decide: build directly on webull-openapi-python-sdk, or shell out
    to webull-agent-skills CLI for the actual order calls
  - Implement marketable-limit logic for force-close (what price
    offset from current bid/ask counts as "marketable enough to fill
    fast" without giving away unnecessary edge)
  - Implement order confirmation / fill polling
  - Wire to Risk Engine: this agent must REJECT any order request that
    didn't come from a Risk Engine approval, no exceptions

Interface this agent must satisfy:

    def submit_order(approved_trade: dict) -> dict   # returns order_id, status
    def force_close(position_id: str) -> dict
    def get_fill_status(order_id: str) -> dict
"""


class ExecutionAgent:
    def __init__(self, environment: str = "uat"):
        self.environment = environment
        raise NotImplementedError(
            "Execution Agent not yet built — pending Webull production API "
            "key and decision on SDK vs Agent Skills CLI approach."
        )
