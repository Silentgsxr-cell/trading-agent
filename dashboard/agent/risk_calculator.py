"""
Share-based risk calculator and trade validator.

Distinct from agents/risk_engine.py (which sizes options contracts).
This module does stock share sizing from account equity + risk % and
validates that a proposed trade meets minimum R/R rules.
"""


def calculate_risk(account_size: float, risk_pct: float,
                   entry_price: float, stop_price: float) -> dict:
    dollar_risk    = round(account_size * risk_pct / 100, 2)
    risk_per_share = abs(entry_price - stop_price)

    if risk_per_share <= 0:
        return {"error": "Entry and stop cannot be the same price"}

    direction       = "LONG" if entry_price > stop_price else "SHORT"
    max_shares      = int(dollar_risk / risk_per_share)
    total_position  = round(entry_price * max_shares, 2)
    pct_of_account  = round(total_position / account_size * 100, 2) if account_size else 0
    max_daily_loss  = round(account_size * 0.02, 2)
    trades_before_limit = int(max_daily_loss / dollar_risk) if dollar_risk > 0 else 0

    if direction == "LONG":
        target_1r5 = round(entry_price + 1.5 * risk_per_share, 4)
        target_2r  = round(entry_price + 2.0 * risk_per_share, 4)
    else:
        target_1r5 = round(entry_price - 1.5 * risk_per_share, 4)
        target_2r  = round(entry_price - 2.0 * risk_per_share, 4)

    return {
        "max_shares":          max_shares,
        "direction":           direction,
        "dollar_risk":         dollar_risk,
        "risk_per_share":      round(risk_per_share, 4),
        "max_daily_loss":      max_daily_loss,
        "trades_before_limit": trades_before_limit,
        "total_position":      total_position,
        "pct_of_account":      pct_of_account,
        "target_1r5":          target_1r5,
        "gain_1r5":            round(dollar_risk * 1.5, 2),
        "target_2r":           target_2r,
        "gain_2r":             round(dollar_risk * 2.0, 2),
    }


def validate_trade(entry: float, stop: float, target: float,
                   account_size: float) -> dict:
    warnings = []

    if entry <= 0 or stop <= 0 or target <= 0:
        return {
            "go_nogo": "NO-GO", "go_class": "nogo", "rr_ratio": 0,
            "dollar_risk": None, "direction": "—",
            "warnings": ["Invalid prices"], "meets_rules": False,
        }

    risk_per_share = abs(entry - stop)
    direction = "LONG" if entry > stop else "SHORT"

    if direction == "LONG":
        reward = target - entry
        if target <= entry:
            warnings.append("Target must be above entry for a long")
    else:
        reward = entry - target
        if target >= entry:
            warnings.append("Target must be below entry for a short")

    rr_ratio    = round(reward / risk_per_share, 2) if risk_per_share > 0 else 0
    dollar_risk = round(account_size * 0.01, 2) if account_size else None

    if rr_ratio < 1.5:
        warnings.append(f"R/R is {rr_ratio}R — minimum required is 1.5R")

    meets_rules = rr_ratio >= 1.5 and len(warnings) == 0
    return {
        "go_nogo":     "GO" if meets_rules else "NO-GO",
        "go_class":    "go" if meets_rules else "nogo",
        "rr_ratio":    rr_ratio,
        "dollar_risk": dollar_risk,
        "direction":   direction,
        "warnings":    warnings,
        "meets_rules": meets_rules,
    }
