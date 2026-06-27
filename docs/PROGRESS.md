# Build Progress — ClawOps
Last updated: 2026-06-26

---

## What Was Built

### 1. Agent Crew — `agents/`

Six v2 agents structured around a strict ring hierarchy:

| Agent | Canonical Name | Ring | Role |
|---|---|---|---|
| `signaos.py` | HAWK | Core | Multi-strategy signal engine (ORB live, 5 stubs) |
| `risk_engine.py` | VAULT | Core | Deterministic veto, position sizing, circuit breakers |
| `dataos.py` | DataOS | Macro | Market data stub — bars, VWAP, session levels, options chain |
| `daitaos.py` | DaiTaos | News | Daily intelligence crew registration |
| `review_agent.py` | LEDGER | News | Daily journal feedback loop, edge-decay tracking |
| `execution_agent.py` | TRIGGER | Execution | Order submission — paper-first, only agent allowed to place orders |
| `strategist.py` | Strategist | Execution | Strike selection — not yet built |

VAULT is the only agent with veto power. HAWK never sizes or orders. TRIGGER rejects anything not approved by VAULT.

---

### 2. Flask Backend — `dashboard/app.py`

17 routes serving the trading terminal at **localhost:5000**:

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
| `/api/status` | GET | Live VAULT session state |
| `/api/status/halt` | POST | Manual kill switch |
| `/api/status/reset` | POST | Reset session for new trading day |
| `/api/backtest` | POST | Historical ORB backtest |
| `/api/tickets` | GET/POST | Dev agent ticket queue |
| `/api/tickets/<id>` | GET | Single ticket with full log |
| `/api/tickets/<id>/approve` | POST | Approve complex ticket |
| `/api/tickets/<id>/revert` | POST | Git revert a completed ticket |

---

### 3. Config Module — `config/`

- `risk_config.py` — max trades/day, daily loss %, consecutive loss cooldown, position limits
- `strategy_config.py` — ORB parameters, watchlist, setup rules
- Clean import: `from config import risk_config as cfg`

---

### 4. ClawOps Mission Control — `mission-control/`

Next.js 14 App Router dashboard at **localhost:3000**. Reads entirely from local files.

**Pages:**
- `/` — Cockpit: agent fleet rings, crew readiness, journal stats, engine status
- `/logs` — Decision feed from `state/decisions.jsonl`
- `/docs` — Vault docs viewer (trading-relevant notes only, denylist enforced)
- `/memory` — Intelligence / context viewer
- `/finance` — Net worth, accounts, debts, budget, trading P&L
- `/dev` — Dev Agent ticket queue (two-column: queue + detail/form)

**Key components:**
- `ThreeRings.tsx` — SVG fleet diagram: Macro / News / Execution rings + Core center
- `AgentCard.tsx` — Per-agent status card (live / stub / missing, derived from source)
- `StatCard.tsx` — Metric cards (P&L, win rate, discipline, engine status)
- `MarketStrip.tsx` — Top-of-page market ticker strip
- `Sidebar.tsx` — Nav: Cockpit, Decision Feed, Intelligence, Research, Finance, Dev Queue

