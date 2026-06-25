"""
Data Agent — STUB. Not yet implemented.

Responsibility (read-only, never decides anything):
  - Publish clean SIGNAL_TIMEFRAME_MIN bars (2-min) for the signal agent
  - Publish CONTEXT_TIMEFRAME_MIN bars (15-min) for trend/regime context
  - Compute and publish live VWAP (Webull does not appear to expose this
    as a precomputed field — compute from cumulative price*volume /
    cumulative volume from session open, using the 1-min bars)
  - Publish opening range, prior day high/low, premarket high/low as
    fixed session reference levels
  - Publish live options chain (bid/ask, IV, delta, open interest) at
    signal time for the strategist/strike-selection step

TODO once Webull production API key is active:
  - Confirm exact market data endpoints in account once approved
    (webull-openapi-python-sdk: data_client.market_data.get_history_bar
    confirmed for 1-min bars; need to confirm options chain endpoint
    shape directly against the real account, docs were unclear)
  - Decide HTTP polling vs MQTT streaming for the 2-min feed
  - Implement VWAP calculation
  - Implement bar aggregation if Webull only gives 1-min natively
    (2-min and 15-min would then be built by aggregating 1-min bars
    in this agent, not pulled directly)

Interface this agent must satisfy (so signal_agent.py doesn't need to
change when this gets filled in):

    def get_latest_bar(timeframe_minutes: int) -> dict | None
    def get_vwap() -> float | None
    def get_session_levels() -> dict   # or_high, or_low, pdh, pdl, premarket_high, premarket_low
    def get_options_chain(symbol: str, expiration: str) -> list[dict]
"""


class DataAgent:
    def __init__(self, symbol: str):
        self.symbol = symbol
        raise NotImplementedError(
            "Data Agent not yet built — pending Webull production API key "
            "and confirmation of options chain endpoint shape."
        )
