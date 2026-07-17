# ClawOps — Handoff Document
Drop this into a new Claude session to restore full context instantly.

> **⚠️ Updated 2026-07-16:** Flask (port 5000) was removed — everything now runs as **one
> Next.js server on localhost:3000**. Sections below that mention a Flask dashboard or two
> servers are historical. `docs/MASTER.md` is the canonical, current reference.

---

## Project location

```
/Users/silent/trading-agent 2/
```

---

## Master context prompt

```
Project: ClawOps — Silent's ORB paper trading system with multi-agent architecture.
Location: /Users/silent/trading-agent 2/

REPO: https://github.com/Silentgsxr-cell/trading-agent  (branch: master)

ONE LIVE DASHBOARD:
  ClawOps Mission Control → localhost:3000  (cd mission-control && npm run dev)
  (Flask on 5000 was removed — all API routes now live inside Next.js at
   mission-control/app/api/. There is no separate backend to start.)

STARTUP:
  cd "/Users/silent/trading-agent 2/mission-control" && npm run dev

BACKGROUND PROCESSES (start manually each session):
  cd "/Users/silent/trading-agent 2"
  python3 utils/watchdog.py &       # security + integrity monitor
  python3 utils/daitaos_bot.py      # Discord bot (!brief, !status, etc.)
  python3 utils/dev_agent.py        # autonomous dev agent (needs Anthropic credits)
```

---

## What is fully built

### Core trading system
- `runner.py` — autonomous ORB loop, weekdays 9:30–16:00 ET, polls yfinance every 30s
- `agents/signaos.py` — **HAWK** signal engine, 6-strategy registry (ORB live, 5 stubs)
- `agents/risk_engine.py` — **VAULT**, circuit breakers, position sizing
- `agents/dataos.py` — **PULSE** (was DataOS), market intelligence stub
- `utils/daitaos.py` — **INTEL** (was DaiTaos), daily brief + Discord bot
- `utils/watchdog.py` — **WATCH** (was Watchdog), security monitor
- `utils/suggestion_agent.py` — **SAGE** (was Suggestion Agent), twice-daily advisor
- `config/risk_config.py` — max 3 trades/day, 1% risk/trade, 3% daily loss limit

### Single-writer rule (all shared files serialized via filelock)
- `utils/state_manager.py` → owns `state/session.json`
- `utils/event_log.py` → owns `state/decisions.jsonl`
- `utils/journal_writer.py` → owns `data/journal.csv`

### Security layer
- `utils/watchdog.py` — 7 checks every 60s (key exposure, session integrity, file integrity,
  config tamper, heartbeat, .env git tracking, git author audit)
- `deploy/com.silent.watchdog.plist` — LaunchAgent (start at login, KeepAlive=true)
  Install: `cp deploy/com.silent.watchdog.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.silent.watchdog.plist`

### Dev agent system
- `utils/dev_agent.py` — autonomous ticket executor (Claude API + git pipeline)
- `data/tickets.json` — ticket database
- `deploy/com.silent.devagent.plist` — LaunchAgent (5:00 AM + 5:30 PM AZ, one-shot)
  Install: `cp deploy/com.silent.devagent.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.silent.devagent.plist`

### Dashboard
- `mission-control/` — Next.js 14, single server on localhost:3000. Pages: Cockpit, Logs, Intelligence, Research, Finance, Dev Queue. All API routes live in `mission-control/app/api/` (the old Flask `dashboard/app.py` was removed).

### Discord
- `utils/daitaos.py` — **INTEL**: 9-section morning brief (incl. dev agent overnight summary)
- `utils/daitaos_bot.py` — bot: !brief, !tsla, !watchlist, !status, !rules, !pnl,
  !config, !ticket status/pause/resume/log, !approve, !revert, !help

---

## Current state — session 2026-06-27

### Phase 2 — Agent Canonical Renames ✅ COMPLETE

| Old Name | Canonical | File (unchanged) |
|---|---|---|
| DataOS | PULSE | `agents/dataos.py` |
| DaiTaos | INTEL | `utils/daitaos.py` |
| Watchdog | WATCH | `utils/watchdog.py` |
| Suggestion Agent | SAGE | `utils/suggestion_agent.py` |
| _(new)_ | CHIEF | not yet built |

