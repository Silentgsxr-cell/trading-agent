"""
risk_calculator.py — Position-sizing and risk-metric calculations.

The core formula:
  dollar_risk   = account_size × (risk_pct / 100)
  risk_per_share = |entry - stop|
  max_shares    = floor(dollar_risk / risk_per_share)

Industry-standard daily loss limit is 2% of account. We surface this
so Silent can track how many trades remain before hitting the limit.
"""

import math


def calculate_risk(
    account_size: float,
    risk_pct: float,
    entry_price: float,
    stop_price: float,
) -> dict:
    """
    Return a full risk breakdown for a single trade.

    Direction is inferred automatically:
      entry > stop → Long  (stop is below entry)
      entry < stop → Short (stop is above entry)
    """
    if account_size <= 0:
        return {'error': 'Account size must be greater than zero.'}
    if entry_price <= 0 or stop_price <= 0:
        return {'error': 'Entry and stop prices must be positive.'}
    if entry_price == stop_price:
        return {'error': 'Entry and stop cannot be the same price.'}

    dollar_risk     = round(account_size * (risk_pct / 100.0), 2)
    risk_per_share  = abs(entry_price - stop_price)
    max_shares      = math.floor(dollar_risk / risk_per_share) if risk_per_share > 0 else 0

    # Max daily loss — standard 2% rule prevents blowing up in one bad morning
    max_daily_loss  = round(account_size * 0.02, 2)

    # How many losing trades at this risk level before hitting the daily limit
    trades_before_limit = math.floor(max_daily_loss / dollar_risk) if dollar_risk > 0 else 0

    # Total capital committed to this position
    total_position  = round(max_shares * entry_price, 2)
    pct_of_account  = round((total_position / account_size) * 100, 1) if account_size > 0 else 0

    # Targets and direction
    if entry_price > stop_price:
        direction    = 'Long'
        target_1r5  = round(entry_price + 1.5 * risk_per_share, 2)
        target_2r   = round(entry_price + 2.0 * risk_per_share, 2)
        gain_1r5    = round(max_shares * 1.5 * risk_per_share, 2)
        gain_2r     = round(max_shares * 2.0 * risk_per_share, 2)
    else:
        direction    = 'Short'
        target_1r5  = round(entry_price - 1.5 * risk_per_share, 2)
        target_2r   = round(entry_price - 2.0 * risk_per_share, 2)
        gain_1r5    = round(max_shares * 1.5 * risk_per_share, 2)
        gain_2r     = round(max_shares * 2.0 * risk_per_share, 2)

    return {
        'direction':            direction,
        'dollar_risk':          dollar_risk,
        'risk_per_share':       round(risk_per_share, 2),
        'max_shares':           max_shares,
        'total_position':       total_position,
        'pct_of_account':       pct_of_account,
        'target_1r5':           target_1r5,
        'target_2r':            target_2r,
        'gain_1r5':             gain_1r5,
        'gain_2r':              gain_2r,
        'max_daily_loss':       max_daily_loss,
        'trades_before_limit':  trades_before_limit,
    }


def validate_trade(
    entry: float,
    stop: float,
    target: float,
    account_size: float = 0,
) -> dict:
    """
    Evaluate a proposed trade and return a GO / NO-GO decision.

    Rules:
      1. Stop loss must be defined (non-zero).
      2. Risk/reward must be >= 1.5R.
    """
    warnings = []

    # Stop is required — this is Silent's #1 discipline rule
    if stop <= 0:
        return {
            'error':        'Stop loss is required. Never enter a trade without a defined stop.',
            'go_nogo':      'NO-GO',
            'go_class':     'nogo',
            'rr_ratio':     0,
            'dollar_risk':  0,
            'warnings':     ['Stop loss not defined.'],
            'meets_rules':  False,
        }

    if entry <= 0 or target <= 0:
        return {'error': 'Entry and target prices must be positive.', 'go_nogo': 'NO-GO', 'go_class': 'nogo'}

    # Determine direction and compute risk/reward
    if entry > stop:
        # Long trade
        risk   = entry - stop
        reward = target - entry
    else:
        # Short trade
        risk   = stop - entry
        reward = entry - target

    if risk <= 0:
        return {'error': 'Invalid stop — risk per share is zero or negative.', 'go_nogo': 'NO-GO', 'go_class': 'nogo'}

    if reward <= 0:
        warnings.append('Target is on the wrong side of entry — reward is zero or negative.')

    rr_ratio = round(reward / risk, 2) if risk > 0 else 0

    if rr_ratio < 1.5:
        warnings.append(f'R/R ratio is {rr_ratio}R — minimum required is 1.5R. Consider moving your target.')

    dollar_risk = round(account_size * 0.01, 2) if account_size > 0 else None

    meets_rules = len(warnings) == 0
    go_nogo     = 'GO'  if meets_rules else 'NO-GO'
    go_class    = 'go'  if meets_rules else 'nogo'

    return {
        'rr_ratio':    rr_ratio,
        'dollar_risk': dollar_risk,
        'warnings':    warnings,
        'go_nogo':     go_nogo,
        'go_class':    go_class,
        'meets_rules': meets_rules,
        'direction':   'Long' if entry > stop else 'Short',
    }
