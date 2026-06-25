"""
Risk engine configuration — locked values.

These are the hard rules. Nothing in the agent stack is allowed to override
these at runtime. Changing these requires a manual edit + redeploy, not a
decision made by any agent (including the signal/strategist agents).
"""

# Paper account starting balance. Mirrors real $1,000 account so the
# percentages below actually mean something.
STARTING_BALANCE = 1000.00

# Per-trade risk: max % of CURRENT equity risked on a single trade.
# Recalculated against current balance after every trade, not the
# original starting balance.
PER_TRADE_RISK_PCT = 0.01  # 1%

# Daily circuit breaker: halts all NEW entries for the rest of the
# session once hit. Does not force-close existing positions early —
# existing positions still respect their own stop/time-exit rules.
DAILY_MAX_LOSS_PCT = 0.03  # 3%

# Max number of trades allowed to be opened in a single session.
MAX_TRADES_PER_DAY = 3

# Number of consecutive losing trades that triggers a mandatory
# cooldown before the next entry is allowed, even if the daily loss
# cap hasn't been hit yet.
CONSECUTIVE_LOSS_COOLDOWN = 2

# Max simultaneous live positions in the underlying while the system
# is still being proven out.
MAX_CONCURRENT_POSITIONS = 1

# --- Exit rules (0DTE / weekly options) ---

# Premium-percentage stop: close the position if it's down this % from
# entry premium. This is the price-based half of the dual exit — does
# NOT rely on a resting stop order actually filling at a price, since
# 0DTE spreads can gap.
PREMIUM_STOP_PCT = 0.50  # placeholder — confirm with Silent before first paper run

# Hard time-based force-close. Independent of price. Minutes before
# market close (16:00 ET) at which any open position gets flattened
# regardless of P&L. This is what makes "ran it to end of day" structurally
# impossible.
FORCE_CLOSE_MINUTES_BEFORE_CLOSE = 30  # placeholder — confirm with Silent

# --- Options selection filters ---

OPTION_DELTA_MIN = 0.35
OPTION_DELTA_MAX = 0.55

# Liquidity floor — reject strikes below this open interest.
OPTION_MIN_OPEN_INTEREST = 500  # placeholder — confirm with Silent

# Reject strikes where bid-ask spread exceeds this % of the premium.
OPTION_MAX_SPREAD_PCT = 0.10  # placeholder — confirm with Silent
