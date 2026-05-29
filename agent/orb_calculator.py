"""
orb_calculator.py — Opening Range Breakout (ORB) trade planner.

Strategy: the first 15-minute candle sets the range (HIGH and LOW).
  Long trade  → buy a break above the HIGH, stop below the LOW.
  Short trade → sell a break below the LOW, stop above the HIGH.

Position size is derived from dollar risk so Silent never risks more than
1% of account on a single trade.
"""

import math

# Setup validity thresholds (as % of average price in the range).
# Tune these if QQQ's typical range changes with volatility.
MIN_RANGE_PCT = 0.05   # Below this the range is too tight — no room to move
MAX_RANGE_PCT = 1.20   # Above this the risk per share is too large for a small account


def validate_range(high: float, low: float) -> tuple[bool, str, str]:
    """
    Return (is_valid, message, css_class) for a given ORB range.
    css_class is 'valid' or 'invalid' — used directly by the HTML template.
    """
    if high <= low or low <= 0:
        return False, 'High must be greater than Low.', 'invalid'

    range_size = high - low
    avg_price  = (high + low) / 2.0
    range_pct  = (range_size / avg_price) * 100

    if range_pct < MIN_RANGE_PCT:
        return False, f'Range too narrow ({range_pct:.2f}% — min is {MIN_RANGE_PCT}%). Skip this setup.', 'invalid'
    if range_pct > MAX_RANGE_PCT:
        return False, f'Range too wide ({range_pct:.2f}% — max is {MAX_RANGE_PCT}%). Risk is too large.', 'invalid'

    return True, f'Setup looks reasonable ({range_pct:.2f}% range).', 'valid'


def calculate_orb(
    ticker: str,
    high: float,
    low: float,
    account_size: float,
    risk_pct: float,
) -> dict:
    """
    Return all ORB planning data for both long and short scenarios.

    Entry prices use a 1-cent buffer beyond the range edge — this is the
    standard breakout confirmation technique (buy ONE tick above the high,
    short ONE tick below the low).

    Targets use R-multiples:
      1.5R = entry ± 1.5 × (entry - stop)
      2.0R = entry ± 2.0 × (entry - stop)
    """
    if high <= 0 or low <= 0 or high <= low:
        return {'error': 'Invalid high/low values. High must be greater than Low.'}

    if account_size <= 0 or risk_pct <= 0:
        return {'error': 'Account size and risk % must be positive numbers.'}

    # Dollar amount Silent is willing to lose on this single trade
    dollar_risk = round(account_size * (risk_pct / 100.0), 2)

    is_valid, validity_message, validity_class = validate_range(high, low)
    range_size = round(high - low, 2)
    avg_price  = (high + low) / 2.0
    range_pct  = round((range_size / avg_price) * 100, 2)

    # ── Long setup ──────────────────────────────────────────────────────────
    # Enter 1¢ above the high (wait for confirmation break)
    # Stop 1¢ below the low (full range as the invalidation point)
    l_entry         = round(high + 0.01, 2)
    l_stop          = round(low  - 0.01, 2)
    l_risk_per_share = round(l_entry - l_stop, 2)
    l_shares         = math.floor(dollar_risk / l_risk_per_share) if l_risk_per_share > 0 else 0
    l_target_1r5    = round(l_entry + 1.5 * l_risk_per_share, 2)
    l_target_2r     = round(l_entry + 2.0 * l_risk_per_share, 2)

    # ── Short setup ─────────────────────────────────────────────────────────
    s_entry          = round(low  - 0.01, 2)
    s_stop           = round(high + 0.01, 2)
    s_risk_per_share = round(s_stop - s_entry, 2)
    s_shares          = math.floor(dollar_risk / s_risk_per_share) if s_risk_per_share > 0 else 0
    s_target_1r5     = round(s_entry - 1.5 * s_risk_per_share, 2)
    s_target_2r      = round(s_entry - 2.0 * s_risk_per_share, 2)

    return {
        'ticker':           ticker.upper(),
        'orb_high':         round(high, 2),
        'orb_low':          round(low,  2),
        'range_size':       range_size,
        'range_pct':        range_pct,
        'dollar_risk':      dollar_risk,
        'is_valid':         is_valid,
        'validity_message': validity_message,
        'validity_class':   validity_class,

        'long': {
            'entry':          l_entry,
            'stop':           l_stop,
            'risk_per_share': l_risk_per_share,
            'shares':         l_shares,
            'target_1r5':     l_target_1r5,
            'target_2r':      l_target_2r,
        },
        'short': {
            'entry':          s_entry,
            'stop':           s_stop,
            'risk_per_share': s_risk_per_share,
            'shares':         s_shares,
            'target_1r5':     s_target_1r5,
            'target_2r':      s_target_2r,
        },
    }
