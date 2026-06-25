# Agent Specs — decision log

This captures the reasoning behind every locked value in `config/`, so
future changes are deliberate, not accidental.

## Why these risk numbers

Starting point was a $1,000 paper account (mirroring the real account
after drawdown from $2,000, driven by 15% per-trade risk sizing and
positions held with no enforced exit through end of day on 0DTE/weekly
options). The risk engine exists specifically to make both of those
failure modes structurally impossible, not just discouraged:

- **Sizing is %-of-current-equity, recalculated every trade** — not a
  fixed dollar amount off the original balance. Prevents the
  compounding-losses-accelerate problem of large fixed-% risk on a
  shrinking account.
- **Dual exit is mandatory, not optional** — premium-percentage stop
  AND a hard time-based force-close, independent of each other. 0DTE
  options can gap past a price-based stop, so price alone isn't
  enough; a clock-based exit makes "ran it to end of day" impossible
  even if the price-stop logic fails.

## Locked values

| Parameter | Value | Source |
|---|---|---|
| Paper starting balance | $1,000 | Mirrors real account so % rules mean something |
| Per-trade risk | 1% of current equity | Silent, direct decision |
| Daily max loss (circuit breaker) | 3% | Silent, direct decision |
| Max trades/day | 3 | Silent, direct decision |
| Consecutive-loss cooldown | 2 losses | Tightened from Silent's 2-3 range — unproven system, loosen later with real data |
| Max concurrent positions | 1 | Stated goal: prove one symbol, one strategy first |
| Premium stop % | 50% (placeholder) | **Not yet confirmed with Silent — confirm before first paper run** |
| Time-based force close | 30 min before close (placeholder) | **Not yet confirmed with Silent — confirm before first paper run** |
| OR window | First 30 min (9:30-10:00 ET) | Silent, direct decision |
| Trade window (new signals only) | First 90 min (9:30-11:00 ET) | Silent, direct decision |
| Volume confirmation | Breakout candle volume > 1.5x 20-bar rolling avg on 2-min timeframe | Silent, direct decision (tightened to 1.5x given TSLA volatility) |
| Body ratio filter | Candle body >= 60% of full range | Added to filter wick-only breaks |
| Option delta band | 0.35-0.55 | Standard 0DTE/weekly directional sweet spot |
| Option min open interest | 500 (placeholder) | **Not yet confirmed with Silent** |
| Option max spread % | 10% (placeholder) | **Not yet confirmed with Silent** |

Anything marked "placeholder" is a reasonable default, not a decision
Silent has actually confirmed — flag these before relying on them.

## Webull OpenAPI notes (confirmed via docs, June 2026)

- Two environments: UAT (test) and production, swapped by changing one
  endpoint config value, no code changes needed.
- **UAT shared credentials connect to a publicly shared test account.**
  Other developers' test orders/positions can appear in it. Do not use
  UAT order/position state as this system's paper-trading record —
  use it only to verify API calls work, keep actual paper trade
  records in this system's own logs.
- Market Data API: HTTP "Data API" confirmed for historical/snapshot
  bars (1-min candlesticks confirmed via SDK example, likely more
  intervals available — confirm once account is live). MQTT "Data
  Streaming API" for real-time quote/snapshot/tick data.
- **VWAP does not appear to be a precomputed field Webull hands back.**
  Compute it in the Data Agent from 1-min bars: running
  cumulative(price * volume) / cumulative(volume) from session open.
- Options orders only support order_type LIMIT. No MARKET, no
  TRAILING_STOP_LOSS. This directly shapes how Execution Agent has to
  implement the time-based force-close (active marketable-limit order,
  not a resting stop).
- Official "Agent Skills" CLI (webull-inc/webull-agent-skills) already
  implements symbol whitelist, max order notional, max order quantity,
  and a dry-run "local-check" mode, defaulting to sandbox unless
  explicitly set to prod. Worth reusing as a second backstop layer
  under Execution Agent, independent of `risk_engine.py`.

## Autonomy progression plan

Not a single switch — two independent dials (human-in-loop vs not,
paper vs live):

1. Paper trading, full agent stack, zero manual approval (nothing at
   stake).
2. Live trading, manual confirm on every order.
3. Live trading, autonomous execution, daily circuit breaker, Silent
   reviews trades daily (not stepping in only when something looks
   wrong — actual daily review).
4. Only once stage 3 has been boring for a sustained period: autonomous
   with periodic rather than daily review.

No stage skips the daily-loss circuit breaker. No agent gets authority
to change `risk_config.py` values — that's a manual, deliberate edit
only.

## Open items (not yet specced)

- Data Agent implementation (blocked on production API key)
- Execution Agent implementation (blocked on Data Agent + SDK vs CLI
  decision)
- Review Agent schema and storage (blocked on Execution Agent —
  need to know real fill data shape first)
- Confirm the three placeholder values above
- Strategist logic that actually picks a strike from the chain using
  the delta band + liquidity filters (currently just config values,
  no code consuming them yet)
