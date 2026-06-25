"""
backtester.py — ORB backtest engine on historical 5-minute data.

Simulates the 15-minute Opening Range Breakout strategy:
  1. First 15 minutes (9:30–9:44 ET) define the range high/low.
  2. Enter on the first breakout above the high (long) or below the low (short).
  3. Stop = other side of the range; exit at target R or stop, whichever comes first.
  4. Any trade still open at 3:55 PM is closed at that candle's close.

yfinance provides up to 60 calendar days of 5-minute data for free.
"""

import math
import yfinance as yf

# Shared validity thresholds with orb_calculator.py
MIN_RANGE_PCT = 0.05
MAX_RANGE_PCT = 1.20


def _record(trades, t, exit_price, result, r_multiple, date, orb_high, orb_low, exit_time):
    if t['direction'] == 'Long':
        pnl = round((exit_price - t['entry']) * t['shares'], 2)
    else:
        pnl = round((t['entry'] - exit_price) * t['shares'], 2)
    trades.append({
        'date':       str(date),
        'direction':  t['direction'],
        'orb_high':   round(orb_high, 2),
        'orb_low':    round(orb_low, 2),
        'entry':      t['entry'],
        'stop':       t['stop'],
        'target':     t['target'],
        'exit':       round(float(exit_price), 2),
        'shares':     t['shares'],
        'entry_time': t['entry_time'],
        'exit_time':  exit_time,
        'result':     result,
        'r_multiple': r_multiple,
        'pnl':        pnl,
    })