Updated: `lib/agents.ts` (names + WATCH/SAGE/CHIEF entries), `utils/agent_brain.py` (AGENT_AVATARS), docs.

---

### Suggestion Intelligence Layer — ✅ COMPLETE (all 10 steps)

| Step | File | Status |
|---|---|---|
| 1 — Shared Brain | `utils/agent_brain.py` | ✅ |
| 2 — Data Schema + Flask Routes | `data/suggestions.json` + 7 routes in `dashboard/app.py` | ✅ |
| 3 — Suggestion Agent | `utils/suggestion_agent.py` + `deploy/com.silent.suggestion.plist` | ✅ |
| 4 — Agent Self-Hooks | risk_engine, signal_agent, watchdog, dev_agent | ✅ |
| 5 — Tab Tracking | `components/TabTracker.tsx` + Flask analytics routes | ✅ |
| 6 — Whiteboard UI | `app/suggestions/page.tsx` + `SuggestionBoard.tsx` | ✅ |
| 7 — Flip-card Sidebar | `QueueFlipCard` inside `SuggestionBoard.tsx` — Dev + Silent flip cards | ✅ |
| 8 — Sidebar Nav Badge | `components/Sidebar.tsx` — "use client", Suggestions + polling badge | ✅ |
| 9 — Discord Routing | daitaos.py → MORNING_BRIEF, dev_agent.py → DEV_AGENT, watchdog.py → WATCHDOG | ✅ |
| 10 — Final Build | `npm run build` clean, docs updated, committed to master | ✅ |

### .env — needs 6 webhook URLs filled in manually
```
DISCORD_MORNING_BRIEF_WEBHOOK=   ← daitaos.py (morning brief)
DISCORD_TRADE_ALERTS_WEBHOOK=    ← reserved for execution agent
DISCORD_WATCHDOG_WEBHOOK=        ← watchdog.py
DISCORD_DEV_AGENT_WEBHOOK=       ← dev_agent.py
DISCORD_SUGGESTIONS_WEBHOOK=     ← priority ≥ 9 suggestions
DISCORD_AGENT_ACTIVITY_WEBHOOK=  ← suggestion_agent cycle summaries
```

### Install suggestion LaunchAgent
```
cp deploy/com.silent.suggestion.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.silent.suggestion.plist
```

### Dev agent status
- **Dry run confirmed working** — all 6 safety gates pass
- **Live run blocked** — Anthropic API account has no credits
- **TICKET-001 queued** — status: open, ready to run once credits added
- **To run live:**
  ```
  cd "/Users/silent/trading-agent 2"
  python3 utils/watchdog.py &
  sleep 2
  python3 utils/dev_agent.py
  ```

### Anthropic API key
- Fresh key is in `/Users/silent/trading-agent 2/.env` as `ANTHROPIC_API_KEY`
- Account needs credits at `console.anthropic.com` → Plans & Billing
- Key was set via terminal (not pasted in chat) — safe

### .env location
```
/Users/silent/trading-agent 2/.env
```
Contains: DISCORD_WEBHOOK_URL, DISCORD_BOT_TOKEN, ANTHROPIC_API_KEY
Never committed to git. Watchdog checks this every cycle.

### LaunchAgents installed
- `com.silent.watchdog.plist` — copied to ~/Library/LaunchAgents/ ✓
- `com.silent.devagent.plist` — copied to ~/Library/LaunchAgents/ ✓
- `com.silent.suggestion.plist` — in `deploy/`, not yet installed
- All need `launchctl load` if not already loaded (Sage blocks this — user must run it manually)

---

## Rules — never break these

| Rule | Reason |
|---|---|
| Never modify `agents/` or `config/` unless explicitly asked | Risk parameters and agent logic are production |
| Never commit `.env` | Contains live secrets — watchdog auto-flags if tracked |
| Never commit `state/session.json` or `state/decisions.jsonl` | Runtime state, excluded in .gitignore |
| All writes to shared files go through `utils/` | Single-writer rule prevents corruption |
| Dev agent never writes to `agents/`, `config/`, `tests/`, or core `utils/` | Hard-blocked in global path list |

