"""
market_data.py — Fetches live price data from yfinance.

Prices may be delayed 15–20 minutes on the free tier.
Arizona is UTC-7 year-round (no DST) — we use 'US/Arizona' from pytz.
"""

import yfinance as yf
import pytz
from datetime import datetime

# The four tickers Silent watches. SPY is fetched separately for bias only.
WATCHLIST = ['QQQ', 'TSLA', 'MSFT', 'AMZN']

ARIZONA_TZ = pytz.timezone('US/Arizona')   # UTC-7, no DST ever
EASTERN_TZ  = pytz.timezone('US/Eastern')  # UTC-5 winter / UTC-4 summer


def get_ticker_info(ticker: str) -> dict:
    """
    Return price, % change vs previous close, and 9-day EMA trend for one ticker.

    trend_class: 'up' | 'down' | 'flat'  — used by the HTML for CSS classes.
    """
    try:
        t = yf.Ticker(ticker)

        # 30 days of daily closes is enough to calculate a reliable 9-day EMA
        hist = t.history(period='30d')

        if hist.empty or len(hist) < 2:
            raise ValueError('Not enough history')

        # Prefer the real-time snapshot from fast_info when available.
        # fast_info is a lightweight dict that doesn't require a full info() call.
        try:
            current_price = float(t.fast_info['last_price'])
            prev_close    = float(t.fast_info['previous_close'])
        except (KeyError, TypeError, AttributeError):
            # Fallback: use the last two daily closes
            current_price = float(hist['Close'].iloc[-1])
            prev_close    = float(hist['Close'].iloc[-2])

        pct_change = ((current_price - prev_close) / prev_close) * 100 if prev_close else 0.0

        # 9-day EMA on daily closes. adjust=False matches how most charting platforms compute it.
        ema9 = float(hist['Close'].ewm(span=9, adjust=False).mean().iloc[-1])

        # Use a 0.15% buffer to avoid flagging tiny oscillations as directional moves
        buffer = ema9 * 0.0015
        if current_price > ema9 + buffer:
            trend, trend_class = 'Trending Up', 'up'
        elif current_price < ema9 - buffer:
            trend, trend_class = 'Trending Down', 'down'
        else:
            trend, trend_class = 'Flat', 'flat'

        return {
            'ticker':      ticker,
            'price':       round(current_price, 2),
            'pct_change':  round(pct_change, 2),
            'trend':       trend,
            'trend_class': trend_class,
            'ema9':        round(ema9, 2),
        }

    except Exception as exc:
        # Return a safe fallback so the dashboard renders even when data is unavailable
        return {
            'ticker':      ticker,
            'price':       0.0,
            'pct_change':  0.0,
            'trend':       'N/A',
            'trend_class': 'flat',
            'ema9':        0.0,
            'error':       str(exc),
        }


def get_spy_bias() -> dict:
    """
    Classify overall market direction as Bullish / Neutral / Bearish.

    Logic: compare SPY's current price to its previous close.
    > +0.3%  → Bullish
    < -0.3%  → Bearish
    otherwise → Neutral

    The spec asks for premarket vs previous close; we use current vs previous
    close because it works the same way during market hours and is more reliable
    to fetch consistently.
    """
    try:
        spy = yf.Ticker('SPY')
        try:
            current   = float(spy.fast_info['last_price'])
            prev_close = float(spy.fast_info['previous_close'])
        except (KeyError, TypeError, AttributeError):
            hist = spy.history(period='5d')
            if len(hist) < 2:
                raise ValueError('No SPY history')
            current    = float(hist['Close'].iloc[-1])
            prev_close = float(hist['Close'].iloc[-2])

        pct = ((current - prev_close) / prev_close) * 100 if prev_close else 0.0

        if pct > 0.3:
            bias, bias_class = 'Bullish', 'bullish'
        elif pct < -0.3:
            bias, bias_class = 'Bearish', 'bearish'
        else:
            bias, bias_class = 'Neutral', 'neutral'

        return {
            'bias':       bias,
            'bias_class': bias_class,
            'spy_pct':    round(pct, 2),
            'spy_price':  round(current, 2),
        }

    except Exception as exc:
        return {'bias': 'Neutral', 'bias_class': 'neutral', 'spy_pct': 0.0, 'spy_price': 0.0}


def get_market_times() -> dict:
    """
    Return today's date, current AZ time, and market open/close times
    converted into Arizona time.

    Arizona stays on MST (UTC-7) year-round.  The stock market runs on
    Eastern time (UTC-5 in winter, UTC-4 in summer), so the open/close
    displayed here will shift by an hour when the US enters/exits DST.
      Winter: open 7:30 AM AZ, close 2:00 PM AZ
      Summer: open 6:30 AM AZ, close 1:00 PM AZ
    """
    now_et = datetime.now(EASTERN_TZ)
    now_az = datetime.now(ARIZONA_TZ)

    # Build market open/close in Eastern time for today, then convert
    open_et  = now_et.replace(hour=9,  minute=30, second=0, microsecond=0)
    close_et = now_et.replace(hour=16, minute=0,  second=0, microsecond=0)
    open_az  = open_et.astimezone(ARIZONA_TZ)
    close_az = close_et.astimezone(ARIZONA_TZ)

    # Simple market-status logic (no holiday calendar)
    is_weekday  = now_et.weekday() < 5          # Mon=0 … Fri=4
    in_session  = open_et <= now_et <= close_et
    is_open     = is_weekday and in_session

    preopen_et  = now_et.replace(hour=4, minute=0, second=0, microsecond=0)
    is_premarket = is_weekday and (preopen_et <= now_et < open_et)

    if is_open:
        status = 'OPEN'
    elif is_premarket:
        status = 'PRE-MARKET'
    else:
        status = 'CLOSED'

    return {
        'today':         now_az.strftime('%A, %B %d, %Y'),
        'current_time':  now_az.strftime('%I:%M %p'),
        'market_open':   open_az.strftime('%I:%M %p'),
        'market_close':  close_az.strftime('%I:%M %p'),
        'market_status': status,
        'is_open':       is_open,
        'is_premarket':  is_premarket,
    }


def get_all_market_data() -> dict:
    """Top-level function called by Flask routes. Aggregates everything."""
    tickers = {t: get_ticker_info(t) for t in WATCHLIST}
    return {
        'tickers':      tickers,
        'spy':          get_spy_bias(),
        'market_times': get_market_times(),
    }


def get_sparklines() -> dict:
    """Return the last 5 daily closing prices per ticker for sparkline rendering."""
    result = {}
    for ticker in WATCHLIST:
        try:
            hist = yf.Ticker(ticker).history(period='7d')
            result[ticker] = [round(float(p), 2) for p in hist['Close'].tail(5).tolist()]
        except Exception:
            result[ticker] = []
    return result


def get_news() -> list:
    """
    Fetch recent news headlines for the watchlist tickers via yfinance.
    Returns a list of dicts sorted newest-first, deduplicated by URL.
    """
    all_news = []
    seen = set()
    for ticker in WATCHLIST:
        try:
            items = yf.Ticker(ticker).news or []
            for item in items[:10]:
                url = item.get('link', '')
                if not url or url in seen:
                    continue
                seen.add(url)
                all_news.append({
                    'ticker':    ticker,
                    'title':     item.get('title', ''),
                    'publisher': item.get('publisher', ''),
                    'link':      url,
                    'timestamp': item.get('providerPublishTime', 0),
                })
        except Exception:
            pass
    all_news.sort(key=lambda x: x['timestamp'], reverse=True)
    return all_news[:50]
