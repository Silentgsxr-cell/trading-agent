#!/usr/bin/env python3
"""
runner.py — ClawOps live agent loop.

Orchestrates:
  yfinance 2-min bars → Signaos (multi-strategy signal engine)
                       → RiskEngine (veto + sizing)
                       → state/ files (Mission Control feed)

Writes:
  state/session.json     live session snapshot (atomic overwrite each poll)
  state/decisions.jsonl  full decision audit log (append-only)
  state/signals.jsonl    all Signaos signal outputs (append-only)

Usage:
  python3 runner.py

Ctrl-C for clean shutdown.
"""

import json
import os
import sys
import time
import signal as _signal
from datetime import datetime, time as dtime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import yfinance as yf

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from agents.signaos import Signaos, RankedSignal
from agents.strategies import EvalContext
from agents.risk_engine import RiskEngine
from config import risk_config as cfg
from config import strategy_config as scfg

_ET = ZoneInfo("America/New_York")

STATE_DIR      = ROOT / "state"
SESSION_FILE   = STATE_DIR / "session.json"
DECISIONS_FILE = STATE_DIR / "decisions.jsonl"
SIGNALS_FILE   = STATE_DIR / "signals.jsonl"

POLL_INTERVAL = 30
SYMBOL        = scfg.SYMBOL

_MARKET_OPEN  = dtime(9, 30)
_MARKET_CLOSE = dtime(16, 0)
_PRE_MARKET   = dtime(4, 0)


# ---------------------------------------------------------------------------
# Clock helpers
# ---------------------------------------------------------------------------

def _now_et() -> datetime:
    return datetime.now(_ET)


def _et_time(now: datetime) -> dtime:
    return now.time().replace(tzinfo=None)


def _is_market_open(now: datetime) -> bool:
    if now.weekday() >= 5:
        return False
    t = _et_time(now)
    return _MARKET_OPEN <= t < _MARKET_CLOSE


def _is_pre_market(now: datetime) -> bool:
    if now.weekday() >= 5:
        return False
    t = _et_time(now)
    return _PRE_MARKET <= t < _MARKET_OPEN


# ---------------------------------------------------------------------------
# State writers
# ---------------------------------------------------------------------------

def write_session(engine: RiskEngine) -> None:
    s = engine.session
    payload = {
        "date":              s.date,
        "startingBalance":   s.starting_balance,
        "currentBalance":    round(s.current_balance, 2),
        "dailyPnl":          round(s.daily_pnl, 2),
        "consecutiveLosses": s.consecutive_losses,
        "halted":            s.halted,
        "haltReason":        s.halt_reason,
        "openPositions":     len(s.open_positions),
        "tradesToday":       s.trades_opened_today,
    }
    tmp = SESSION_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(SESSION_FILE)


def _append_jsonl(path: Path, obj: dict) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(obj) + "\n")


def log_decision(kind: str, agent: str, message: str, meta: Optional[dict] = None) -> None:
    event: dict = {
        "ts":      _now_et().isoformat(),
        "kind":    kind,
        "agent":   agent,
        "message": message,
    }
    if meta:
        event["meta"] = meta
    _append_jsonl(DECISIONS_FILE, event)
    print(f"[{agent:16s}] {kind.upper():8s}  {message}")


def log_signal(ranked: RankedSignal) -> None:
    _append_jsonl(SIGNALS_FILE, ranked.to_dict())


# ---------------------------------------------------------------------------
# Data fetcher
# ---------------------------------------------------------------------------

def fetch_bars(symbol: str) -> list:
    """
    Pull completed 2-min bars for today.
    Drops the last bar — it is still forming.
    Returns bars with naive ET timestamps for the strategy engine.
    """
    try:
        hist = yf.Ticker(symbol).history(period="1d", interval="2m")
        if hist.empty or len(hist) < 2:
            return []
        hist = hist.iloc[:-1]
        bars = []
        for ts, row in hist.iterrows():
            ts_et = ts.tz_convert(_ET).to_pydatetime().replace(tzinfo=None)
            bars.append({
                "timestamp": ts_et,
                "open":   float(row["Open"]),
                "high":   float(row["High"]),
                "low":    float(row["Low"]),
                "close":  float(row["Close"]),
                "volume": int(row["Volume"]),
            })
        return bars
    except Exception as exc:
        print(f"[runner           ] bar fetch error: {exc}")
        return []


