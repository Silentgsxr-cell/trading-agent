# Startup Commands

## Flask Dashboard — localhost:5000

```bash
cd ~/Desktop/silent\ graph/trading-agent\ 2
python3 dashboard/app.py
```

## ClawOps Mission Control — localhost:3000

```bash
cd ~/Desktop/silent\ graph/trading-agent\ 2/mission-control
npm run dev
```

---

## Notes

- **AirPlay Receiver must be OFF** — macOS routes port 5000 to AirPlay if enabled.
  Turn off: System Settings → General → AirDrop & Handoff → AirPlay Receiver → off
- Both servers must run simultaneously for full system operation.
- Flask serves the trading terminal (market data, ORB planner, risk calc, journal).
- Mission Control serves the agent fleet cockpit (Next.js, reads local files — no Flask dependency).
- Flask debug PIN (session-specific): shown in terminal on startup.
