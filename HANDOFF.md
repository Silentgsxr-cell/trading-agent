# Trading Sim — Claude Handoff
Drop this file into `trading-agent/` alongside the sim. When starting a new Claude session, paste the relevant section as your first message.

---

## Master context prompt
Paste this at the start of any new Claude session to restore full context.

```
I have a TSLA paper trading simulator saved at trading-agent/sim/tsla_trading_sim.html.
It is a single standalone HTML file — no framework, no backend, runs offline in any browser.

The sim has 6 core engines:
1. Price engine — GBM (geometric Brownian motion) with session-based volatility
2. Candle engine — two-phase build (body ticks → wick ticks → close), up to 5,000 bars stored in candleHistory[]
3. Viewport model — candleHistory[] is the data, the chart is a window over it. Drag to pan, scroll to zoom, liveMode snaps back to right edge
4. Drawings layer — rendered after candles, before crosshair. Types: hline (blue) and support zone (purple with ±0.3% band). Stored in drawings[]
5. Options chain — Black-Scholes pricing, 5 expirations (0DTE/7d/14d/30d/60d), ITM/OTM badges, current price pinned in middle
6. ORB engine — 9:30–9:45 sim time marks opening range, locks at 9:45, valid entry = breakout above H or below L

Order types: market, limit, stop, EOD
Account sidebar shows: Account P&L, Day P&L, Unrealized P&L, Realized P&L, Cash, Buying power
Full account details + psychology engine are hidden behind a "Details" toggle
ORB scorecard compares valid vs invalid entries and generates plain-English trade insights
Trade journal logs every closed trade with: time, side, instrument, qty, entry, exit, P&L, strategy, valid?

The file is ~1,100 lines. When I paste it, please read it fully before making any changes.
All changes should be applied to the file and re-exported so I can re-download.
```

---

## How to paste the file into Claude

1. Open `tsla_trading_sim.html` in a text editor (VS Code, Notepad, TextEdit)
2. Select all → Copy
3. In Claude, type: `Here is my current sim file:` then paste the code
4. Then describe what you want changed

Claude will read the full file, make the change, and give you an updated file to download.

---

## Feature request prompts
Copy-paste any of these exactly as written.

### Chart upgrades

```
In my trading sim, add a volume histogram at the bottom of the chart.
Each bar height = that candle's volume relative to the max visible volume.
Green bars for bullish candles, red for bearish. Use the bottom 20% of chart height.
Keep all existing chart features intact.
```

```
In my trading sim, add a 9 and 21 period EMA overlay on the candlestick chart.
9 EMA in cyan, 21 EMA in orange. Both as solid lines, 1px width.
Add them to the legend in the top right corner of the chart.
```

```
In my trading sim, add a RSI panel below the main chart.
14-period RSI. Panel height 60px. Overbought line at 70 (red dashed), oversold at 30 (green dashed).
RSI line in purple. Keep all existing chart features.
```

```
In my trading sim, add a MACD panel below the main chart.
MACD line in blue, signal line in orange, histogram bars green/red.
Panel height 60px. Keep all existing chart features.
```

```
In my trading sim, add Bollinger Bands overlay on the candlestick chart.
20-period SMA, 2 standard deviations. Upper band red dashed, lower band green dashed, middle band gray.
Shade the band area with 5% opacity. Add to legend.
```

### Order system upgrades

```
In my trading sim, add a bracket order system.
When placing a market order, I can optionally set both a stop-loss AND a profit target at the same time.
Show both pending orders in a "Pending orders" table below the positions table.
Each pending order shows: side, type, price, qty, and a cancel button.
```

```
In my trading sim, add a trailing stop order type.
When I select "Trailing Stop" from the order type dropdown and enter a dollar amount,
the stop follows price up (for longs) automatically and only triggers on a reversal.
Show the current trailing stop level in the positions table.
```

```
In my trading sim, add an order history table below the positions table.
Shows all filled orders (not just closed trades): time, side, instrument, qty, fill price, order type.
Separate from the trade journal which shows completed round trips.
```

### Options upgrades

```
In my trading sim, add a Greeks panel.
When I have an open option position, show a live-updating panel with:
Delta, Gamma, Theta (per day), Vega, and current IV.
Values update every tick. Position below the positions table.
```

```
In my trading sim, add an options P&L scenario table.
Show what my current option position is worth if price moves -20%, -10%, -5%, flat, +5%, +10%, +20%
from current price. Update live. Show as a horizontal row of colored cells.
```

```
In my trading sim, make the 0DTE options expire and go to zero at sim time 3:59 PM (minute 959).
Any 0DTE options still held at that time should settle: ITM options cash-settle at intrinsic value, OTM options expire worthless.
Log the expiration in the trade journal.
```

### Account / analytics upgrades

