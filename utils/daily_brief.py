#!/usr/bin/env python3
"""
utils/daily_brief.py — Silent's 6:20 AM morning brief.
Sends a Discord embed: market status, TSLA bias, watchlist scan,
SPY tone, trading rules, session status, journal edge, edge reminder.
"""

import sys
import os
import json
import csv
import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import requests
import yfinance as yf
import pytz
from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from config import risk_config as cfg
from config import strategy_config as scfg

WEBHOOK_URL  = os.getenv("DISCORD_WEBHOOK_URL", "")
EASTERN      = pytz.timezone("America/New_York")
ARIZONA      = pytz.timezone("America/Phoenix")
EMBED_COLOR  = 0x1A2744

WATCHLIST = ["TSLA", "QQQ", "NVDA", "AAPL", "MSFT", "META", "AMZN", "GOOG", "CSCO", "TTWO"]

# NYSE holidays 2025-2026
HOLIDAYS = {
    datetime.date(2025, 1, 1),  datetime.date(2025, 1, 20),  datetime.date(2025, 2, 17),
    datetime.date(2025, 4, 18), datetime.date(2025, 5, 26),  datetime.date(2025, 6, 19),
    datetime.date(2025, 7, 4),  datetime.date(2025, 9, 1),   datetime.date(2025, 11, 27),
    datetime.date(2025, 12, 25),
    datetime.date(2026, 1, 1),  datetime.date(2026, 1, 19),  datetime.date(2026, 2, 16),
    datetime.date(2026, 4, 3),  datetime.date(2026, 5, 25),  datetime.date(2026, 6, 19),
    datetime.date(2026, 7, 3),  datetime.date(2026, 9, 7),   datetime.date(2026, 11, 26),
    datetime.date(2026, 12, 25),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_trading_day(d: datetime.date) -> bool:
    return d.weekday() < 5 and d not in HOLIDAYS

def _ema(values: list, period: int) -> float:
    k = 2.0 / (period + 1)
    v = float(values[0])
    for x in values[1:]:
        v = float(x) * k + v * (1 - k)
    return v

def _pct(n, decimals=2) -> str:
    if n is None:
        return "—"
    return f"{'+'if n>=0 else ''}{n:.{decimals}f}%"

def _price(n) -> str:
    if n is None:
        return "—"
    return f"${n:,.2f}"

def _arrow(n) -> str:
    if n is None:
        return "·"
    return "↑" if n >= 0 else "↓"

def _add_min(t: str, mins: int) -> str:
    h, m = map(int, t.split(":"))
    total = h * 60 + m + mins
    return f"{total // 60:02d}:{total % 60:02d}"

def _ticker_premarket(symbol: str):
    """Returns (price, prev_close, chg_pct) for a symbol."""
    try:
        info = yf.Ticker(symbol).info
        price = info.get("preMarketPrice") or info.get("currentPrice")
        prev  = info.get("regularMarketPreviousClose") or info.get("previousClose")
        chg   = (price - prev) / prev * 100 if (price and prev and prev > 0) else None
        return price, prev, chg
    except Exception:
        return None, None, None


# ── Section 1 — Date & Market Status ─────────────────────────────────────────

def s1_date_status() -> str:
    now_et = datetime.datetime.now(EASTERN)
    today  = now_et.date()
    trading = is_trading_day(today)

    market_open_dt = EASTERN.localize(
        datetime.datetime(today.year, today.month, today.day, 9, 30)
    )
    if now_et < market_open_dt:
        secs = (market_open_dt - now_et).total_seconds()
        h, rem = divmod(int(secs // 60), 60)
        until = f"{h}h {rem}m" if h else f"{rem}m"
        until_str = f"Opens in **{until}**"
    else:
        until_str = "Market is **open**"

    status = "✅ Trading day" if trading else "🚫 Market closed (weekend / holiday)"
    return (
        f"**{today.strftime('%A, %B %-d, %Y')}**\n"
        f"{status}\n"
        f"{until_str} (9:30 AM ET)"
    )


# ── Section 2 — TSLA Direction Bias ──────────────────────────────────────────

def s2_tsla_bias() -> str:
    try:
        t    = yf.Ticker("TSLA")
        info = t.info

        prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
        pre_price  = info.get("preMarketPrice")
        pre_chg    = (
            (pre_price - prev_close) / prev_close * 100
            if (pre_price and prev_close and prev_close > 0) else None
        )

        # Daily history for EMA 9 and prior-day H/L
        hist = t.history(period="20d", interval="1d")
        prior_high = prior_low = ema9 = None
        if len(hist) >= 2:
            prior      = hist.iloc[-2]
            prior_high = float(prior["High"])
            prior_low  = float(prior["Low"])
        if len(hist) >= 9:
            ema9 = _ema(hist["Close"].tolist(), 9)

        # 1-min premarket bars for H/L and volume
        now_et = datetime.datetime.now(EASTERN)
        pm_cutoff = EASTERN.localize(
            datetime.datetime(now_et.year, now_et.month, now_et.day, 9, 30)
        )
        pre_hist = t.history(period="1d", interval="1m", prepost=True)
        pre_bars = (
            pre_hist[pre_hist.index.tz_convert(EASTERN) < pm_cutoff]
            if not pre_hist.empty else pre_hist
        )
        pre_high = float(pre_bars["High"].max()) if not pre_bars.empty else None
        pre_low  = float(pre_bars["Low"].min())  if not pre_bars.empty else None
        pre_vol  = int(pre_bars["Volume"].sum())  if not pre_bars.empty else None

        # EMA context
        if ema9 and prev_close:
            ema_tag = "above prev close ✅" if ema9 > prev_close else "below prev close ⚠️"
        else:
            ema_tag = "unavailable"

        # Bias
        if pre_chg is not None:
            if   pre_chg >=  0.5: bias = "**BULLISH** 🟢"
            elif pre_chg <= -0.5: bias = "**BEARISH** 🔴"
            else:                  bias = "**NEUTRAL** 🟡"
        else:
            bias = "**NEUTRAL** 🟡"

        vol_str = f"{pre_vol:,}" if pre_vol else "—"
        return "\n".join([
            f"Pre-mkt: **{_price(pre_price)}** ({_pct(pre_chg)}) {_arrow(pre_chg)}",
            f"Prev close: {_price(prev_close)}  ·  Pre-mkt vol: {vol_str}",
            f"EMA 9: {_price(ema9)} — {ema_tag}",
            f"Bias: {bias}",
            f"",
            f"Prior day H / L: {_price(prior_high)} / {_price(prior_low)}",
            f"Pre-mkt   H / L: {_price(pre_high)} / {_price(pre_low)}",
        ])
    except Exception as e:
        return f"⚠️ TSLA data error: {e}"


# ── Section 3 — Watchlist Scan ────────────────────────────────────────────────

def s3_watchlist() -> str:
    lines = ["```"]
    lines.append(f"{'SYM':<5} {'PRICE':>8}  {'CHG%':>7}  DIR")
    lines.append("─" * 33)
    for sym in WATCHLIST:
        price, _, chg = _ticker_premarket(sym)
        if price and chg is not None:
            flag     = "*" if abs(chg) >= 1.5 else " "
            chg_fmt  = f"{'+'if chg>=0 else ''}{chg:.2f}%"
            lines.append(f"{flag}{sym:<4} {_price(price):>8}  {chg_fmt:>7}  {_arrow(chg)}")
        else:
            lines.append(f" {sym:<4} {'—':>8}  {'—':>7}  ·")
    lines.append("```")
    lines.append("\\* = mover ≥ ±1.5%")
    return "\n".join(lines)


# ── Section 4 — SPY Market Bias ───────────────────────────────────────────────

def s4_spy_bias() -> str:
    try:
        price, prev, chg = _ticker_premarket("SPY")
        if chg is None:
            return "SPY data unavailable."
        if   chg >=  0.3: label, tone = "**RISK ON** 🟢",  "Futures pointing higher — favorable tape for ORB longs."
        elif chg <= -0.3: label, tone = "**RISK OFF** 🔴", "Futures under pressure — be selective, lean toward shorts or sit out."
        else:              label, tone = "**NEUTRAL** 🟡",  "Flat tape — wait for clear directional conviction at the open."
        return (
            f"SPY pre-mkt: **{_price(price)}** ({_pct(chg)}) {_arrow(chg)}\n"
            f"{label}\n"
            f"*{tone}*"
        )
    except Exception as e:
        return f"⚠️ SPY data error: {e}"


# ── Section 5 — Trading Rules ─────────────────────────────────────────────────

def s5_rules() -> str:
    per_trade_usd  = cfg.STARTING_BALANCE * cfg.PER_TRADE_RISK_PCT
    daily_loss_usd = cfg.STARTING_BALANCE * cfg.DAILY_MAX_LOSS_PCT
    or_end       = _add_min(scfg.OR_START_TIME, scfg.OR_DURATION_MIN)
    trade_end    = _add_min(scfg.OR_START_TIME, scfg.TRADE_WINDOW_DURATION_MIN)
    return "\n".join([
        f"Max trades: **{cfg.MAX_TRADES_PER_DAY}**",
        f"Per-trade risk: **{int(cfg.PER_TRADE_RISK_PCT*100)}%** (${per_trade_usd:.0f} at ${cfg.STARTING_BALANCE:.0f})",
        f"Daily loss limit: **{int(cfg.DAILY_MAX_LOSS_PCT*100)}%** (${daily_loss_usd:.0f} circuit breaker)",
        f"Cooldown after: **{cfg.CONSECUTIVE_LOSS_COOLDOWN}** consecutive losses",
        f"Force close: **{cfg.FORCE_CLOSE_MINUTES_BEFORE_CLOSE} min** before close (3:30 PM ET)",
        f"OR window: **{scfg.OR_START_TIME}–{or_end} ET**",
        f"Trade window: **{scfg.OR_START_TIME}–{trade_end} ET**",
    ])


# ── Section 6 — Agent & Session Status ───────────────────────────────────────

def s6_session() -> str:
    path = os.path.join(PROJECT_ROOT, "state", "session.json")
    try:
        with open(path) as f:
            s = json.load(f)
        halted    = s.get("halted", False)
        remaining = max(0, cfg.MAX_TRADES_PER_DAY - s.get("tradesToday", 0))
        consec    = s.get("consecutiveLosses", 0)
        pnl       = s.get("dailyPnl", 0.0)
        engine    = "🟢 ONLINE" + (" ⛔ HALTED" if halted else "")
        return "\n".join([
            f"Engine: {engine}",
            f"Trades remaining: **{remaining}** of {cfg.MAX_TRADES_PER_DAY}",
            f"Consecutive losses: **{consec}**",
            f"Daily P&L: **{'+'if pnl>=0 else ''}{pnl:.2f}**",
        ])
    except FileNotFoundError:
        return "Engine: 🔴 OFFLINE\n*state/session.json not found — runner not started*"
    except Exception as e:
        return f"⚠️ Session read error: {e}"


# ── Section 7 — Journal Edge Summary ─────────────────────────────────────────

def s7_journal() -> str:
    path = os.path.join(PROJECT_ROOT, "data", "journal.csv")
    try:
        trades = []
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                raw = row.get("pnl", "").strip()
                pnl = float(raw) if raw else None
                trades.append({"pnl": pnl, "ticker": row.get("ticker",""), "grade": row.get("discipline_grade","").strip()})

        closed = [t for t in trades if t["pnl"] is not None]
        if not closed:
            return "No closed trades in journal yet."

        wins     = [t for t in closed if t["pnl"] > 0]
        losses   = [t for t in closed if t["pnl"] < 0]
        net_pnl  = sum(t["pnl"] for t in closed)
        win_rate = len(wins) / len(closed) * 100

        last = closed[-1]
        outcome = "WIN ✅" if last["pnl"] > 0 else "LOSS ❌" if last["pnl"] < 0 else "FLAT"
        last_str = f"{last['ticker']} {outcome} ${abs(last['pnl']):.2f} · Grade: {last['grade'] or '—'}"

        # Streak
        streak_type = "W" if closed[-1]["pnl"] >= 0 else "L"
        streak = 0
        for t in reversed(closed):
            if (streak_type == "W" and t["pnl"] >= 0) or (streak_type == "L" and t["pnl"] < 0):
                streak += 1
            else:
                break
        streak_emoji = "🔥" if (streak >= 2 and streak_type == "W") else ("⚠️" if streak >= 2 else "")
        streak_str = f"**{streak}{streak_type}** {streak_emoji}"

        return "\n".join([
            f"Win rate: **{win_rate:.0f}%** ({len(wins)}W / {len(losses)}L)",
            f"Net P&L: **{'+'if net_pnl>=0 else ''}{net_pnl:.2f}**",
            f"Last trade: {last_str}",
            f"Current streak: {streak_str}",
        ])
    except FileNotFoundError:
        return "No journal found."
    except Exception as e:
        return f"⚠️ Journal read error: {e}"


# ── Section 8 — Edge Reminder ─────────────────────────────────────────────────

def s8_edge() -> str:
    return "*ORB only. First 90 minutes. Risk $10 per trade. Let the setup come to you.*"


# ── Send ──────────────────────────────────────────────────────────────────────

def send_brief():
    if not WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK_URL not set in .env")
        sys.exit(1)

    now_az = datetime.datetime.now(ARIZONA)

    print("Fetching market data…")
    fields = [
        {"name": "📅  DATE & MARKET STATUS",   "value": s1_date_status(), "inline": False},
        {"name": "📈  TSLA DIRECTION BIAS",     "value": s2_tsla_bias(),   "inline": False},
        {"name": "🔍  WATCHLIST SCAN",          "value": s3_watchlist(),   "inline": False},
        {"name": "📊  SPY MARKET BIAS",         "value": s4_spy_bias(),    "inline": False},
        {"name": "⚙️   TODAY'S TRADING RULES",  "value": s5_rules(),       "inline": False},
        {"name": "🤖  AGENT & SESSION STATUS",  "value": s6_session(),     "inline": False},
        {"name": "📓  JOURNAL EDGE SUMMARY",    "value": s7_journal(),     "inline": False},
        {"name": "💡  SILENT'S EDGE REMINDER",  "value": s8_edge(),        "inline": False},
    ]

    # Measure total embed size; split at section 5 if approaching 5800 chars
    total = sum(len(f["name"]) + len(f["value"]) for f in fields) + 40  # +40 for title/footer
    split = total > 5800

    footer_text = f"ClawOps · Paper Mode · {now_az.strftime('%-I:%M %p AZ')}"

    if split:
        embeds = [
            {
                "title": "🌅  Silent's Morning Brief",
                "color": EMBED_COLOR,
                "fields": fields[:4],
            },
            {
                "color": EMBED_COLOR,
                "fields": fields[4:],
                "footer": {"text": footer_text},
            },
        ]
    else:
        embeds = [{
            "title": "🌅  Silent's Morning Brief",
            "color": EMBED_COLOR,
            "fields": fields,
            "footer": {"text": footer_text},
        }]

    resp = requests.post(WEBHOOK_URL, json={"embeds": embeds}, timeout=20)
    if resp.status_code == 204:
        print(f"✅  Morning brief sent at {now_az.strftime('%-I:%M %p AZ')} ({'2 embeds' if split else '1 embed'})")
    else:
        print(f"❌  Discord error {resp.status_code}: {resp.text}")
        sys.exit(1)


if __name__ == "__main__":
    send_brief()