def run_backtest(
    ticker: str = 'TSLA',
    trading_days: int = 30,
    account_size: float = 1000.0,
    risk_pct: float = 1.0,
    target_r: float = 2.0,
) -> dict:
    """
    Simulate the 15-min ORB strategy on up to `trading_days` days of 5-min bars.
    Returns per-trade detail and aggregate stats.
    """
    t = yf.Ticker(ticker)
    data = t.history(period='60d', interval='5m')

    if data is None or data.empty:
        return {'error': f'No 5-minute data available for {ticker}.'}

    # Ensure Eastern timezone
    if data.index.tz is None:
        data.index = data.index.tz_localize('UTC').tz_convert('US/Eastern')
    else:
        data.index = data.index.tz_convert('US/Eastern')

    # Limit to requested number of most-recent trading days
    dates = sorted(set(data.index.date))
    dates = dates[-min(trading_days, len(dates)):]

    trades = []
    days_scanned = 0
    days_skipped = 0
    dollar_risk  = account_size * (risk_pct / 100.0)

    for date in dates:
        day_data = data[data.index.date == date]
        # Regular session: 9:30 AM to 3:55 PM ET (last 5m bar closes at 4:00)
        session = day_data.between_time('09:30', '15:55')

        if len(session) < 4:   # need ORB (3 bars) + at least 1 scan bar
            days_skipped += 1
            continue

        days_scanned += 1

        # 15-min ORB = bars starting at 9:30, 9:35, 9:40
        orb_bars = session.iloc[:3]
        orb_high  = float(orb_bars['High'].max())
        orb_low   = float(orb_bars['Low'].min())
        avg_price = (orb_high + orb_low) / 2.0
        range_pct = ((orb_high - orb_low) / avg_price) * 100 if avg_price > 0 else 0

        if range_pct < MIN_RANGE_PCT or range_pct > MAX_RANGE_PCT or orb_high <= orb_low:
            days_skipped += 1
            days_scanned -= 1
            continue

        long_entry  = round(orb_high + 0.01, 2)
        short_entry = round(orb_low  - 0.01, 2)
        trade_open  = None
        traded      = False   # one trade per day maximum

        for ts, bar in session.iloc[3:].iterrows():
            b_high  = float(bar['High'])
            b_low   = float(bar['Low'])
            b_close = float(bar['Close'])
            tstr    = ts.strftime('%H:%M')

            if trade_open is None and not traded:
                broke_long  = b_high  >= long_entry
                broke_short = b_low   <= short_entry

                if broke_long and not broke_short:
                    rps  = round(long_entry - (orb_low - 0.01), 2)
                    if rps <= 0:
                        break
                    stop   = round(orb_low - 0.01, 2)
                    target = round(long_entry + target_r * rps, 2)
                    shares = math.floor(dollar_risk / rps)
                    trade_open = dict(direction='Long', entry=long_entry, stop=stop,
                                      target=target, shares=shares, rps=rps, entry_time=tstr)
                    traded = True
                    # Same-candle exit check
                    if b_low <= stop:
                        _record(trades, trade_open, stop, 'Loss', -1.0, date, orb_high, orb_low, tstr)
                        trade_open = None
                    elif b_high >= target:
                        _record(trades, trade_open, target, 'Win', target_r, date, orb_high, orb_low, tstr)
                        trade_open = None

                elif broke_short and not broke_long:
                    rps  = round((orb_high + 0.01) - short_entry, 2)
                    if rps <= 0:
                        break
                    stop   = round(orb_high + 0.01, 2)
                    target = round(short_entry - target_r * rps, 2)
                    shares = math.floor(dollar_risk / rps)
                    trade_open = dict(direction='Short', entry=short_entry, stop=stop,
                                      target=target, shares=shares, rps=rps, entry_time=tstr)
                    traded = True
                    if b_high >= stop:
                        _record(trades, trade_open, stop, 'Loss', -1.0, date, orb_high, orb_low, tstr)
                        trade_open = None
                    elif b_low <= target:
                        _record(trades, trade_open, target, 'Win', target_r, date, orb_high, orb_low, tstr)
                        trade_open = None

            elif trade_open is not None:
                if trade_open['direction'] == 'Long':
                    if b_low <= trade_open['stop']:
                        _record(trades, trade_open, trade_open['stop'], 'Loss', -1.0, date, orb_high, orb_low, tstr)
                        trade_open = None
                    elif b_high >= trade_open['target']:
                        _record(trades, trade_open, trade_open['target'], 'Win', target_r, date, orb_high, orb_low, tstr)
                        trade_open = None
                else:
                    if b_high >= trade_open['stop']:
                        _record(trades, trade_open, trade_open['stop'], 'Loss', -1.0, date, orb_high, orb_low, tstr)
                        trade_open = None
                    elif b_low <= trade_open['target']:
                        _record(trades, trade_open, trade_open['target'], 'Win', target_r, date, orb_high, orb_low, tstr)
                        trade_open = None

        # EOD exit — close at 3:55 candle's close
        if trade_open is not None:
            eod_close = float(session.iloc[-1]['Close'])
            rps = trade_open['rps']
            if trade_open['direction'] == 'Long':
                r = round((eod_close - trade_open['entry']) / rps, 2) if rps else 0
            else:
                r = round((trade_open['entry'] - eod_close) / rps, 2) if rps else 0
            result = ('Win' if r > 0 else 'Loss') + ' (EOD)'
            _record(trades, trade_open, eod_close, result, r, date, orb_high, orb_low, 'EOD')

    if not trades:
        return {
            'trades': [],
            'stats': {
                'total_trades': 0,
                'days_scanned': days_scanned,
                'days_skipped': days_skipped,
                'note': 'No valid ORB setups found in the selected period.',
            },
        }

    wins   = [t for t in trades if t['result'].startswith('Win')]
    losses = [t for t in trades if t['result'].startswith('Loss')]
    total_pnl = round(sum(t['pnl'] for t in trades), 2)
    win_rate  = round(len(wins) / len(trades) * 100, 1)
    avg_r     = round(sum(t['r_multiple'] for t in trades) / len(trades), 2)

    return {
        'trades': trades,
        'stats': {
            'ticker':       ticker.upper(),
            'total_trades': len(trades),
            'wins':         len(wins),
            'losses':       len(losses),
            'win_rate':     win_rate,
            'total_pnl':    total_pnl,
            'avg_r':        avg_r,
            'best_trade':   max(t['pnl'] for t in trades),
            'worst_trade':  min(t['pnl'] for t in trades),
            'days_scanned': days_scanned,
            'days_skipped': days_skipped,
            'target_r':     target_r,
        },
    }
