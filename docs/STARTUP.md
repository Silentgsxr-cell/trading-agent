# Startup Commands

> **Architecture note (updated 2026-07-16):** ClawOps is now a **single server** — one
> Next.js app on **localhost:3000**. The old Flask trading terminal on port 5000 was
> removed (migrated into Next.js API routes). See `docs/MASTER.md` for the canonical
> reference.

## ClawOps Mission Control — the only server — localhost:3000

```bash
cd ~/trading-agent\ 2/mission-control
npm run dev
```

Then open **http://localhost:3000** (it redirects to `/chief`, the cockpit).

---

## Background agents (optional — start manually or via LaunchAgents)

```bash
cd ~/trading-agent\ 2
python3 utils/watchdog.py &        # WATCH — security monitor
python3 utils/daitaos_bot.py       # INTEL — Discord bot
python3 runner.py                  # Trading loop (weekdays 9:30–16:00 ET)
```

---

## Notes

- **One server only.** All API routes live inside Next.js at `mission-control/app/api/`.
  There is no separate backend to start.
- The AirPlay Receiver / port 5000 conflict no longer applies — Flask is gone.
- Mission Control reads local files directly (state, journal, finance, tickets) — no
  external server dependency.
- Project lives at `~/trading-agent 2/`. The `~/Desktop/silent graph/trading-agent (shortcut)`
  entry in the Obsidian vault is a symlink to it — the same folder, not a second copy.
