# Silent — Trading Terminal

A Webull-style day trading dashboard built with Flask. Designed for a small account trader focused on the 15-minute Opening Range Breakout (ORB) strategy on TSLA, QQQ, MSFT, and AMZN.

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

- **Backend:** Python 3, Flask, yfinance, pandas, pytz
- **Frontend:** Vanilla HTML/CSS/JS — no frameworks
- **Chart:** TradingView embeddable widget (free, no API key)
- **Data:** yfinance for prices and news (15–20 min delay on free tier)

## Setup

```bash
git clone https://github.com/Silentgsxr-cell/trading-agent.git
cd trading-agent
pip3 install -r requirements.txt
PORT=5001 python3 run.py
```

Then open **http://localhost:5001** in your browser.

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
- Port 5000 conflicts with macOS AirPlay Receiver — use `PORT=5001`
- Prices are delayed 15–20 minutes on the yfinance free tier
- ORB range validity thresholds are tunable constants at the top of `agent/orb_calculator.py`
