#!/usr/bin/env python3
"""
utils/daitaos.py — DaiTaos daily intelligence brief.
Sends a Discord embed: market status, TSLA bias, watchlist scan,
SPY tone, trading rules, session status, journal edge, edge reminder.
Watchlist and send time are loaded from data/daitaos_config.json.
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
from utils.daitaos_logger import log

try:
    from utils.agent_brain import AgentBrain
    brain = AgentBrain("INTEL", "#4fc3f7")
except Exception:
    brain = None

WEBHOOK_URL  = os.getenv("DISCORD_MORNING_BRIEF_WEBHOOK", "")
EASTERN      = pytz.timezone("America/New_York")
ARIZONA      = pytz.timezone("America/Phoenix")
EMBED_COLOR  = 0x1A2744

CONFIG_PATH = os.path.join(PROJECT_ROOT, "data", "daitaos_config.json")

DEFAULT_CONFIG = {
    "send_time": "06:20",
    "watchlist": ["TSLA", "QQQ", "NVDA", "AAPL", "MSFT", "META", "AMZN", "GOOG", "CSCO", "TTWO"],
    "timezone": "America/Phoenix",
}

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


def load_config() -> dict:
    try:
        with open(CONFIG_PATH) as f:
            data = json.load(f)
        return {**DEFAULT_CONFIG, **data}
    except Exception:
        return DEFAULT_CONFIG.copy()


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
    watchlist = load_config().get("watchlist", DEFAULT_CONFIG["watchlist"])
    lines = ["```"]
    lines.append(f"{'SYM':<5} {'PRICE':>8}  {'CHG%':>7}  DIR")
    lines.append("─" * 33)
    for sym in watchlist:
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


def s9_dev_overnight() -> str:
    """Dev Agent overnight summary for the morning brief."""
    tickets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tickets.json")
    audit_path   = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "dev_agent_audit.log")

    try:
        if not os.path.exists(tickets_path):
            return "No ticket database found."
        with open(tickets_path) as f:
            db = json.load(f)

        tickets    = db.get("tickets", [])
        paused     = db.get("paused", False)
        cutoff     = datetime.datetime.now() - datetime.timedelta(hours=16)  # since ~yesterday's brief

        # Completed and failed since last brief
        completed = [t for t in tickets if t.get("status") == "done"
                     and t.get("completed_at")
                     and datetime.datetime.fromisoformat(t["completed_at"]) > cutoff]
        failed    = [t for t in tickets if t.get("status") == "failed"
                     and t.get("started_at")
                     and datetime.datetime.fromisoformat(t["started_at"]) > cutoff]
        open_q    = [t for t in tickets if t.get("status") == "open"]
        review    = [t for t in tickets if t.get("status") == "needs_review"]

        lines = []
        if not completed and not failed:
            lines.append("No dev agent activity overnight.")
        else:
            if completed:
                lines.append(f"✅ **{len(completed)} ticket(s) completed overnight:**")
                for t in completed:
                    changed = len(t.get("files_modified", [])) + len(t.get("files_created", []))
                    lines.append(f"  • `{t['id']}` — {t['title'][:50]} ({changed} files)")
            if failed:
                lines.append(f"❌ **{len(failed)} ticket(s) failed:**")
                for t in failed:
                    lines.append(f"  • `{t['id']}` — {t['title'][:50]}")

        lines.append(f"📋 Queue: {len(open_q)} open · {len(review)} needs review")
        if paused:
            lines.append("⏸ Dev agent is **paused**")

        # Security flags from audit log (yesterday's run)
        if os.path.exists(audit_path):
            try:
                with open(audit_path) as f:
                    recent_lines = f.readlines()[-20:]
                flags = [l.strip() for l in recent_lines if "CRITICAL" in l or "failed" in l.lower()]
                if flags:
                    lines.append(f"⚠️ {len(flags)} security/failure flag(s) in audit log")
            except Exception:
                pass

        return "\n".join(lines)
    except Exception as exc:
        return f"Dev agent status unavailable: {exc}"


# ── Send ──────────────────────────────────────────────────────────────────────

def send_brief():
    if not WEBHOOK_URL:
        print("ERROR: DISCORD_MORNING_BRIEF_WEBHOOK not set in .env")
        if brain:
            brain.error("DISCORD_MORNING_BRIEF_WEBHOOK not set in .env")
        sys.exit(1)

    if brain:
        brain.start_task("Building morning brief — 9 sections", queue_len=9)

    now_az = datetime.datetime.now(ARIZONA)

    print("Fetching market data…")
    if brain:
        brain.update_task("Fetching market data + watchlist scan", progress_pct=20)
    fields = [
        {"name": "📅  DATE & MARKET STATUS",   "value": s1_date_status(), "inline": False},
        {"name": "📈  TSLA DIRECTION BIAS",     "value": s2_tsla_bias(),   "inline": False},
        {"name": "🔍  WATCHLIST SCAN",          "value": s3_watchlist(),   "inline": False},
        {"name": "📊  SPY MARKET BIAS",         "value": s4_spy_bias(),    "inline": False},
        {"name": "⚙️   TODAY'S TRADING RULES",  "value": s5_rules(),       "inline": False},
        {"name": "🤖  AGENT & SESSION STATUS",  "value": s6_session(),     "inline": False},
        {"name": "📓  JOURNAL EDGE SUMMARY",    "value": s7_journal(),        "inline": False},
        {"name": "💡  SILENT'S EDGE REMINDER",  "value": s8_edge(),           "inline": False},
        {"name": "⌬   DEV AGENT OVERNIGHT",     "value": s9_dev_overnight(),  "inline": False},
    ]
    if brain:
        brain.update_task("Composing Discord embed", progress_pct=80)

    # Measure total embed size; split at section 5 if approaching 5800 chars
    total = sum(len(f["name"]) + len(f["value"]) for f in fields) + 40
    split = total > 5800

    footer_text = f"ClawOps · DaiTaos · {now_az.strftime('%-I:%M %p AZ')}"

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
        label = "2 embeds" if split else "1 embed"
        print(f"✅  Morning brief sent at {now_az.strftime('%-I:%M %p AZ')} ({label})")
        tsla_line = fields[1]["value"].split("\n")[0]   # first line: price + bias
        spy_lines = fields[3]["value"].split("\n")
        spy_line  = spy_lines[1] if len(spy_lines) > 1 else spy_lines[0]   # 2nd line normally; single-line on data-unavailable/error fallback
        log("🌅", "Morning Brief Sent",
            f"**TSLA:** {tsla_line}\n"
            f"**SPY:** {spy_line}\n"
            f"Sent at {now_az.strftime('%-I:%M %p AZ')} · {label}")

        # Write structured log for Master Chief home page
        _write_brief_log(fields, now_az)
        if brain:
            brain.finish_task(f"Sent morning brief — {tsla_line}")
    else:
        print(f"❌  Discord error {resp.status_code}: {resp.text}")
        log("⚠️", "Morning Brief Failed", f"Discord returned {resp.status_code}")
        if brain:
            brain.error(f"Discord error {resp.status_code}")
        sys.exit(1)


def _write_brief_log(fields: list, now_az: datetime.datetime) -> None:
    """Write a structured JSON log so Master Chief home page can display the brief."""
    try:
        log_path = os.path.join(PROJECT_ROOT, "logs", "morning_brief_log.json")
        watchlist_raw = fields[2]["value"]  # s3_watchlist section
        watchlist_lines = [
            l.strip() for l in watchlist_raw.split("\n")
            if l.strip() and not l.startswith("#") and len(l.strip()) > 2
        ]
        brief = {
            "sent_at": now_az.isoformat(),
            "sections": {
                "date_status":   fields[0]["value"].split("\n")[0].strip(),
                "tsla":          fields[1]["value"].split("\n")[0].strip(),
                "watchlist":     watchlist_lines[:10],
                "spy":           fields[3]["value"].split("\n")[1].strip() if "\n" in fields[3]["value"] else fields[3]["value"].strip(),
                "catalysts":     fields[4]["value"].strip()[:400],  # today's rules as context
                "dev_overnight": fields[8]["value"].strip()[:400] if len(fields) > 8 else "",
            },
        }
        with open(log_path, "w") as f:
            json.dump(brief, f, indent=2)
    except Exception as exc:
        print(f"⚠️  Could not write morning_brief_log.json: {exc}")


if __name__ == "__main__":
    send_brief()
