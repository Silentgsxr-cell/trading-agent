# Build Progress — ClawOps
Last updated: 2026-06-26

> **Historical changelog.** This is a point-in-time record of what was built. Sections 2, 8,
> and others describe the Flask backend on **localhost:5000** — that backend was **removed
> shortly after** (migrated into Next.js API routes). The system now runs as a single
> Next.js server on **localhost:3000**. For the current architecture see `docs/MASTER.md`.

---

## What Was Built

### 1. Agent Crew — `agents/`

Six v2 agents structured around a strict ring hierarchy:

| File | Canonical Name | Ring | Role |
|---|---|---|---|
| `signaos.py` | HAWK | Core | Multi-strategy signal engine (ORB live, 5 stubs) |
| `risk_engine.py` | VAULT | Core | Deterministic veto, position sizing, circuit breakers |
| `dataos.py` | **PULSE** | Macro | Market intelligence — bars, VWAP, session levels, options chain |
| `daitaos.py` | **INTEL** | News | Daily intelligence brief, Discord bot |
| `review_agent.py` | LEDGER | News | Daily journal feedback loop, edge-decay tracking |
| `execution_agent.py` | TRIGGER | Execution | Order submission — paper-first, only agent allowed to place orders |
| `strategist.py` | Strategist | Execution | Strike selection — not yet built |
| `utils/watchdog.py` | **WATCH** | Core | Security monitor, 7 checks every 60s |
| `utils/suggestion_agent.py` | **SAGE** | News | Suggestion intelligence, twice-daily Claude API cycle |
| `chief.py` | **CHIEF** | Core | Chief of Staff — orchestrator (not yet built) |

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

### 12. INTEL (DaiTaos) — Daily Intelligence + Discord Bot

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

### 13. WATCH (Security Watchdog) — `utils/watchdog.py`

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

### 14. DEV Agent System — `utils/dev_agent.py`

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

---

### 16. Agent Card Flip Cards — `mission-control/components/AgentCard.tsx`

CSS-only 3D flip on every agent card in the Cockpit:
- **Front**: status dot, name, governor chip, role, summary, blockers, file/line count
- **Back**: large codename, ring badge (Core/Macro/News/Execution) with color coding, full architecture description, "Output →" feeds-into line
- Pure CSS — no JavaScript, no "use client" — `perspective + preserve-3d + :hover rotateY(180deg)`
- Ring badge colors: Core=green, Macro=blue, News=amber, Execution=maroon
- `description` and `feedsInto` fields added to all 7 agents in `lib/agents.ts`
- "hover to flip" watermark on each front face
- Blank white page fix: cleared stale `.next` cache (webpack chunk 991.js mismatch)

---

### 17. Suggestion Intelligence Layer — `utils/agent_brain.py` ✅ COMPLETE

Major multi-step feature. All 10 steps complete as of 2026-06-26.

**Step 1 — Shared Brain Module** ✅ `utils/agent_brain.py`
- `AgentBrain(agent_id, agent_color)` — single import interface for all agents
- `suggest()` — creates suggestion card, appends to `data/suggestions.json`
  - Hard cap: 3 suggestions per agent per calendar day
  - Priority ≥ 9 override (always posts regardless of cap)
  - Auto-detects blocked paths → adds "locked_file" flag + ⚠️ to title
  - Posts to `#suggestions` Discord channel for priority ≥ 9
- `urgent_alert()` — routes to one of 6 Discord channel webhooks by name
- `log_reasoning()` — appends `{ts} | {agent_id} | {confidence} | {thought}` to `logs/agent_reasoning.log`
- 6 Discord channels: morning_brief, trade_alerts, watchdog, dev_agent, suggestions, agent_activity

**Step 2 — Suggestion Data Schema + Flask Routes** ✅
- `data/suggestions.json` — initialized as empty list
- 7 Flask routes added to `dashboard/app.py`:
  - `GET /api/suggestions` — all cards
  - `POST /api/suggestions` — create (from agent_brain)
  - `PATCH /api/suggestions/<id>` — update title/reasoning/progress/edits
  - `POST /api/suggestions/<id>/approve-dev` — create dev ticket, set status=dev_queue
  - `POST /api/suggestions/<id>/approve-silent` — set status=silent_queue
  - `POST /api/suggestions/<id>/discard` — requires archive_reason
  - `GET /api/suggestions/stats` — counts by status + agent