def get_spy_bias() -> str:
    try:
        hist = yf.Ticker("SPY").history(period="2d", interval="1d")
        if len(hist) >= 2:
            closes = list(hist["Close"])
            pct = (closes[-1] - closes[-2]) / closes[-2] * 100
            if pct > 0.2:
                return "Bullish"
            if pct < -0.2:
                return "Bearish"
    except Exception:
        pass
    return "Neutral"


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run() -> None:
    STATE_DIR.mkdir(exist_ok=True)

    now          = _now_et()
    session_date = now.strftime("%Y-%m-%d")

    engine  = RiskEngine(cfg.STARTING_BALANCE)
    engine.session.date = session_date
    signaos = Signaos()

    write_session(engine)
    log_decision("info", "runner", f"HAWK + ClawOps runner started — {SYMBOL}", {
        "balance": cfg.STARTING_BALANCE,
        "date":    session_date,
        "strategies": [s.name for s in signaos.strategies],
    })

    print(f"\n  ClawOps Runner — {SYMBOL} | {session_date}")
    print(f"  Strategies: {', '.join(s.name for s in signaos.strategies)}")
    print(f"  Poll: {POLL_INTERVAL}s | State: {STATE_DIR}\n")

    all_bars:     list = []
    last_bar_ts:  Optional[datetime] = None
    spy_bias:     str  = "Neutral"
    spy_last_fetch: Optional[datetime] = None
    running = True

    def _shutdown(sig, frame):
        nonlocal running
        print("\n[runner           ] SIGINT — shutting down cleanly...")
        running = False

    _signal.signal(_signal.SIGINT,  _shutdown)
    _signal.signal(_signal.SIGTERM, _shutdown)

    while running:
        now   = _now_et()
        today = now.strftime("%Y-%m-%d")

        # Daily session roll-over.
        if today != session_date:
            session_date = today
            engine       = RiskEngine(cfg.STARTING_BALANCE)
            engine.session.date = session_date
            signaos.reset_session()
            all_bars    = []
            last_bar_ts = None
            write_session(engine)
            log_decision("info", "runner", f"New session — {session_date}")

        if not _is_market_open(now):
            status = "PRE-MARKET" if _is_pre_market(now) else "CLOSED"
            print(f"[runner           ] {status} {now.strftime('%H:%M ET')} — sleeping {POLL_INTERVAL}s")
            time.sleep(POLL_INTERVAL)
            continue

        # Refresh SPY bias every 5 minutes.
        if spy_last_fetch is None or (now - spy_last_fetch).seconds >= 300:
            spy_bias       = get_spy_bias()
            spy_last_fetch = now

        # Fetch 2-min bars.
        all_bars = fetch_bars(SYMBOL)
        new_bars = [
            b for b in all_bars
            if last_bar_ts is None or b["timestamp"] > last_bar_ts
        ]
        if new_bars:
            last_bar_ts = new_bars[-1]["timestamp"]

        # Build context for Signaos.
        context = EvalContext(
            now         = now,
            symbol      = SYMBOL,
            bars        = all_bars,
            new_bars    = new_bars,
            news        = [],       # wired up when News Agent is built
            spy_bias    = spy_bias,
            market_data = {},
        )

        # Poll Signaos — get ranked signals this tick.
        ranked_signals = signaos.poll(context)

        for ranked in ranked_signals:
            sig = ranked.signal
            log_signal(ranked)
            log_decision(
                "signal", f"hawk/{sig.strategy_name}",
                f"[{ranked.conviction_tier}] {sig.direction.upper()} {sig.ticker} — "
                f"{sig.reasoning[:80]}",
                ranked.to_dict(),
            )

            # Only route A and S tier to VAULT for sizing/approval.
            if ranked.conviction_tier not in ("S", "A"):
                log_decision(
                    "info", "hawk",
                    f"[{ranked.conviction_tier}] signal logged but not routed "
                    f"(below A tier, score={ranked.final_score})",
                )
                continue

            # Placeholder premium — 1% of price until Execution Agent provides real ask.
            placeholder_premium = round(sig.metadata.get("entry_trigger", 1.0) * 0.01, 2)
            result = engine.evaluate(sig.direction, placeholder_premium)

            if result["approved"]:
                log_decision(
                    "approved", "vault",
                    f"APPROVED — {result['quantity']} contract(s) "
                    f"@ ${placeholder_premium:.2f} premium, "
                    f"risk ${result['dollar_risk']:.2f}, "
                    f"stop ${result['stop_premium']:.4f}",
                    result,
                )
            else:
                log_decision(
                    "rejected", "vault",
                    f"REJECTED — {result['reason']}",
                    result,
                )

            write_session(engine)

        # Time-based force-close guard.
        if engine.check_force_close(now) and engine.session.open_positions:
            log_decision(
                "halt", "vault",
                "Force-close window reached — all open positions must be closed",
            )

        write_session(engine)

        t   = now.strftime("%H:%M:%S ET")
        bal = engine.session.current_balance
        pnl = engine.session.daily_pnl
        print(
            f"[runner           ] {t} | new bars: {len(new_bars):2d} | "
            f"signals: {len(ranked_signals)} | "
            f"balance: ${bal:.2f} | P&L: ${pnl:+.2f} | SPY: {spy_bias}"
        )

        time.sleep(POLL_INTERVAL)

    log_decision("info", "runner", "Runner stopped (clean shutdown)")
    write_session(engine)
    print("[runner           ] Stopped.")


if __name__ == "__main__":
    run()
