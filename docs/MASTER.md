# ClawOps — Master Reference Document
> **Last updated:** 2026-07-16 | **Branch:** master | **Repo:** [Silentgsxr-cell/trading-agent](https://github.com/Silentgsxr-cell/trading-agent)

---

## Overview

ClawOps is Silent's autonomous ORB paper trading system built on a multi-agent architecture. It runs a daily trading loop, monitors system security, routes intelligence to Discord, and exposes everything through a single Next.js Mission Control dashboard.

**One server. One codebase. No Flask.**
- `localhost:3000` — Next.js 14 Mission Control (the only UI)
- All API routes live inside Next.js at `mission-control/app/api/`
- Flask trading terminal has been removed

---

## Changelog

Most recent first. For full detail on any entry, see the git log or the dated session log in `docs/SESSION_LOG_*.md`.

### 2026-07-16
- **Fixed a real bug** in `lib/agents.ts`: the stub/live detector matched `raise NotImplementedError` anywhere in a file, so CHIEF and SAGE — whose own source contains that exact string as a literal (they scan other agents for it) — were mislabeled "stub." Regex anchored to line start.
- **Added live agent-status plumbing**: `AgentBrain.start_task/update_task/finish_task/error()` (`utils/agent_brain.py`) writes to `state/agent_status.json` (filelock-protected). New `/api/agents` route exposes it; `AgentCard` and a new Sidebar crew-health strip render it (thinking/idle/error, progress, queue, confidence). Wired into CHIEF, INTEL, SAGE, WATCH.
- **Sidebar reorganized** into department groups (Trading / Intelligence / Personal / System); fixed a dead `localhost:5000` fetch for the suggestion badge, left over from the Flask migration.
- **Added a Notes section to the Journal tab** — add/remove free-form notes, `data/journal_notes.json` via `/api/journal/notes`.
- **CHIEF's and SAGE's LaunchAgents installed** and confirmed armed via `launchctl print` (CHIEF: 6:00 AM / 4:30 PM AZ, SAGE: 5:00 AM / 5:30 PM AZ).
- **Found: `ANTHROPIC_API_KEY` is invalid/revoked** — live run returns `HTTP 401 authentication_error: API key is invalid`, not a credits/billing error as previously assumed. A fresh key from `console.anthropic.com` is required; credits still matter after that.
- 6 Discord webhook URLs provided by the operator but not yet written to `.env` — blocked by a local security hook on direct `.env` edits, needs to be done manually.
- Renamed the vault symlink `trading-agent 3` → `trading-agent (shortcut)`; fixed `.obsidianignore` and `deploy/com.silent.chief.plist`, both of which still referenced the old symlink path.
- Freed ~42GB of disk space (an unused Parallels Windows 11 VM + its ISO installer, plus Downloads clutter) after the machine hit `ENOSPC`.

---

## Project Location

```
~/trading-agent 2/
```

Symlinked into Obsidian vault at:
```
~/Desktop/silent graph/trading-agent (shortcut)  →  ~/trading-agent 2
```
> Renamed from `trading-agent 3` on 2026-07-16 to make clear it's a shortcut, not a second project.

> **Why home root?** macOS TCC blocks LaunchAgents from accessing `~/Desktop/` without Full Disk Access (system Python shims are greyed out in FDA settings). Home root has no TCC restriction.

---

## How to Start

```bash
# Mission Control (only server needed)
cd ~/trading-agent\ 2/mission-control && npm run dev
# Opens at http://localhost:3000

# Background agents (optional — start manually or via LaunchAgents)
cd ~/trading-agent\ 2
python3 utils/watchdog.py &        # WATCH — security monitor
python3 utils/daitaos_bot.py       # INTEL — Discord bot
python3 runner.py                  # Trading loop (weekdays 9:30–16:00 ET)
```

> **AirPlay Receiver must be OFF** — System Settings → General → AirDrop & Handoff.
> macOS hijacks port 5000 otherwise (no longer relevant since Flask is removed).

---

## Architecture

```
~/trading-agent 2/
├── runner.py                      # Autonomous ORB loop (weekdays 9:30–16:00 ET)
├── agents/
│   ├── signaos.py                 # HAWK — signal engine (ORB live, 5 stubs)
│   ├── risk_engine.py             # VAULT — circuit breakers + position sizing
│   ├── dataos.py                  # PULSE — market intelligence stub
│   ├── execution_agent.py         # TRIGGER — order execution stub
│   ├── review_agent.py            # LEDGER — journal feedback stub
│   ├── chief.py                   # CHIEF — Chief of Staff orchestrator (live, runs 6:00 AM + 4:30 PM AZ)
│   └── strategies/
│       ├── orb.py                 # ORB strategy (live)
│       └── *.py                   # 5 stub strategies
├── utils/
│   ├── watchdog.py                # WATCH — 7-check security monitor (60s cycle)
│   ├── daitaos.py                 # INTEL — morning brief (9 sections)
│   ├── daitaos_bot.py             # Discord bot (!brief, !status, !pnl, etc.)
│   ├── dev_agent.py               # Autonomous ticket executor (Claude API)
│   ├── suggestion_agent.py        # SAGE — twice-daily advisor
│   ├── agent_brain.py             # Shared agent registry + avatars
│   ├── state_manager.py           # Owns state/session.json (filelock)
│   ├── event_log.py               # Owns state/decisions.jsonl (filelock)
│   └── journal_writer.py          # Owns data/journal.csv (filelock)
├── config/
│   ├── risk_config.py             # STARTING_BALANCE=1000, 1% risk/trade, 3 max trades
│   └── strategy_config.py         # SYMBOL=TSLA, ORB window, watchlist
├── mission-control/               # Next.js 14 — localhost:3000
│   ├── app/
│   │   ├── chief/page.tsx         # Cockpit (home) — reads logs/chief_assessment.json
│   │   ├── life/page.tsx          # Life — Calendar, Tasks, Goals, Finance
│   │   ├── dev/DevClient.tsx      # Dev Queue — ticket system
│   │   ├── suggestions/           # Suggestion whiteboard
│   │   ├── finance/               # Finance tab
│   │   ├── logs/                  # Journal — Decision feed, journaled trades, Notes
│   │   │   └── NotesPanel.tsx     # Add/remove free-form notes (data/journal_notes.json)
│   │   ├── memory/                # Intelligence
│   │   ├── markets/               # Markets + TradingView chart
│   │   └── api/                   # ← All API routes (see below), incl. api/agents/, api/journal/notes/
│   ├── components/
│   │   ├── Sidebar.tsx            # Grouped nav (Trading/Intelligence/Personal/System) + crew-health strip
│   │   ├── AgentCard.tsx          # Renders live status (thinking/idle/error) from AgentBrain
│   │   ├── TabTracker.tsx         # Analytics tracking
│   │   └── ...
│   └── lib/
│       ├── dataPath.ts            # Shared JSON read/write utility
│       ├── agents.ts              # Agent registry + live-status merge (reads state/agent_status.json)
│       ├── chief.ts               # Reads logs/chief_assessment.json for the /chief page
│       ├── finance.ts
│       ├── tickets.ts
│       └── ...
├── data/
│   ├── tickets.json               # Dev agent ticket database
│   ├── suggestions.json           # Suggestion cards
│   ├── goals.json                 # Life goals
│   ├── finance.json               # Accounts, debts, budget
│   ├── journal.csv                # Trade journal
│   ├── journal_notes.json         # Journal tab free-form notes
│   └── tab_usage.json             # Tab analytics
├── state/                         # Runtime only — excluded from git
│   ├── session.json
│   ├── decisions.jsonl
│   ├── signals.jsonl
│   └── agent_status.json          # Live agent status (AgentBrain start_task/finish_task/error)
├── deploy/
│   ├── com.silent.watchdog.plist
│   ├── com.silent.devagent.plist
│   ├── com.silent.suggestion.plist
│   └── com.silent.chief.plist     # not yet installed to ~/Library/LaunchAgents
└── logs/
    ├── watchdog.log
    ├── dev_agent_audit.log
    └── chief_assessment.json      # Written by chief.py, read by mission-control/app/chief/page.tsx
```

---

## Next.js API Routes

All routes are relative — no Flask, no external server dependency.

### Suggestions
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/suggestions` | List all suggestion cards |
| POST | `/api/suggestions` | Create new card |
| GET | `/api/suggestions/stats` | Count by status + agent |
| GET/PATCH | `/api/suggestions/[id]` | Get or update a card |
| POST | `/api/suggestions/[id]/approve-dev` | Dev approves |
| POST | `/api/suggestions/[id]/approve-silent` | Silent approves |
| POST | `/api/suggestions/[id]/discard` | Discard with reason |

### Tickets
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/tickets` | List all tickets |
| POST | `/api/tickets` | Create ticket |
| GET | `/api/tickets/[id]` | Get single ticket |
| POST | `/api/tickets/[id]/approve` | Approve ticket |
| POST | `/api/tickets/[id]/revert` | Revert to open |

### Life
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/life/calendar` | Apple Calendar events (next 7 days via osascript) |
| POST | `/api/life/calendar/event` | Create Calendar event |
| GET | `/api/life/tasks` | Apple Reminders — incomplete tasks |
| DELETE | `/api/life/tasks/[id]` | Delete reminder by title |
| GET | `/api/life/goals` | List goals |
| POST | `/api/life/goals` | Create goal |
| PATCH | `/api/life/goals/[id]` | Update / mark done |
| DELETE | `/api/life/goals/[id]` | Delete goal |
| GET | `/api/life/finance` | Accounts + debts + net worth |

### Finance
| Method | Route | Description |
|--------|-------|-------------|
| PATCH | `/api/finance/accounts/[id]` | Update account balance |
| PATCH | `/api/finance/debts/[id]` | Update debt balance |

### Analytics
| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/analytics/tab` | Log tab view event |

### Journal
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/journal/notes` | List all notes |
| POST | `/api/journal/notes` | Create a note |
| DELETE | `/api/journal/notes/[id]` | Remove a note |

### Agents
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/agents` | Full crew list + live status (from `state/agent_status.json`) + crew health summary |

---

## Agent Roster

| Canonical Name | File | Role | Status |
|---|---|---|---|
| **HAWK** | `agents/signaos.py` | Signal engine — ORB strategy + 5 stubs | Live (ORB active) |
| **VAULT** | `agents/risk_engine.py` | Risk governor — circuit breakers, position sizing | Live |
| **PULSE** | `agents/dataos.py` | Market intelligence | Stub |
| **TRIGGER** | `agents/execution_agent.py` | Order execution | Stub |
| **LEDGER** | `agents/review_agent.py` | Journal feedback | Stub |
| **WATCH** | `utils/watchdog.py` | 7-check security monitor (60s) | Live — LaunchAgent |
| **INTEL** | `utils/daitaos.py` | 9-section morning brief + Discord | Live |
| **SAGE** | `utils/suggestion_agent.py` | Twice-daily advisor | Live — LaunchAgent |
| **CHIEF** | `agents/chief.py` | Chief of Staff — reads all agent state, one Claude API call, writes `logs/chief_assessment.json` for the `/chief` cockpit home page | Live — LaunchAgent installed and armed. Real (non-dry-run) calls currently fail: `ANTHROPIC_API_KEY` is invalid, needs regeneration |

---

## LaunchAgents (Background Services)

All services point to `~/trading-agent 2/`. Plist source files live in `deploy/`.

| Service | Trigger | Script |
|---|---|---|
| `com.silent.watchdog` | Login + KeepAlive | `utils/watchdog.py` |
| `com.silent.dataos.bot` | Login + KeepAlive | `utils/daitaos_bot.py` |
| `com.silent.dataos` | 6:20 AM daily | `utils/daitaos.py` |
| `com.silent.dataos.sync` | 4:30 PM daily | `utils/daitaos_sync.py` |
| `com.silent.devagent` | 5:00 AM + 5:30 PM | `utils/dev_agent.py` |
| `com.silent.suggestion` | 5:00 AM + 5:30 PM | `utils/suggestion_agent.py` — installed 2026-07-16, confirmed armed via `launchctl print` |
| `com.silent.chief` | 6:00 AM + 4:30 PM AZ | `agents/chief.py` — installed 2026-07-16, confirmed armed via `launchctl print` |

**Reinstall after any path change:**
```bash
cd ~/trading-agent\ 2
cp com.silent.dataos*.plist ~/Library/LaunchAgents/
cp deploy/com.silent.*.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.silent.watchdog.plist
launchctl load ~/Library/LaunchAgents/com.silent.dataos.bot.plist
```

---

## Watchdog Checks (WATCH)

Runs every 60 seconds. All 7 must pass:

| # | Check | What it catches |
|---|---|---|
| 1 | Key exposure | API keys printed to logs or state files |
| 2 | Session integrity | session.json schema valid |
| 3 | File integrity | Core files not tampered |
| 4 | Config tamper | risk_config.py + strategy_config.py unchanged |
| 5 | Heartbeat freshness | runner.py heartbeat not stale |
| 6 | .env security | .env not git-tracked |
| 7 | Git history audit | No unexpected authors in commit history |

---

## Dev Agent System

Autonomous ticket executor. Reads `data/tickets.json`, uses Claude API to generate code, runs 6 safety gates before touching any file.

**6 Safety Gates (all must pass):**
1. WATCH is running
2. No open positions (runner not mid-trade)
3. Ticket is approved status
4. Target file not in blocked paths
5. Diff size within limits
6. Dry-run passes

**Blocked paths (dev agent can never touch):**
- `agents/`, `config/`, `tests/`, `utils/state_manager.py`, `utils/event_log.py`, `utils/journal_writer.py`

**To run:**
```bash
cd ~/trading-agent\ 2
python3 utils/watchdog.py &
sleep 2
python3 utils/dev_agent.py
```

> **Blocked:** `ANTHROPIC_API_KEY` is invalid (401) — needs a fresh key at `console.anthropic.com` → Settings → API Keys, then credits at Plans & Billing.

---

## Discord Bot Commands

Bot runs via `utils/daitaos_bot.py`. Invite token in `.env` as `DISCORD_BOT_TOKEN`.

| Command | Description |
|---|---|
| `!brief` | Trigger morning brief |
| `!status` | System health + agent states |
| `!tsla` | TSLA quote |
| `!watchlist` | Watchlist quotes |
| `!pnl` | Today's P&L |
| `!rules` | Risk rules summary |
| `!config` | Current risk config |
| `!ticket status` | Ticket queue status |
| `!ticket pause/resume` | Pause/resume dev agent |
| `!approve TICKET-XXX` | Approve a ticket |
| `!revert TICKET-XXX` | Revert last ticket commit |
| `!help` | Full command list |

---

## .env Variables

File: `~/trading-agent 2/.env` — never committed to git.

```
ANTHROPIC_API_KEY=           # Claude API — dev agent, CHIEF, SAGE
DISCORD_BOT_TOKEN=           # Discord bot login
DISCORD_MORNING_BRIEF_WEBHOOK=    # daitaos.py channel
DISCORD_TRADE_ALERTS_WEBHOOK=     # reserved (execution agent)
DISCORD_WATCHDOG_WEBHOOK=         # watchdog.py alerts
DISCORD_DEV_AGENT_WEBHOOK=        # dev_agent.py updates
DISCORD_SUGGESTIONS_WEBHOOK=      # priority ≥ 9 suggestions
DISCORD_AGENT_ACTIVITY_WEBHOOK=   # suggestion_agent cycle summaries
```

> **`ANTHROPIC_API_KEY` is currently invalid** (HTTP 401 `authentication_error`, confirmed 2026-07-16) — not a credits/billing issue as earlier notes assumed. Generate a fresh key at `console.anthropic.com` → Settings → API Keys.
>
> The 6 `DISCORD_*_WEBHOOK` vars are still empty as of 2026-07-16 — URLs were provided by the operator but not yet written to `.env`.

---

## Risk Rules (never change without explicit intent)

| Rule | Value |
|---|---|
| Starting balance | $1,000 |
| Risk per trade | 1% ($10) |
| Max trades per day | 3 |
| Daily loss limit | 3% ($30) |
| Symbol | TSLA |
| ORB window | 9:30–9:45 AM ET |

---

## Single-Writer Rule

All shared state files are owned by one utility. No other file writes to them directly.

| File | Owner |
|---|---|
| `state/session.json` | `utils/state_manager.py` |
| `state/decisions.jsonl` | `utils/event_log.py` |
| `data/journal.csv` | `utils/journal_writer.py` |
| `state/agent_status.json` | `utils/agent_brain.py` (`AgentBrain._write_status`, filelock) — many agents write, all through this one function |

---

## Rules — Never Break

| Rule | Reason |
|---|---|
| Never modify `agents/` or `config/` unless explicitly asked | Risk parameters and agent logic are production |
| Never commit `.env` | Contains live secrets — watchdog flags if tracked |
| Never commit `state/session.json` or `state/decisions.jsonl` | Runtime state, excluded in .gitignore |
| All shared file writes go through `utils/` | Single-writer rule prevents corruption |
| Dev agent blocked from `agents/`, `config/`, `tests/`, core `utils/` | Risk parameters must never be autonomously changed |
| WATCH must be running before dev agent runs | Safety gate #1 |
| AirPlay Receiver must be OFF | (Historical — Flask on 5000 is now removed) |

---

## Build Status

| Milestone | Status |
|---|---|
| Initial trading dashboard | ✅ |
| runner.py — live ORB loop | ✅ |
| HAWK signal engine + strategy framework | ✅ |
| VAULT risk engine | ✅ |
| Single-writer state system | ✅ |
| Security watchdog (7 checks) | ✅ |
| Dev agent + ticket system | ✅ |
| Discord bot (INTEL) | ✅ |
| Suggestion intelligence layer (10 steps) | ✅ |
| Mission Control Next.js dashboard | ✅ |
| Life tab (Calendar, Tasks, Goals, Finance) | ✅ |
| Flask → Next.js API migration | ✅ |
| Apple Calendar via osascript | ✅ (wired, needs macOS permission grant) |
| CHIEF — master orchestrator | ✅ Live, LaunchAgent installed and armed |
| Live agent-status plumbing (AgentBrain → `/api/agents` → Sidebar/AgentCard) | ✅ (2026-07-16) |
| Journal Notes (add/remove) | ✅ (2026-07-16) |
| Webull data feed (PULSE live) | ⬜ Not started |
| Paper execution (TRIGGER live) | ⬜ Not started |
| Calendar tab — trading schedule / FOMC | ⬜ Not started |
| Strike selection (STRATEGIST) | ⬜ Not started |

---

## Next Priorities

1. **Regenerate `ANTHROPIC_API_KEY`** — current key is invalid/revoked (401), not a credits issue. Get a fresh one at `console.anthropic.com` → Settings → API Keys, add credits at Plans & Billing. Blocks CHIEF, SAGE, and the dev agent's real (non-dry-run) runs, including TICKET-001.
2. **Write the 6 Discord webhook URLs into `.env`** — provided by the operator 2026-07-16, not yet saved
3. **Apple Calendar permission** — grant `npm` / Node access in System Settings → Privacy → Calendars
4. **Webull data agent** — wire PULSE to real bar + options chain data
5. **Paper execution** — wire TRIGGER to journal_writer fill simulation

---

## Obsidian Vault

Vault root: `~/Desktop/silent graph/`

`.obsidianignore` at vault root excludes all code/log/data folders so the graph stays clean:
```
trading-agent (shortcut)/mission-control
trading-agent (shortcut)/.git
trading-agent (shortcut)/__pycache__
trading-agent (shortcut)/data
trading-agent (shortcut)/logs
trading-agent (shortcut)/state
trading-agent (shortcut)/node_modules
trading-agent (shortcut)/sim
trading-agent (shortcut)/tests
trading-agent (shortcut)/dashboard/agent
trading-simm-play
```