- Also fixed missing `import json` in app.py (latent bug)

**Step 3 — Suggestion Agent** ✅ `utils/suggestion_agent.py`
- Reads 9 data sources: journal.csv, session.json, decisions.jsonl, tickets.json, suggestions.json, finance.json, watchdog.log (last 20 lines), tab_usage.json, agents/ stub scan
- Each source truncated to 1000 chars — controls token cost
- ONE Claude API call (claude-sonnet-4-6, max_tokens=2000, JSON-only output)
- Posts suggestions via AgentBrain, routes cycle summary to Discord
- `--dry-run` flag: skips API call, logs would-post items
- `deploy/com.silent.suggestion.plist` — 5:00 AM + 5:30 PM AZ, KeepAlive=false
  Install: `cp deploy/com.silent.suggestion.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.silent.suggestion.plist`

**Step 4 — Agent Self-Suggestion Hooks** ✅
All hooks wrapped in `try/except` — brain failure never breaks agent logic.
- `agents/risk_engine.py` — record_close(): consecutive losses ≥ 2 → priority=7; circuit breaker → priority=8 "critical"
- `agents/signal_agent.py` — on_bar(): OR locked + no signal by window end → priority=4
- `utils/watchdog.py` — config modified during session → priority=10 "critical"; .env age > 30 days → priority=9
- `utils/dev_agent.py` — before ticket execution: posts planning suggestion (priority=5) as confirmation log

**Step 5 — Tab Usage Tracking** ✅
- `mission-control/components/TabTracker.tsx` — "use client", tracks pathname changes
  - On route change: POSTs previous tab name + duration_ms to `/api/analytics/tab`
  - Mounted in `app/layout.tsx` — covers all pages automatically
- Flask routes: `POST /api/analytics/tab`, `GET /api/analytics/tabs`
- `data/tab_usage.json` — `{tab_counts, last_updated, sessions[]}`, keeps last 1000 sessions
- Feeds suggestion agent: knows which tabs you actually use vs ignore

