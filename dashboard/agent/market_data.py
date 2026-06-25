"""
Market data via yfinance — prices, bias, sparklines, news.

Uses zoneinfo (stdlib Python 3.9+) so no extra pytz dependency.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import yfinance as yf

_WATCHLIST = ["TSLA", "QQQ", "MSFT", "AMZN"]
_PHX = ZoneInfo("America/Phoenix")
_ET  = ZoneInfo("America/New_York")


def _market_times() -> dict:
    now_et = datetime.now(_ET)
    now_az = datetime.now(_PHX)
    open_et  = now_et.replace(hour=9,  minute=30, second=0, microsecond=0)
    close_et = now_et.replace(hour=16, minute=0,  second=0, microsecond=0)
    pre_et   = now_et.replace(hour=4,  minute=0,  second=0, microsecond=0)
    weekday  = now_et.weekday() < 5
    is_open  = weekday and open_et <= now_et < close_et
    is_pre   = weekday and pre_et  <= now_et < open_et
    status   = "OPEN" if is_open else ("PRE" if is_pre else "CLOSED")
    return {
        "today":         now_az.strftime("%A, %B %d, %Y"),
        "current_time":  now_az.strftime("%I:%M %p"),
        "market_open":   "9:30 AM ET",
        "market_close":  "4:00 PM ET",
        "market_status": status,
        "is_open":       is_open,
        "is_premarket":  is_pre,
    }


def _ticker_data(sym: str) -> dict:
    try:
        hist = yf.Ticker(sym).history(period="10d", interval="1d")
        if hist.empty:
            return {"error": "no data"}
        closes   = list(hist["Close"])
        price    = round(float(closes[-1]), 2)
        prev     = round(float(closes[-2]), 2) if len(closes) > 1 else price
        pct_chg  = round((price - prev) / prev * 100, 2) if prev else 0.0
        k = 2 / 10
        ema = closes[0]
        for c in closes[1:]:
            ema = c * k + ema * (1 - k)
        if   price > round(ema, 2): trend, tcls = "Above EMA9", "up"
        elif price < round(ema, 2): trend, tcls = "Below EMA9", "down"
        else:                        trend, tcls = "At EMA9",    "flat"
        return {"price": price, "pct_change": pct_chg, "trend": trend, "trend_class": tcls}
    except Exception as e:
        return {"error": str(e)}


def get_all_market_data() -> dict:
    tickers = {sym: _ticker_data(sym) for sym in _WATCHLIST}
    spy = _ticker_data("SPY")
    if "error" not in spy:
        p = spy["pct_change"]
        if   p >  0.2: bias, cls = "Bullish", "bullish"
        elif p < -0.2: bias, cls = "Bearish", "bearish"
        else:           bias, cls = "Neutral", "neutral"
        spy_out = {"bias": bias, "bias_class": cls, "spy_pct": p}
    else:
        spy_out = {"bias": "N/A", "bias_class": "neutral", "spy_pct": 0}
    return {"tickers": tickers, "spy": spy_out, "market_times": _market_times()}


def get_sparklines() -> dict:
    result = {}
    for sym in _WATCHLIST:
        try:
            hist = yf.Ticker(sym).history(period="5d", interval="1d")
            result[sym] = [round(float(c), 2) for c in hist["Close"].tail(5)]
        except Exception:
            result[sym] = []
    return result


def get_news() -> list:
    items = []
    for sym in _WATCHLIST:
        try:
            for n in (yf.Ticker(sym).news or [])[:3]:
                items.append({
                    "ticker":    sym,
                    "title":     n.get("title", ""),
                    "link":      n.get("link", ""),
                    "publisher": n.get("publisher", ""),
                    "timestamp": n.get("providerPublishTime"),
                })
        except Exception:
            pass
    items.sort(key=lambda x: x.get("timestamp") or 0, reverse=True)
    return items
