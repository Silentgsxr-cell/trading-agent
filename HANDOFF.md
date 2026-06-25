# ClawOps — Handoff Document
Drop this into a new Claude session to restore full context instantly.

---

## Master context prompt

```
Project: ClawOps — Silent's ORB paper trading system with multi-agent architecture.
Location: ~/Desktop/silent graph/trading-agent 2/

WHAT EXISTS:
Two live dashboards:
  1. Flask trading terminal  → localhost:5000  (python3 dashboard/app.py)
  2. ClawOps Mission Control → localhost:3000  (npm run dev from mission-control/)

STARTUP (AirPlay Receiver must be OFF in System Settings or port 5000 is blocked):
  cd ~/Desktop/silent\ graph/trading-agent\ 2 && python3 dashboard/app.py
  cd ~/Desktop/silent\ graph/trading-agent\ 2/mission-control && npm run dev

REPO: https://github.com/Silentgsxr-cell/trading-agent  (branch: master)

PROJECT STRUCTURE:
  agents/              v2 agent crew (signal, risk, data, review, execution)
  config/              risk_config.py + strategy_config.py
  dashboard/
    app.py             Flask app — 12 routes
    agent/             market_data, orb_calculator, risk_calculator, journal_manager, notifier
    templates/         index.html (full trading terminal UI)
  mission-control/     Next.js 14 App Router (localhost:3000)
    app/
      page.tsx         Cockpit — agent fleet rings, crew readiness, journal stats
      finance/         Finance tab — net worth, accounts, debts, budget, trading P&L
      logs/            Decision feed (state/decisions.jsonl)
      memory/          Intelligence / context viewer
      docs/            Vault docs viewer
    components/        Sidebar, StatCard, ThreeRings, AgentCard, MarketStrip
    lib/               agents.ts, journal.ts, runtime.ts, vault.ts, finance.ts, config.ts
  data/
    journal.csv        Trade journal (4 entries: 2 closed, 2 open. Net P&L: -$887.15)
    finance.json       Finance data (accounts, debts, budget — manually editable in UI)
  state/
    session.json       Runtime session state (written by Phase 2 runner)
  docs/
    AGENT_SPECS.md     Full agent specifications
    STARTUP.md         Startup commands + AirPlay fix note
    PROGRESS.md        Full build log

AGENT CREW (agents/):
  signal_agent.py    Core  — ORB breakout detection, never sizes or orders
  risk_engine.py     Core  — Veto power, sizing, circuit breakers (the governor)
  data_agent.py      Macro — Market data, VWAP, session levels, options chain
  review_agent.py    News  — Daily journal feedback, edge-decay tracking
  execution_agent.py Exec  — Only agent that can place orders; rejects unapproved trades

FLASK ROUTES (/api/market, /api/orb, /api/validate, /api/risk, /api/journal GET+POST,
              /api/news, /api/sparkline, /api/status, /api/status/halt, /api/status/reset)

MISSION CONTROL DATA FLOW:
  - Reads local files only — no Flask dependency
  - journal.csv → stats + P&L
  - agents/*.py → status (live/stub/missing derived from NotImplementedError)
  - state/session.json → engine ONLINE/OFFLINE + session metrics
  - data/finance.json → finance tab (accounts, debts, budget)
  - Vault root (/Users/silent/Desktop/silent graph) → trading docs only (denylist enforced)

RULES:
  - Never touch agents/ or config/ unless explicitly asked
  - Finance data persists to data/finance.json via Next.js Server Actions
  - state/ files written by Phase 2 runner (not yet built)
  - macOS AirPlay Receiver MUST be off for Flask to own port 5000
```

---

## Session resume prompts

### Start both servers
```
Start Flask: cd ~/Desktop/silent\ graph/trading-agent\ 2 && python3 dashboard/app.py
Start Next.js: cd ~/Desktop/silent\ graph/trading-agent\ 2/mission-control && npm run dev
Confirm localhost:5000 and localhost:3000 are both responding.
```

### If localhost:5000 is blank / returning 403
```
macOS AirPlay Receiver is intercepting port 5000.
Go to System Settings → General → AirDrop & Handoff → AirPlay Receiver → toggle OFF.
Then kill any existing python3 processes on 5000 and restart Flask.
```

### Continue building Phase 2
```
Phase 2 goal: live agent loop that writes to state/ in real time.
Files to create:
  - runner.py (orchestrates agent loop, writes state/session.json + state/decisions.jsonl)
  - agents/signal_agent.py (currently stub — NotImplementedError)
  - agents/execution_agent.py (currently stub — NotImplementedError)
  - agents/strategist.py (not yet created)
Do not modify risk_engine.py or data_agent.py — they are already live.
```

---

## Key decisions made

| Decision | Reason |
|---|---|
| Flask on 5000, Next.js on 3000 | Two separate tools — trading terminal vs cockpit |
| Mission Control reads files, not Flask API | Avoids CORS, works offline, cleaner separation |
| Agent status derived from source (NotImplementedError) | No hardcoded config to maintain |
| finance.json for finance data | Persists between sessions, editable in UI |
| Vault denylist enforced at lib level | Finance/personal docs must never surface in UI |
| AirPlay disabled | Only fix — port 5000 is hardcoded in Flask and Next.js has no dependency on it |

---

## What's next (Phase 2)

- [ ] `runner.py` — Python runner that drives the agent loop and writes `state/session.json` and `state/decisions.jsonl`
- [ ] `agents/signal_agent.py` — Real ORB signal detection (currently stub)
- [ ] `agents/execution_agent.py` — Paper order execution (currently stub)
- [ ] `agents/strategist.py` — Strike selection (not yet created)
- [ ] Broker integration (paper trading first — Alpaca or IBKR paper)
- [ ] `state/signals.jsonl` feed populating the Mission Control logs page
- [ ] Finance tab: reset monthly budget, historical budget tracking by month
