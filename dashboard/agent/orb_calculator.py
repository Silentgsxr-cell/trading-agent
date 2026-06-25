"""
ORB level calculator — the math that was previously typed in by hand.

Entry is placed 1¢ beyond the range boundary so the order only fills
on a confirmed close-beyond, not on a wick poke. Stop is 1¢ inside
the opposite boundary. Targets are 1.5R and 2R from entry.
"""


def calculate_orb(ticker: str, high: float, low: float,
                  account_size: float, risk_pct: float) -> dict:
    range_size = round(high - low, 4)
    if range_size <= 0:
        return {"error": "High must be greater than low"}

    range_pct  = round(range_size / low * 100, 2)
    dollar_risk = round(account_size * risk_pct / 100, 2)

    is_valid = 0.10 <= range_size <= low * 0.03
    if range_size < 0.10:
        validity_message = "Range too tight (<$0.10) — skip"
    elif range_size > low * 0.03:
        validity_message = "Range too wide (>3% of price) — risk is outsized"
    else:
        validity_message = "Clean setup"

    l_entry  = round(high + 0.01, 4)
    l_stop   = round(low  - 0.01, 4)
    l_rps    = round(l_entry - l_stop, 4)
    l_shares = int(dollar_risk / l_rps) if l_rps > 0 else 0
    l_1r5    = round(l_entry + 1.5 * l_rps, 4)
    l_2r     = round(l_entry + 2.0 * l_rps, 4)

    s_entry  = round(low  - 0.01, 4)
    s_stop   = round(high + 0.01, 4)
    s_rps    = round(s_stop - s_entry, 4)
    s_shares = int(dollar_risk / s_rps) if s_rps > 0 else 0
    s_1r5    = round(s_entry - 1.5 * s_rps, 4)
    s_2r     = round(s_entry - 2.0 * s_rps, 4)

    return {
        "ticker":           ticker,
        "is_valid":         is_valid,
        "validity_message": validity_message,
        "range_size":       range_size,
        "range_pct":        range_pct,
        "dollar_risk":      dollar_risk,
        "long": {
            "entry": l_entry, "stop": l_stop, "risk_per_share": l_rps,
            "target_1r5": l_1r5, "target_2r": l_2r, "shares": l_shares,
        },
        "short": {
            "entry": s_entry, "stop": s_stop, "risk_per_share": s_rps,
            "target_1r5": s_1r5, "target_2r": s_2r, "shares": s_shares,
        },
    }
