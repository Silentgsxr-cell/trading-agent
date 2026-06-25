"""
ORB strategy configuration — locked values.
"""

# Primary signal timeframe (minutes per bar)
SIGNAL_TIMEFRAME_MIN = 2

# Context timeframe for trend/regime alignment (minutes per bar)
CONTEXT_TIMEFRAME_MIN = 15

# Opening range window: marks OR high/low from session open.
# 9:30-10:00 ET.
OR_START_TIME = "09:30"
OR_DURATION_MIN = 30

# Trade window: signal agent only emits NEW candidates within this
# window from session open. No new signals after this even if a
# breakout happens later. 9:30-11:00 ET (first 90 minutes total,
# including the OR window itself).
TRADE_WINDOW_DURATION_MIN = 90

# --- Volume confirmation rule ---
# Breakout candle must close beyond OR high/low AND:
VOLUME_LOOKBACK_BARS = 20          # rolling average window, on SIGNAL_TIMEFRAME_MIN bars
VOLUME_MULTIPLIER = 1.5            # breakout candle volume must exceed avg * this
MIN_BODY_RATIO = 0.6               # candle body must cover >= this fraction of full range
                                    # (filters wick-only pokes through the OR boundary)

# Underlying symbol for this strategy instance
SYMBOL = "TSLA"