**Data layer (`lib/`):**
- `agents.ts` — Reads agents/*.py, derives status from NotImplementedError presence
- `journal.ts` — Parses data/journal.csv, computes P&L / win rate / discipline score
- `runtime.ts` — Reads state/session.json, state/signals.jsonl, state/decisions.jsonl
- `vault.ts` — Reads Obsidian vault with denylist/allowlist filtering
- `finance.ts` — Types + getFinance() reader for data/finance.json
- `tickets.ts` — Server-only getTickets() for data/tickets.json
- `ticket-types.ts` — Client-safe ticket types/constants (no Node.js imports)

**Vault denylist:** finance, ein, family, business & llc, business plan, network, vault-setup, mac tools

---

### 5. State Contract — `state/`

- `state/session.json` — Written by runner, read by dashboard + Mission Control. **Excluded from git** (runtime state).
- `state/signals.jsonl` — Signal feed (excluded from git)
- `state/decisions.jsonl` — Decision audit log (excluded from git)

---

### 6. Journal System — `data/journal.csv`

CSV-based trade journal with discipline tracking. Fields: date, ticker, strategy, entry, stop, target, exit, pnl, trade_type, was_planned, chased, followed_stop, lesson, discipline_grade.

---

### 7. Finance Tab — `mission-control/app/finance/`

Full personal finance dashboard at `/finance`:
- **Net Worth Snapshot** — live-computed from accounts minus debts
- **Accounts** — inline edit balance, persists to `data/finance.json`
- **Debt Tracker** — color-coded progress bars (red/amber/green by remaining %)
- **Monthly Budget** — 6 categories, Set Budget + Spend buttons, progress bars
- **Trading P&L** — read-only, sourced from journal.csv

---

### 8. Infrastructure Fixes

- **AirPlay port conflict** — macOS AirPlay Receiver occupies port 5000. Fix: disable in System Settings.
- **Path resolution** — Next.js resolves project root as `cwd/..` from `mission-control/`.
- **Windows line endings** — journal.csv `\r\n` handled correctly in journal.ts.

---

### 9. HAWK (Signaos) — Multi-Strategy Signal Engine

`agents/signaos.py` — pluggable strategy registry, 6 strategies:
- **ORB** (live) — 2-min bar ORB, volume ratio filter, confidence scoring, 9:30–11:00 ET window
- trend_continuation, pullback, relative_strength, volatility_expansion, news_catalyst — stubs

Scoring: Technical 40% + News 15% + Macro 25% + Risk 20% → S/A/B/C conviction tiers.
Only S and A tier signals routed to VAULT.

---

### 10. Single-Writer Rule — `utils/`

All shared file writes serialized through filelock-protected utils:

| Module | Owns | Protection |
|---|---|---|
| `utils/state_manager.py` | `state/session.json` | filelock + atomic rename |
| `utils/journal_writer.py` | `data/journal.csv` | filelock |
| `utils/event_log.py` | `state/decisions.jsonl` | filelock |

`dashboard/app.py` reads state_manager when runner is online, falls back to in-process engine when offline.
`runner.py` delegates all writes through these utils. `filelock>=3.12.0` in requirements.txt.

---

### 11. runner.py — Autonomous Trading Loop

`runner.py` — live ORB runner, active weekdays 9:30–16:00 ET:
- Polls yfinance 2-min bars every 30s
- Feeds bars → Signaos (HAWK) → RiskEngine (VAULT) → state files
- SPY bias refreshed every 5 minutes
- Heartbeat written every off-hours poll tick
- Daily roll-over resets engine + signaos at midnight ET
- Clean shutdown on SIGINT/SIGTERM → writes OFFLINE to session.json

---

### 12. DaiTaos — Daily Intelligence + Discord Bot

`utils/daitaos.py` — 9-section morning brief sent to Discord webhook:
1. Date & market status
2. TSLA direction bias
3. Watchlist scan
4. SPY market bias
5. Today's trading rules
6. Agent & session status
7. Journal edge summary
8. Silent's edge reminder
9. **Dev Agent overnight** — tickets completed/failed, queue size, security flags

`utils/daitaos_bot.py` — Discord bot with commands:
- `!brief`, `!tsla`, `!watchlist`, `!status`, `!rules`, `!pnl`, `!config`, `!help`
- `!ticket status` — all tickets and statuses
- `!ticket pause` / `!ticket resume` — pause/resume dev agent
- `!ticket log TICKET-XXX` — full execution log
- `!approve TICKET-XXX` — approve complex tickets
- `!revert TICKET-XXX` — git revert a completed ticket

LaunchAgents: `com.silent.dataos.plist`, `com.silent.dataos.bot.plist`, `com.silent.dataos.sync.plist`

---

### 13. Security Watchdog — `utils/watchdog.py`

Background process, checks every 60 seconds. Start: `python3 utils/watchdog.py &`

| # | Check | Alert Level | Action |
|---|---|---|---|
| 1 | API key exposure in any source/data file | CRITICAL | Discord embed, no key value logged |
| 2 | session.json invariants vs config thresholds | WARNING | Exact field + value in Discord |
| 3 | 5 critical files exist + non-empty | CRITICAL | Auto-halts runner via state_manager |
| 4 | risk_config.py / strategy_config.py mtime+size | CRITICAL | Logs timestamp + byte delta |
| 5 | lastHeartbeat stale >3min during market hours | WARNING | "Runner heartbeat stale" |
| 6 | .env not git-tracked, not empty | CRITICAL | Auto-runs `git rm --cached .env` |
| 7 | Git commit author audit (hourly) | CRITICAL | Flags unknown commit authors |

Alert dedup: same key fires 3+ cycles → suppressed, persistent summary sent instead.
Log rotation: `logs/watchdog.log` → `watchdog.log.1` at 10 MB.

LaunchAgent: `deploy/com.silent.watchdog.plist`
```
cp deploy/com.silent.watchdog.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.silent.watchdog.plist
```

---

### 14. Dev Agent System — `utils/dev_agent.py`

Autonomous agent that picks up tickets from `data/tickets.json`, calls Claude API,
writes code, tests, commits, and merges — fully unattended.

**6 safety gates** (abort if any fail):
1. Market hours — only runs before 6 AM ET or after 4:30 PM ET
2. Runner not active — checks session.json heartbeat
3. Watchdog running — `pgrep -f utils/watchdog.py`
4. Clean git tree — `git status --porcelain` must be empty
5. No path overlap — ticket allowed_paths vs global blocked_paths
6. .env not git-tracked

**11-step execution pipeline:**
branch → context gather → Claude API → security scan → path validation → file write
→ smoke test → Next.js build → commit+push → merge to master → ticket completion

**Security scan** (on every Claude response before any write):
- Live .env values not in generated code
- No `../` directory traversal
- No file over 500 KB
- No dangerous imports injected (subprocess, os.system, eval, exec)

**Global blocked paths** (always enforced, ticket cannot override):
`agents/`, `config/`, `tests/`, `.env`, `utils/watchdog.py`, `utils/state_manager.py`,
`utils/journal_writer.py`, `utils/event_log.py`

**Rate limiting:** max 3 tickets per run, 30s between tickets.
**Audit log:** `logs/dev_agent_audit.log` — append-only, never modified by any agent.

LaunchAgent: `deploy/com.silent.devagent.plist` — runs 5:00 AM + 5:30 PM AZ, one-shot (KeepAlive=false).

**Current status:** Dry run confirmed working — all 6 safety gates pass. Live run blocked by missing Anthropic API credits. TICKET-001 queued and ready.

---

### 15. Dev Queue Tab — `mission-control/app/dev/`

Two-column Dev tab at `/dev`:
- **Left column** — ticket queue sorted by priority, complexity-colored left borders (green/amber/red/purple)
- **Right column** — ticket detail (agent summary, file tabs, execution log, commit hash) or new ticket form

New ticket form posts to Flask `/api/tickets` — auto-assigns TICKET-00X ID, validates paths.

---

## What's Next

1. **Add Anthropic API credits** — `console.anthropic.com` → Plans & Billing
2. **Run TICKET-001 live** — `python3 utils/watchdog.py & && python3 utils/dev_agent.py`
3. **Webull data agent** — wire up real bar + options chain data to EvalContext (DataOS)
4. **Calendar tab** — trading schedule, earnings dates, FOMC, planned session days
5. **Flip cards** — AgentCard CSS 3D flip (paused from earlier this session)
6. **Paper execution** — `agents/execution_agent.py` wired to fill simulation
7. **Strike selection** — `agents/strategist.py` built out
8. **Monthly budget reset** — Finance tab: historical month-over-month tracking
