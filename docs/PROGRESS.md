# Build Progress — 2026-06-24

## What Was Built

### 1. Agent Crew — `agents/`

Five v2 agents structured around a strict ring hierarchy:

| Agent | Ring | Role |
|---|---|---|
| `signal_agent.py` | Core | ORB breakout detection on the 2-min stream |
| `risk_engine.py` | Core | Deterministic veto, position sizing, circuit breakers |
| `data_agent.py` | Macro | Market data, VWAP, session levels, options chain |
| `review_agent.py` | News | Daily journal feedback loop, edge-decay tracking |
| `execution_agent.py` | Execution | Order submission (paper-first), only agent allowed to place orders |
| `strategist.py` | Execution | Strike selection — not yet built |

Risk Engine is the only agent with veto power. Signal Agent never sizes or orders. Execution Agent rejects anything not approved by Risk Engine.

---

### 2. Flask Backend — `dashboard/app.py`

12 routes serving the trading terminal at **localhost:5000**:

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Dashboard page with server-side market data seed |
| `/api/market` | GET | Live prices, SPY bias, market clock |
| `/api/orb` | POST | ORB level calculation |
| `/api/validate` | POST | Trade GO/NO-GO validation |
| `/api/risk` | POST | Position size + risk metrics |
| `/api/journal` | GET | Last 10 journal entries + stats |
| `/api/journal` | POST | Save new journal entry |
| `/api/news` | GET | Recent news for watchlist tickers |
| `/api/sparkline` | GET | 5-bar sparkline data per ticker |
| `/api/status` | GET | Live risk engine session state |
| `/api/status/halt` | POST | Manual kill switch |
| `/api/status/reset` | POST | Reset session for new trading day |

Agent module relocated from `agent/` → `dashboard/agent/` to co-locate with Flask.

---

### 3. Config Module — `config/`

- `risk_config.py` — max trades/day, daily loss %, consecutive loss cooldown, position limits
- `strategy_config.py` — ORB parameters, watchlist, setup rules
- Clean import path: `from config import risk_config as cfg`

---

### 4. ClawOps Mission Control — `mission-control/`

Next.js 14 App Router dashboard at **localhost:3000**. Reads entirely from local files — no Flask dependency.

**Pages:**
- `/` — Cockpit: agent fleet rings, crew readiness, journal stats, engine status
- `/logs` — Decision feed from `state/decisions.jsonl`
- `/docs` — Vault docs viewer (trading-relevant Obsidian notes only, denylist enforced)
- `/memory` — Memory/context viewer

**Key components:**
- `ThreeRings.tsx` — SVG fleet diagram: Macro / News / Execution rings + Core center
- `AgentCard.tsx` — Per-agent status card (live / stub / missing, derived from source)
- `StatCard.tsx` — Metric cards (P&L, win rate, discipline, engine status)
- `MarketStrip.tsx` — Top-of-page market ticker strip

**Data layer (`lib/`):**
- `agents.ts` — Reads `agents/*.py`, derives status from `NotImplementedError` presence
- `journal.ts` — Parses `data/journal.csv`, computes P&L / win rate / discipline score
- `runtime.ts` — Reads `state/session.json`, `state/signals.jsonl`, `state/decisions.jsonl`
- `vault.ts` — Reads Obsidian vault with denylist/allowlist filtering
- `config.ts` — Resolves all file paths from project root; enforces vault denylist

**Vault denylist** (never surfaced in docs/memory screens):
`finance, ein, family, business & llc, business plan, network, vault-setup, mac tools`

---

### 5. State Contract — `state/`

- `state/session.json` — Written by Python runner (Phase 2). Read-if-present by Mission Control. Holds daily P&L, trades opened, halted flag, consecutive losses.
- `state/signals.jsonl` — Signal feed (Phase 2)
- `state/decisions.jsonl` — Decision audit log (Phase 2)

Session created today with default zero state so Mission Control shows **ONLINE** instead of offline.

---

### 6. Journal System — `data/journal.csv`

CSV-based trade journal with discipline tracking. Fields: date, ticker, strategy, entry, stop, target, exit, pnl, trade_type, was_planned, chased, followed_stop, lesson, discipline_grade.

Current entries: 4 trades (2 closed, 2 open). Net P&L: -$887.15. Win rate: 50%.

---

### 7. Infrastructure Fixes

- **AirPlay port conflict** — macOS AirPlay Receiver occupies port 5000 on all interfaces (IPv6). Flask only binds IPv4. Browser connects via IPv6 → AirPlay intercepts → blank page. Fix: disable AirPlay Receiver in System Settings.
- **Path resolution** — Next.js resolves project root as `cwd/..` from `mission-control/`. All lib paths verified correct.
- **Windows line endings** — `journal.csv` uses `\r\n`; `journal.ts` parser handles this correctly (strips `\r`).

---

## What's Next (Phase 2)

- [ ] Python runner that writes `state/session.json` and `state/decisions.jsonl` in real time
- [ ] `strategist.py` — strike selection agent
- [ ] Live signal loop: data_agent → signal_agent → risk_engine → execution_agent
- [ ] Broker integration (paper trading first via IBKR or Alpaca)
- [ ] `state/signals.jsonl` feed powering the Mission Control logs page