**Step 6 — Whiteboard UI** ✅ `mission-control/app/suggestions/`
- `page.tsx` — server component shell with `force-dynamic`
- `SuggestionBoard.tsx` — full client component:
  - Cork board texture: `#8B6914` base + 4-layer CSS gradient (fiber lines + radial highlights)
  - Header: title + unreviewed iOS badge + agent avatar strip + category chips + sort toggle
  - Agent avatar strip: circular avatars with color glow, click to filter, open-count badge
  - Sticky note cards: agent-colored background at 15% opacity, full-color header strip
  - Flag emojis displayed prominently (⚠️🚨🔴🔧🔑⏰)
  - Priority ≥ 9: `animate-riskPulse` red border + "⚠️ REQUIRES YOUR ATTENTION" banner
  - Inline editing: title + reasoning become contentEditable on "Edit" click, PATCH on blur
  - Action buttons: Dev (blue #2196f3), Silent (maroon #8B1A1A), Edit (grey), Discard (✕)
  - Discard requires reason via modal (required field)
  - QueueSidebar component embedded — Dev / Silent tabs with Active / Archive sub-tabs
  - Silent queue items: draggable 0–100 progress slider, auto-completes at 100%
  - Dev queue items: shows linked ticket ID
  - Archive tab: completed (green) + discarded (grey) with reason always shown
  - Sidebar toggle button (‹/›) on right edge
- Build passes ✅ — `/suggestions` route included in build output

**Step 7 — Collapsible Flip-Card Sidebar** ✅ `mission-control/app/suggestions/SuggestionBoard.tsx`
- Two vertically stacked flip cards: DEV (blue #2196f3) and SILENT (maroon #8B1A1A)
- Click-to-flip via JS state + inline `style.transform = rotateY(180deg)` (not hover CSS)
- `transform-style: preserve-3d` + `backface-visibility: hidden` on both faces
- Front face: colored avatar + section label + active/archived count bubble + "Click to view queue" hint
- Back face: Active | Archive sub-tabs with active route indicator
  - Active items: agent dot + title (clamp-2) + circular SVG progress ring (r=11, dashoffset)
  - Silent active: draggable slider 0–100%; at 100% triggers inline note prompt → auto-archive on confirm
  - Dev active: ticket ID chip (blue monospace)
  - Archive: COMPLETED (green) / DISCARDED (grey) chip + completed_by + archive_reason + timestamp
- localStorage persistence: `clawops-dev-flipped`, `clawops-silent-flipped`, `clawops-dev-subtab`, `clawops-silent-subtab`, `clawops-sidebar-open`
- `QueueSidebar` wrapper component composes both flip cards, filters by queue field
- `onComplete(id, note)` handler: archives with note at 100% progress

**Step 8 — Sidebar Nav** ✅ `mission-control/components/Sidebar.tsx`
- Converted to `"use client"` with `usePathname()` for active route highlighting
- Suggestions link added between Intelligence and Research: `{ href: "/suggestions", label: "Suggestions", glyph: "📌" }`
- Badge counter: polls `GET /api/suggestions/stats` every 30s, shows `unreviewed` count as iOS-style maroon badge
- Active route: `bg-navy-700/80` background + left maroon accent bar + highlighted glyph
- Falls back silently when Flask is offline (badge stays at 0)

**Step 9 — Discord Routing Cleanup** ✅
- `utils/daitaos.py` — `DISCORD_WEBHOOK_URL` → `DISCORD_MORNING_BRIEF_WEBHOOK` (line 29 + error string)
- `utils/dev_agent.py` — `DISCORD_WEBHOOK_URL` → `DISCORD_DEV_AGENT_WEBHOOK` (line 51 only; line 181 `_load_secrets()` scan list left unchanged)
- `utils/watchdog.py` — `DISCORD_WEBHOOK_URL` → `DISCORD_WATCHDOG_WEBHOOK` (line 81 only; line 91 `_SECRET_VARS` scan list left unchanged)
- All 6 dedicated channels now in use across the system

**Step 10 — Final Build Verification** ✅
- `npm run build` — all 10 routes compile clean, `/suggestions` at 6.41 kB, zero TypeScript errors
- `docs/PROGRESS.md` updated — section 17 marked complete
- `HANDOFF.md` updated — suggestion layer complete, next priorities updated

---

### 18. Phase 2 — Agent Canonical Renames ✅ COMPLETE

Display-name renames throughout the codebase. Python files NOT renamed.

| Old Name | Canonical Name | File (unchanged) |
|---|---|---|
| DataOS | **PULSE** | `agents/dataos.py` |
| DaiTaos | **INTEL** | `utils/daitaos.py` |
| Watchdog | **WATCH** | `utils/watchdog.py` |
| Suggestion Agent | **SAGE** | `utils/suggestion_agent.py` |
| HAWK | HAWK (unchanged) | `agents/signaos.py` |
| VAULT | VAULT (unchanged) | `agents/risk_engine.py` |
| TRIGGER | TRIGGER (unchanged) | `agents/execution_agent.py` |
| LEDGER | LEDGER (unchanged) | `agents/review_agent.py` |
| Dev Agent | DEV (unchanged) | `utils/dev_agent.py` |
| — | **CHIEF** (new, stub) | `agents/chief.py` |

Files updated:
- `mission-control/lib/agents.ts` — PULSE/INTEL names, added WATCH/SAGE/CHIEF entries with `dir` override for utils/ files
- `utils/agent_brain.py` — AGENT_AVATARS updated with canonical names + legacy aliases
- `docs/PROGRESS.md` + `HANDOFF.md` — agent name table updated

WATCH and SAGE now appear in the Cockpit crew diagram (core and news rings).
CHIEF shows as "missing" — placeholder until Phase 3 builds it.

---

## What's Next

1. **Add Anthropic API credits** — `console.anthropic.com` → Plans & Billing → run TICKET-001 live
2. **Populate Discord webhooks** — add 6 channel webhook URLs to `.env`
3. **Install suggestion LaunchAgent** — `cp deploy/com.silent.suggestion.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.silent.suggestion.plist`
4. **Webull data agent** — wire DataOS to real bar + options chain data; feed EvalContext
5. **Calendar tab** — trading schedule, earnings, FOMC, planned session days
6. **Paper execution** — `agents/execution_agent.py` wired to fill simulation
7. **Strike selection** — `agents/strategist.py`
