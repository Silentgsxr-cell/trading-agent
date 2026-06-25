"""
Smoke test — run with: python -m tests.smoke_test

Proves Risk Engine and Signal Agent work end to end against synthetic
bar data, without needing any live Webull connection. Not a full test
suite, just a sanity check that the two built agents behave as specced.
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.signal_agent import ORBSignalAgent
from agents.risk_engine import RiskEngine, Trade


def make_bar(t, o, h, l, c, v):
    return {"timestamp": t, "open": o, "high": h, "low": l, "close": c, "volume": v}


def run_signal_agent_smoke_test():
    print("--- Signal Agent smoke test ---")
    agent = ORBSignalAgent(symbol="TSLA")
    start = datetime.strptime("2026-06-19 09:30", "%Y-%m-%d %H:%M")

    # 15 bars (30 min) building the opening range, flat-ish volume
    t = start
    for i in range(15):
        bar = make_bar(t, 300, 302, 298, 300, 50_000)
        result = agent.on_bar(bar)
        assert result is None, "should not signal during OR window"
        t += timedelta(minutes=2)

    print(f"OR locked: high={agent.or_high}, low={agent.or_low}")

    # 20 quiet bars to build rolling volume average post-OR
    for i in range(20):
        bar = make_bar(t, 300, 301, 299, 300, 50_000)
        agent.on_bar(bar)
        t += timedelta(minutes=2)

    # Breakout bar: closes above OR high, volume way above average, strong body
    breakout = make_bar(t, 301, 306, 300.5, 305, 150_000)
    signal = agent.on_bar(breakout)
    assert signal is not None, "expected a breakout signal"
    assert signal["direction"] == "long"
    print("Signal fired:", signal)


def run_risk_engine_smoke_test():
    print("\n--- Risk Engine smoke test ---")
    engine = RiskEngine(starting_balance=1000.00)

    # NOTE: at $1,000 balance / 1% risk / 50% premium stop, dollar_risk
    # is $10 and loss_per_contract = premium * 100 * 0.50. That caps
    # affordable premium at $0.20 to size even 1 contract. Using a
    # cheap-premium contract here on purpose to demonstrate sizing —
    # this constraint is real and worth flagging to Silent directly,
    # not something to silently work around.
    cheap_premium = 0.15
    decision = engine.evaluate(direction="long", entry_premium=cheap_premium)
    print("First trade evaluation:", decision)
    assert decision["approved"] is True

    trade = Trade(
        entry_time=datetime.now(),
        direction="long",
        entry_premium=cheap_premium,
        quantity=decision["quantity"],
        dollar_risk=decision["dollar_risk"],
    )
    engine.record_open(trade)

    # Simulate it hitting the premium stop
    engine.record_close(trade, exit_premium=cheap_premium * 0.5, exit_reason="stop")
    print(f"After 1 loss: balance={engine.session.current_balance:.2f}, "
          f"consecutive_losses={engine.session.consecutive_losses}")

    # Second loss should trigger cooldown (CONSECUTIVE_LOSS_COOLDOWN=2)
    decision2 = engine.evaluate(direction="long", entry_premium=cheap_premium)
    trade2 = Trade(
        entry_time=datetime.now(), direction="long", entry_premium=cheap_premium,
        quantity=decision2["quantity"], dollar_risk=decision2["dollar_risk"],
    )
    engine.record_open(trade2)
    engine.record_close(trade2, exit_premium=cheap_premium * 0.5, exit_reason="stop")

    decision3 = engine.evaluate(direction="long", entry_premium=cheap_premium)
    print("Third trade evaluation (should be rejected — cooldown):", decision3)
    assert decision3["approved"] is False


def run_dashboard_modules_smoke_test():
    print("\n--- Dashboard modules smoke test ---")

    # dashboard/ is a sibling of tests/ so add its parent to path
    dashboard_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard")
    sys.path.insert(0, dashboard_dir)

    from agent.orb_calculator  import calculate_orb
    from agent.risk_calculator import calculate_risk, validate_trade

    # ORB calculator
    orb = calculate_orb("TSLA", high=305.00, low=299.00, account_size=1000, risk_pct=1.0)
    assert "error" not in orb, f"Unexpected ORB error: {orb}"
    assert orb["is_valid"], f"Expected valid setup, got: {orb['validity_message']}"
    assert orb["long"]["entry"]  > 305.00
    assert orb["short"]["entry"] < 299.00
    assert orb["long"]["shares"] > 0
    print(f"ORB long entry={orb['long']['entry']}  stop={orb['long']['stop']}  "
          f"shares={orb['long']['shares']}  1.5R={orb['long']['target_1r5']}")

    # Risk calculator
    risk = calculate_risk(account_size=1000, risk_pct=1.0, entry_price=305.01, stop_price=298.99)
    assert "error" not in risk
    assert risk["direction"] == "LONG"
    assert risk["max_shares"] > 0
    assert risk["target_2r"] > risk["target_1r5"]  # 2R target farther than 1.5R
    print(f"Risk: max_shares={risk['max_shares']}  dollar_risk={risk['dollar_risk']}  "
          f"1.5R={risk['target_1r5']}  2R={risk['target_2r']}")

    # Validate — GO case (>= 1.5R)
    go = validate_trade(entry=305.01, stop=298.99, target=314.07, account_size=1000)
    assert go["go_nogo"] == "GO",   f"Expected GO, got {go}"
    assert go["rr_ratio"] >= 1.5

    # Validate — NO-GO case (< 1.5R)
    nogo = validate_trade(entry=305.01, stop=298.99, target=307.00, account_size=1000)
    assert nogo["go_nogo"] == "NO-GO", f"Expected NO-GO, got {nogo}"
    print(f"Validator GO rr={go['rr_ratio']}R  NO-GO rr={nogo['rr_ratio']}R — both correct")

    # Signal → risk engine end-to-end: signal fires, risk engine approves, loss recorded
    print("\nEnd-to-end: signal → risk engine approval → loss bookkeeping")
    agent  = ORBSignalAgent(symbol="TSLA")
    engine = RiskEngine(starting_balance=1000.00)
    t      = datetime.strptime("2026-06-20 09:30", "%Y-%m-%d %H:%M")

    for i in range(15):   # build OR window (30 min of 2-min bars)
        agent.on_bar(make_bar(t, 300, 302, 298, 300, 50_000))
        t += timedelta(minutes=2)
    for i in range(20):   # build volume baseline post-OR
        agent.on_bar(make_bar(t, 300, 301, 299, 300, 50_000))
        t += timedelta(minutes=2)

    signal = agent.on_bar(make_bar(t, 301, 306, 300.5, 305, 150_000))
    assert signal is not None and signal["direction"] == "long"

    decision = engine.evaluate(direction=signal["direction"], entry_premium=0.15)
    assert decision["approved"], f"Expected approval: {decision}"

    trade = Trade(
        entry_time=t, direction=decision["direction"],
        entry_premium=0.15, quantity=decision["quantity"],
        dollar_risk=decision["dollar_risk"],
    )
    engine.record_open(trade)
    engine.record_close(trade, exit_premium=0.075, exit_reason="stop")
    assert engine.session.consecutive_losses == 1
    print(f"Signal fired → approved {decision['quantity']} contract(s) → "
          f"loss recorded, consecutive_losses={engine.session.consecutive_losses}")


if __name__ == "__main__":
    run_signal_agent_smoke_test()
    run_risk_engine_smoke_test()
    run_dashboard_modules_smoke_test()
    print("\nAll smoke tests passed.")
