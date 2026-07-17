# Silent — ClawOps Trading Terminal

A Webull-style day trading dashboard for a small account trader focused on the 15-minute Opening Range Breakout (ORB) strategy on TSLA, QQQ, MSFT, and AMZN. It runs as a single Next.js "Mission Control" app on `localhost:3000` over a Python multi-agent trading system.

> **Note:** This started as a Flask app on port 5000. Flask was removed in June 2026 — everything now runs as one Next.js server on port 3000. `docs/MASTER.md` is the canonical, up-to-date reference; this README is the historical origin doc.

## Features

- **Dashboard** — Live TSLA chart (TradingView), SPY market bias, account placeholders
- **Watchlist** — Real-time prices, % change, 9 EMA trend, SVG sparklines
- **ORB Planner** — Enter the 15-min high/low and get entry, stop, 1.5R/2R targets, and position size for both long and short setups
- **Risk Calculator** — Position sizing from dollar risk, max daily loss, targets
- **Trade Validator** — GO / NO-GO decision based on R/R ratio (minimum 1.5R required, stop loss enforced)
- **News** — Latest headlines for TSLA, QQQ, MSFT, AMZN via yfinance, filterable by ticker
- **Trade Journal** — Log every trade to a local CSV with discipline grading (A–F), win rate, and P/L tracking
- **Positions / Orders** — Placeholder pages ready for future Webull integration
- **Settings** — Default account size, risk %, and ticker stored in localStorage
- **Paper/Live toggle** — Sidebar toggle persists across sessions, clearly visible at all times

## Stack

- **App / UI:** Next.js 14 (App Router, TypeScript, Tailwind) — one server on `localhost:3000`, all API routes inside `mission-control/app/api/`
- **Agents / trading loop:** Python 3 — `runner.py`, `agents/`, `utils/`, yfinance, pandas, pytz
- **Chart:** TradingView embeddable widget (free, no API key)
- **Data:** yfinance for prices and news (15–20 min delay on free tier)

## Setup

```bash
cd ~/trading-agent\ 2/mission-control
npm install
npm run dev
```

Then open **http://localhost:3000** in your browser (redirects to `/chief`).

## Project Structure

```
trading-agent/
├── agent/
│   ├── market_data.py       # yfinance price fetching, SPY bias, news, sparklines
│   ├── orb_calculator.py    # ORB entry/stop/target/position sizing
│   ├── risk_calculator.py   # Dollar risk, position sizing, GO/NO-GO logic
│   └── journal_manager.py   # CSV read/write, stats (win rate, avg grade)
├── dashboard/
│   ├── app.py               # Flask routes
│   └── templates/
│       └── index.html       # Full single-page terminal UI
├── data/
│   └── journal.csv          # Trade journal (created on first save, gitignored)
├── run.py                   # Entry point
├── requirements.txt
└── .env                     # API keys placeholder (gitignored)
```

## Trader Profile

- **Style:** 15-min ORB on TSLA (primary), QQQ, MSFT, AMZN
- **Account:** Small ($1,000–$5,000), paper trading first
- **Risk:** 1% per trade max
- **Platform:** Webull (manual execution — no API)
- **Timezone:** Arizona MST (UTC-7, no DST)

## Notes

- `.env` and `data/journal.csv` are excluded from git — they stay local on each machine
- Runs on port 3000. The old port 5000 / macOS AirPlay conflict no longer applies (Flask removed)
- Prices are delayed 15–20 minutes on the yfinance free tier
- ORB range validity thresholds are tunable constants at the top of `agent/orb_calculator.py`
