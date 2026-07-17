# ClawOps — Context Handoff (2026-07-16)

Paste this whole document to any new AI session (Claude, Claude Code, GPT, etc.) to bring it fully up to speed. Written by a Cowork session that had direct read/write access to the live project folder — everything below was verified against the actual files, not assumed.

---

## 1. What ClawOps is

A Personal Operating System, not just a trading bot. Trading (ORB paper-trading TSLA/QQQ/MSFT/AMZN via a Python multi-agent backend) is the current focus, but the long-term vision is a full daily operating system: trading + personal productivity + a persistent knowledge layer, run by a "crew" of specialized agents that research, monitor, and recommend — the operator (Silent) remains the final decision-maker on everything. Agents are meant to feel like coworkers with a clear mission, inputs/outputs, and explicit authority boundaries — not background scripts.

Discord is the notification layer ("Signal Agent: A-tier TSLA setup detected"). The Next.js dashboard ("Mission Control") is the single source of truth — no jumping between Discord, Webull, news sites, and docs.

## 2. Location & stack

```
Project root:  /Users/silent/trading-agent 2/
Repo:          https://github.com/Silentgsxr-cell/trading-agent  (branch: master)
Dashboard:     cd mission-control && npm run dev  →  http://localhost:3000  (redirects to /chief)
```

Single Next.js 14 server (App Router, TypeScript, Tailwind). Flask (port 5000) was fully removed in June 2026 — all API routes now live under `mission-control/app/api/`. There is no second backend to start.

Python 3 handles the trading loop and all autonomous agents (`runner.py`, `agents/`, `utils/`) — yfinance, pandas, pytz, filelock, python-dotenv.

Background processes (start manually each session, or via LaunchAgents — see §6):
```
python3 utils/watchdog.py &       # WATCH — security monitor
python3 utils/daitaos_bot.py      # INTEL — Discord bot (!brief, !status, etc.)
python3 utils/dev_agent.py        # autonomous dev agent (needs Anthropic credits)
python3 agents/chief.py           # CHIEF — scheduled 6:00 AM / 4:30 PM AZ
python3 utils/suggestion_agent.py # SAGE — scheduled 5:00 AM / 5:30 PM AZ
```

## 3. Agent roster — verified real status (not the dashboard's old stale labels)

Status is computed by scanning each agent's actual source file for a genuine `raise NotImplementedError` statement (see §4 for a regex bug that used to make this lie).