---

## Project structure

```
/Users/silent/trading-agent 2/
├── runner.py                  # autonomous trading loop (run in terminal)
├── agents/
│   ├── signaos.py             # HAWK — signal engine (ORB live)
│   ├── risk_engine.py         # VAULT — veto + sizing (governor)
│   ├── dataos.py              # DataOS — data stub
│   ├── daitaos.py             # DaiTaos — daily brief crew registration
│   ├── review_agent.py        # LEDGER — journal feedback stub
│   ├── execution_agent.py     # TRIGGER — order execution stub
│   └── strategies/
│       ├── base.py            # BaseStrategy, EvalContext, SignalOutput
│       ├── orb.py             # ORB strategy (live)
│       └── *.py               # 5 stub strategies
├── config/
│   ├── risk_config.py         # STARTING_BALANCE=1000, PER_TRADE_RISK=1%, MAX_TRADES=3
│   └── strategy_config.py     # SYMBOL=TSLA, ORB window, watchlist
├── utils/
│   ├── state_manager.py       # owns state/session.json (filelock)
│   ├── event_log.py           # owns state/decisions.jsonl (filelock)
│   ├── journal_writer.py      # owns data/journal.csv (filelock)
│   ├── watchdog.py            # security monitor (7 checks, 60s cycle)
│   ├── dev_agent.py           # autonomous dev agent (6 safety gates, Claude API)
│   ├── daitaos.py             # morning brief (9 sections)
│   └── daitaos_bot.py         # Discord bot
├── dashboard/
│   ├── app.py                 # Flask (17 routes)
│   └── agent/                 # market_data, orb_calculator, risk_calculator, notifier
├── mission-control/           # Next.js 14 (localhost:3000)
│   ├── app/
│   │   ├── page.tsx           # Cockpit
│   │   ├── finance/           # Finance tab
│   │   ├── dev/               # Dev Queue tab
│   │   ├── logs/              # Decision feed
│   │   ├── memory/            # Intelligence
│   │   └── docs/              # Research
│   ├── components/            # Sidebar, AgentCard, ThreeRings, StatCard, MarketStrip
│   └── lib/                   # agents, journal, runtime, vault, finance, tickets
├── data/
│   ├── tickets.json           # dev agent ticket database
│   ├── journal.csv            # trade journal
│   └── finance.json           # finance data (accounts, debts, budget)
├── state/                     # runtime only — excluded from git
│   ├── session.json
│   ├── decisions.jsonl
│   └── signals.jsonl
├── deploy/
│   ├── com.silent.watchdog.plist
│   └── com.silent.devagent.plist
├── logs/
│   ├── watchdog.log
│   └── dev_agent_audit.log
└── docs/
    ├── PROGRESS.md
    ├── AGENT_SPECS.md
    └── STARTUP.md
```

---

## Next priorities (in order)

1. **Add Anthropic API credits** → `console.anthropic.com` → Plans & Billing → run TICKET-001 live
2. **Populate Discord webhooks** — fill 6 vars in `.env` (see above)
3. **Install suggestion LaunchAgent** — copy plist + `launchctl load`
4. **Webull data agent** — wire DataOS to real bar + options chain data; feed EvalContext
5. **Calendar tab** — trading schedule, earnings, FOMC, planned session days
6. **Paper execution** — `agents/execution_agent.py` wired to journal_writer fill simulation
7. **Strike selection** — `agents/strategist.py`

---

## Key decisions made

| Decision | Reason |
|---|---|
| Single Next.js server on 3000 | Flask (5000) was merged into Next.js API routes — one server, no CORS, simpler |
| Mission Control reads files directly | No CORS, works offline, cleaner separation |
| Agent status derived from source (NotImplementedError) | No hardcoded config to maintain |
| Single-writer rule via filelock | Prevents state corruption from concurrent processes |
| Dev agent blocked from agents/ and config/ | Risk parameters must never be autonomously changed |
| Safety gates check watchdog is running | Dev agent won't touch code if the guard is down |
| Anthropic credits needed | Key is valid and safe; account just needs funding |