```
In my trading sim, add a P&L equity curve chart.
Below the trade journal, show a line chart of cumulative realized P&L over time.
X axis = trade number, Y axis = cumulative $. Green line above zero, red below.
Updates after each closed trade.
```

```
In my trading sim, add a session summary popup.
When I click Reset, before clearing everything, show a summary of the session:
Total trades, Win rate, Gross profit, Gross loss, Net P&L, Best trade, Worst trade, Discipline score.
Include a "Close and Reset" button and a "Keep Trading" button.
```

```
In my trading sim, add a max drawdown tracker to the ORB scorecard.
Max drawdown = largest peak-to-trough drop in cumulative P&L during the session.
Show it in the scorecard panel. Color red if drawdown exceeds 10% of starting cash.
```

### Sim / replay upgrades

```
In my trading sim, add a CSV import feature.
Add a button "Load historical data" that lets me upload a CSV with columns: time, open, high, low, close, volume.
When loaded, replace the GBM engine with a replay engine that steps through the CSV row by row at the selected speed.
Show a "Replay mode" badge in the header when active.
```

```
In my trading sim, add a pre-market session from 4:00 AM to 9:30 AM sim time.
Pre-market uses lower volatility (0.0003) and thinner volume.
Show pre-market candles in a slightly dimmed color (70% opacity) to visually separate from regular session.
Add a vertical line at 9:30 to mark market open.
```

```
In my trading sim, add session markers on the chart.
A vertical dashed line at 9:30 AM labeled "Open", another at 9:45 AM labeled "ORB Lock", another at 4:00 PM labeled "Close".
Lines should be semi-transparent and not interfere with candle reading.
```

```
In my trading sim, add a news event simulator.
Every 30–60 real-time seconds (random), generate a simulated news event that temporarily spikes volatility for 10–20 ticks.
Show a small flag marker on the chart at that candle.
Hovering the flag shows the fake headline (e.g. "TSLA: analyst upgrades to Buy" or "Fed minutes released").
```

### Drawing tool upgrades

```
In my trading sim, add a trend line drawing tool.
Click two points on the chart to draw a line between them extending to the right edge.
Color: white. Show the angle and slope in a tooltip.
Add it to the draw tool buttons alongside H-line and S/R.
```

```
In my trading sim, add a Fibonacci retracement drawing tool.
Click two points (swing high and swing low). Draw the 23.6%, 38.2%, 50%, 61.8%, and 78.6% levels.
Each level labeled with the percentage and price. Color each level differently.
```

```
In my trading sim, make drawings persist across resets using localStorage.
Save drawings[] to localStorage on every change.
On load, restore drawings from localStorage if present.
Add a "Clear saved drawings" option to the reset dialog.
```

### UI upgrades

```
In my trading sim, add a dark/light mode toggle.
Light mode: white background, dark text, same green/red color scheme.
Toggle button in the top bar. Persist preference in localStorage.
```

```
In my trading sim, add keyboard shortcuts:
B = market buy 1 share
S = market sell 1 share  
P = pause/resume
R = reset (with confirmation)
+ / - = zoom in / zoom out
Arrow left/right = pan chart
Show a shortcuts reference in a small overlay triggered by pressing ?
```

```
In my trading sim, make the left P&L sidebar numbers animate when they change.
Flash green briefly on increase, red briefly on decrease.
Use a CSS transition — no libraries.
```

### Bug fix prompts

```
In my trading sim, [describe the bug exactly — what you clicked, what happened, what you expected].
Here is the current file: [paste file]
```

---

## How to update the file after Claude makes a change

1. Claude will give you an updated file to download
2. Download it
3. Replace the old `tsla_trading_sim.html` in `trading-agent/sim/`
4. Refresh the browser tab (or close and reopen the file)

You do NOT need to restart anything. The file is self-contained.

---

## Architecture reference
Quick cheat sheet if you need to explain the sim to Claude mid-session.

```
candleHistory[]     — full candle data array (max 5,000 bars)
vwapPerCandle[]     — parallel VWAP value per completed candle
curCandle           — the candle currently forming
viewportStart       — index of leftmost visible candle
viewportLen         — how many candles to show (0 = all)
liveMode            — true = viewport tracks right edge
drawings[]          — [{type, price, color, label}] — separate from candle data
orbHigh / orbLow    — set during 9:30–9:45 sim time, locked at 9:45
price               — current tick price
simMin              — sim clock in minutes from midnight (570 = 9:30 AM)
cash / pos / optPos — account state
tradeLog[]          — all trades for journal and scorecard
```

---

## File locations

```
trading-agent/
  ├── sim/
  │     └── tsla_trading_sim.html
  ├── journal/
  ├── notes/
  ├── README.md              ← full technical documentation
  └── HANDOFF.md             ← this file
```

---

No Claude needed to run the sim. Claude only needed when adding features or fixing bugs.