| Agent | File | Status | What it actually does |
|---|---|---|---|
| **HAWK** | `agents/signaos.py` | Live | Multi-strategy signal engine. ORB (opening range breakout) is live; 5 other strategies are registered stubs. Scores signals S/A/B/C, only forwards S/A tier. Never sizes or trades. |
| **VAULT** | `agents/risk_engine.py` | Live | The only agent with veto power. 1% risk/trade, 3% daily loss circuit breaker, max 3 trades/day, consecutive-loss cooldown. No agent can override it. |
| **INTEL** | `utils/daitaos.py` | Live | 9-section Discord morning brief (market status, TSLA bias, watchlist scan, SPY bias, rules, session status, journal edge, edge reminder, dev-agent overnight). Also runs the Discord bot (`daitaos_bot.py`). |
| **WATCH** | `utils/watchdog.py` | Live | Continuous security monitor, 7 checks every 60s (key exposure, session integrity, file integrity, config tamper, heartbeat, .env git-tracking, git author audit). |
| **SAGE** | `utils/suggestion_agent.py` | Live | Runs 5:00 AM / 5:30 PM AZ. Reads 9 data sources, one Claude call, posts up to 3 actionable suggestions to the Suggestion Board. |
| **CHIEF** | `agents/chief.py` | Live (was mislabeled "not yet built" until today — see §4) | Runs 6:00 AM / 4:30 PM AZ. Reads state from every agent, one Claude call, writes `logs/chief_assessment.json` for the `/chief` home page. Coordinates, never trades, never overrides VAULT. |
| **PULSE** | `agents/dataos.py` | **Genuine stub** | Market data backbone (bars, VWAP, session levels, options chain). Blocked on a production Webull API key. Everything HAWK does should flow through PULSE first — currently doesn't. |
| **TRIGGER** | `agents/execution_agent.py` | **Genuine stub** | Only agent allowed to place/modify/cancel orders. Paper-mode only once built. Blocked on PULSE. |
| **LEDGER** | `agents/review_agent.py` | **Genuine stub** | Daily trade review — expectancy by strategy, discipline score. Can tighten filters, cannot touch risk limits. Blocked on TRIGGER producing real fill data. |
| **Strategist** | `agents/strategist.py` | Missing (file doesn't exist) | Will pick strikes/expirations from VAULT-approved signals. Not started. |
| **Dev Agent** | `utils/dev_agent.py` | Built, blocked on billing | Autonomous ticket executor — reads `data/tickets.json`, makes a Claude API call, edits code, runs a git pipeline with 6 safety gates. Hard-blocked from ever touching `agents/`, `config/`, `tests/`, or core `utils/` files. TICKET-001 is queued and already failed once with "Claude API call failed — check ANTHROPIC_API_KEY" (no credits, not a bug). You can submit new tickets right now from the dashboard's Dev tab (`POST /api/tickets` already works).

## 4. What this session found and fixed (all committed to the live files, not just discussed)

1. **Dashboard stub-status bug (real bug, found and fixed).** `mission-control/lib/agents.ts` flags an agent as "stub" if its source file contains the text `raise NotImplementedError` anywhere. CHIEF and SAGE both contain that exact string *as a quoted literal* (they each scan other agents' files for the same pattern), so the old unanchored regex matched inside their own string literals and mislabeled both as unbuilt. Fixed by anchoring the regex to line start (`^\s*raise\s+NotImplementedError`, multiline). Verified with a standalone Node script against all 9 agent files — output now matches reality exactly (HAWK/VAULT/INTEL/WATCH/SAGE/CHIEF live, PULSE/TRIGGER/LEDGER stub).
2. **CHIEF's dashboard copy was stale**, still saying "not yet built / architecture not yet specced" despite `chief.py` (319 lines) being fully implemented and scheduled. Rewrote the role/summary/description in `lib/agents.ts`.
3. **Built the missing "agent feels alive" plumbing.** There was no shared file where a Python agent could report "what am I doing right now" — everything the dashboard showed was either static copy or derived from a stub/live scan, never live activity. Added to `utils/agent_brain.py`:
   - `AgentBrain.start_task(task, queue_len, confidence, waiting_on)`
   - `AgentBrain.update_task(...)` — mid-run progress updates
   - `AgentBrain.finish_task(last_action, next_scheduled_action)`
   - `AgentBrain.error(message)`
   All four write to `state/agent_status.json` (filelock-protected, same single-writer pattern as the other state files). A built-in schedule table (`CHIEF`: 06:00/16:30 AZ, `SAGE`: 05:00/17:30 AZ, `INTEL`: 06:20 AZ) computes `next_scheduled_action` automatically so idle agents show "next run 6:00 AM AZ" instead of nothing.
4. **Wired the above into the 4 agents that actually run on a cycle**: `agents/chief.py`, `utils/daitaos.py` (INTEL — needed a new `AgentBrain` import, didn't have one before), `utils/suggestion_agent.py` (SAGE), `utils/watchdog.py` (WATCH, wraps each 60s check cycle). **Deliberately did not wire PULSE/TRIGGER/LEDGER** — they're genuine stubs with no real task to report; faking a "thinking" state for code that immediately raises `NotImplementedError` would just be different mock data.
5. **Verified end-to-end, not just written**: ran `python3 agents/chief.py --dry-run` and `python3 utils/suggestion_agent.py --dry-run` for real in the project directory. `state/agent_status.json` now contains real entries for CHIEF and SAGE with correct timestamps, `next_scheduled_action`, etc. (Both entries currently say "dry run" as their last action — that's expected, they'll be overwritten with real content the next time these run for real, e.g. once Anthropic credits are added.)
6. **Dashboard wired to the new data**: `lib/agents.ts` now reads `state/agent_status.json` and merges it into each `AgentCard` (new `live` field — state/currentTask/progressPct/queueLen/confidence/waitingOn/lastAction/nextScheduledAction/lastHeartbeat). Handles legacy AgentBrain ids (WATCH's brain posts as "WATCHDOG", etc. — matches `AGENT_AVATARS` aliasing already in `agent_brain.py`).
7. **`AgentCard.tsx`** front face now shows the live state: thinking agents get their current task + a progress bar + queue/confidence/waiting-on chips; idle agents show last action + next scheduled run; errored agents show the failure reason in maroon.
8. **New `/api/agents` route** (`mission-control/app/api/agents/route.ts`) — didn't exist before, exposes `getAgents()` + `crewHealth()` to client components.
9. **Sidebar** (`components/Sidebar.tsx`): added a global status strip under the logo — a segmented bar (thinking/idle/errors/stub/missing) plus counts, polling `/api/agents` every 15s. Also reorganized nav into department groups (Trading: Markets/Signals/Risk/Journal · Intelligence: News & Research/Vault Docs · Personal: Life/Finance · System: Suggestions/Dev/System) — every link points at a page that actually exists; nothing was added ahead of its page being built.
10. Verified with `npx tsc --noEmit` inside `mission-control/` — clean, zero type errors. Could not complete a full `npm run build` inside the sandbox's 45-second per-command limit; typecheck passing is a strong signal but run `npm run dev` locally to confirm it renders correctly.

## 5. Current git state — nothing committed yet

`git status` on the project root shows:

**Modified (this session's work):**
`agents/chief.py`, `mission-control/components/AgentCard.tsx`, `mission-control/components/Sidebar.tsx`, `mission-control/lib/agents.ts`, `mission-control/lib/config.ts`, `utils/agent_brain.py`, `utils/daitaos.py`, `utils/suggestion_agent.py`, `utils/watchdog.py`

**Also modified, NOT from this session** — a separate/earlier local Claude Code session appears to have been mid-way through a Journal Notes feature: `mission-control/app/logs/page.tsx`, `mission-control/lib/dataPath.ts`, plus untracked `mission-control/app/logs/NotesPanel.tsx`, `mission-control/app/api/journal/`, `data/journal_notes.json`. Worth checking `git diff` on those specifically before committing anything — they weren't reviewed or touched by this session.

**Untracked:** `state/` (this is correct — `state/` is gitignored, it's runtime data including the new `agent_status.json`), `.claude/`, `logs/`.

Nothing has been committed. Recommend reviewing and committing in two separate commits (agent-status plumbing vs. journal notes feature) rather than one big commit mixing unrelated work.

## 6. Still open — manual steps only Silent can do (nothing here is a code bug)

1. **Add Anthropic API credits** — console.anthropic.com → Plans & Billing. Blocks: Dev Agent (TICKET-001 already queued and failed on this), CHIEF's and SAGE's daily Claude calls.
2. **Add 6 Discord webhook URLs to `.env`** — currently only the legacy `DISCORD_WEBHOOK_URL` / `DISCORD_BOT_TOKEN` / `ANTHROPIC_API_KEY` are set. Missing: `DISCORD_MORNING_BRIEF_WEBHOOK`, `DISCORD_TRADE_ALERTS_WEBHOOK`, `DISCORD_WATCHDOG_WEBHOOK`, `DISCORD_DEV_AGENT_WEBHOOK`, `DISCORD_SUGGESTIONS_WEBHOOK`, `DISCORD_AGENT_ACTIVITY_WEBHOOK`. This is the root cause of "no daily briefs" — `daitaos.py` checks for `DISCORD_MORNING_BRIEF_WEBHOOK` specifically and aborts silently without it.
3. **Install/load LaunchAgents on the Mac:**
   ```
   cp "/Users/silent/trading-agent 2/deploy/com.silent.chief.plist" ~/Library/LaunchAgents/
   cp "/Users/silent/trading-agent 2/deploy/com.silent.suggestion.plist" ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.silent.chief.plist
   launchctl load ~/Library/LaunchAgents/com.silent.suggestion.plist
   launchctl list | grep silent   # confirm watchdog/devagent are still loaded too
   ```
4. **Grant Calendar permission** — System Settings → Privacy & Security → Calendars → allow Terminal/Node (for the Life tab calendar integration).
5. **Manually run CHIEF + INTEL once for real** once 1 and 2 are done, to confirm `chief_assessment.json` refreshes and a brief actually posts to Discord, before trusting the scheduled runs:
   ```
   cd "/Users/silent/trading-agent 2"
   python3 agents/chief.py
   python3 utils/daitaos.py
   ```

## 7. Data / state file ownership (single-writer rule — do not bypass)

| File | Owner | Notes |
|---|---|---|
| `state/session.json` | `utils/state_manager.py` | filelock |
| `state/decisions.jsonl` | `utils/event_log.py` | filelock. **Currently empty** — `log_event()` exists but nothing calls it yet. This is why there's no Activity Feed data source today (see §9). |
| `data/journal.csv` | `utils/journal_writer.py` | filelock |
| `data/suggestions.json` | `utils/agent_brain.py` (`AgentBrain.suggest()`) | filelock, 3-per-agent-per-day cap unless priority ≥ 9 |
| `state/agent_status.json` | `utils/agent_brain.py` (`start_task`/`update_task`/`finish_task`/`error`) | **New this session.** filelock. Merge-on-write per agent key — safe for concurrent agents. |
| `data/tickets.json` | Dev Agent + `POST /api/tickets` | |
| `logs/chief_assessment.json` | `agents/chief.py` | Read by `/chief` page via `lib/chief.ts` |
| `logs/morning_brief_log.json` | `utils/daitaos.py` | Structured version of the last brief, for the dashboard |

## 8. Hard rules — do not break these (from the project's own docs)

- Never modify `agents/` or `config/` unless explicitly asked — risk parameters and agent logic are production.
- Never commit `.env` — watchdog auto-flags if it becomes git-tracked.
- Never commit `state/session.json` or `state/decisions.jsonl` — runtime state, gitignored.
- All writes to shared files go through the owning `utils/` module (see §7) — never write those files directly from a new script.
- The Dev Agent is hard-blocked from writing to `agents/`, `config/`, `tests/`, or core `utils/` files (`state_manager.py`, `event_log.py`, `journal_writer.py`, `watchdog.py`) — this is enforced in its own safety-gate code, not just a convention.
- No agent, including CHIEF, has authority to change `config/risk_config.py` values — manual, deliberate edit only.
- Circuit breaker (3% daily loss) cannot be skipped at any autonomy stage.

## 9. Backlog — not started yet, from Silent's UI vision list

1. **CHIEF page rewrite** — Jarvis-style narrative morning readout (already has real data available via `chief_assessment.json`) + an "Ask Chief" chat box. The chat box needs a new API route hitting the Anthropic API per message — real per-query cost, flag this before building.
2. **Agent Activity Feed** — a live scrolling feed (HAWK found signal / VAULT rejected trade / etc.). Blocked on nothing except instrumentation: `utils/event_log.py`'s `log_event()` already exists and `state/decisions.jsonl` already exists, but no agent calls it yet. Needs both the write-side hooks and a read-side feed component.
3. **Signals / Risk / System pages** — currently literal 11-line "coming in a future phase" placeholders. Signals: pipeline counts from `state/signals.jsonl`. Risk: today's budget/drawdown/trades-left from `config/risk_config.py` + `state/session.json`. System: per-agent health from the new `agent_status.json` + logs.
4. **Intelligence page rebuild** — `/memory` is mostly empty; should show today's narrative, market themes, news score, company relationships — reusing what `daitaos.py` already computes (`s2_tsla_bias`, `s3_watchlist`, `s8_edge`) rather than new scraping work.
5. **Agent relationship / pipeline diagram** — visualize the INTEL → CHIEF → HAWK → PULSE → VAULT → STRATEGIST → TRIGGER → LEDGER → CHIEF handoff chain.

## 10. Known doc drift to be aware of

`HANDOFF.md` (project root) was last edited today but still has a stale rename table showing CHIEF as "not yet built" — contradicts `docs/MASTER.md` (also edited today), which correctly says CHIEF is live. `docs/MASTER.md` explicitly declares itself canonical. Worth reconciling — not done as part of this session, flagged as a follow-up.

---

*Generated by a Cowork session with direct file access to `/Users/silent/trading-agent 2/`. Every claim above was verified against actual file contents, not inferred from memory or prior conversation.*
