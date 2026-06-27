"""
DataOS — Market Data Agent. STUB. Not yet implemented.

DataOS is the read-only data backbone of the ClawOps system.
It publishes clean, structured market data to the rest of the agent crew.
It never signals, never sizes, never orders.

Core responsibilities:
  - 1-min bar stream (Webull MQTT) → aggregated into 2-min and 15-min bars for Signaos
  - Live VWAP (computed in-agent: cumsum(price*volume) / cumsum(volume) from session open)
  - Session reference levels: OR high/low, prior day high/low, premarket high/low
  - Live options chain at signal time: bid/ask, IV, delta, open interest per strike

Split consideration (see notes below):
  DataOS currently covers both price data and options data.
  These may be split into two agents if the message volume is too high:
    DataOS-Price  → bars, VWAP, session levels (low-latency, always-on)
    DataOS-Options → options chain (fetched on-demand at signal time only)

TODO once Webull production API key is active:
  - Confirm exact market data endpoints against the live account
    (get_history_bar confirmed for 1-min bars; options chain endpoint shape TBD)
  - Decide: HTTP polling vs MQTT streaming for the bar feed
  - Implement bar aggregation: 2-min and 15-min from 1-min natively
  - Implement VWAP calculation from session open
  - Implement options chain fetch with delta/OI/spread filters

Interface DataOS must satisfy (Signaos + Strategist depend on this shape):

    def get_bars(timeframe_minutes: int, limit: int) -> list[dict]
    def get_latest_bar(timeframe_minutes: int) -> dict | None
    def get_vwap() -> float | None
    def get_session_levels() -> dict
        # returns: or_high, or_low, pdh, pdl, premarket_high, premarket_low
    def get_options_chain(symbol: str, expiration: str) -> list[dict]
        # returns: strike, expiration, direction, bid, ask, iv, delta, open_interest

Webull API notes (confirmed June 2026):
  - VWAP is NOT a precomputed field from Webull — compute it here from 1-min bars.
  - Options orders only support LIMIT type. No MARKET, no trailing stop.
  - UAT environment uses a shared test account — do not rely on its order/position state.
  - MQTT Data Streaming API for real-time quotes (preferred for bar feed latency).
"""


class DataOS:
    def __init__(self, symbol: str):
        self.symbol = symbol
        raise NotImplementedError(
            "DataOS not yet built — pending Webull production API key "
            "and confirmation of options chain endpoint shape."
        )

    def get_bars(self, timeframe_minutes: int, limit: int) -> list:
        raise NotImplementedError

    def get_latest_bar(self, timeframe_minutes: int):
        raise NotImplementedError

    def get_vwap(self):
        raise NotImplementedError

    def get_session_levels(self) -> dict:
        raise NotImplementedError

    def get_options_chain(self, symbol: str, expiration: str) -> list:
        raise NotImplementedError
