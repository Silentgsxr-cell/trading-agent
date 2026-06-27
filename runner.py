#!/usr/bin/env python3
"""
runner.py — ClawOps live agent loop.

Orchestrates:  yfinance 2-min bars → ORBSignalAgent → RiskEngine → (stub) Execution
Writes state files consumed by Mission Control at localhost:3000:
  state/session.json     live session snapshot (overwritten each poll)
  state/decisions.jsonl  decision audit log (append-only)
  state/signals.jsonl    raw signal feed (append-only)

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
from zoneinfo import ZoneInfo

from typing import Optional

import yfinance as yf

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from agents.signal_agent import ORBSignalAgent
from agents.risk_engine import RiskEngine
from config import risk_config as cfg
from config import strategy_config as scfg

_ET = ZoneInfo("America/New_York")

STATE_DIR      = ROOT / "state"
SESSION_FILE   = STATE_DIR / "session.json"
DECISIONS_FILE = STATE_DIR / "decisions.jsonl"
SIGNALS_FILE   = STATE_DIR / "signals.jsonl"

POLL_INTERVAL = 30        # seconds between yfinance polls
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
    """Return naive local time in ET for simple comparisons."""
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
    # Atomic write so Mission Control never reads a partial file.
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
    print(f"[{agent:12s}] {kind.upper():8s}  {message}")


def log_signal(signal: dict) -> None:
    out = {
        **signal,
        "timestamp": signal["timestamp"].isoformat(),
    }
    _append_jsonl(SIGNALS_FILE, out)


# ---------------------------------------------------------------------------
# Data fetcher
# ---------------------------------------------------------------------------

def fetch_bars(symbol: str) -> list[dict]:
    """
    Pull completed 2-min bars for today from yfinance.
    Drops the last bar — it is still forming.
    Returns bars with naive ET timestamps for the signal agent.
    """
    try:
        hist = yf.Ticker(symbol).history(period="1d", interval="2m")
        if hist.empty or len(hist) < 2:
            return []
        hist = hist.iloc[:-1]   # drop forming bar
        bars = []
        for ts, row in hist.iterrows():
            # yfinance returns tz-aware Timestamps; convert to naive ET.
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
        print(f"[runner      ] bar fetch error: {exc}")
        return []


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run() -> None:
    STATE_DIR.mkdir(exist_ok=True)

    now            = _now_et()
    session_date   = now.strftime("%Y-%m-%d")

    engine         = RiskEngine(cfg.STARTING_BALANCE)
    engine.session.date = session_date
    signal_agent   = ORBSignalAgent(SYMBOL)

    write_session(engine)
    log_decision("info", "runner", f"ClawOps runner started — {SYMBOL} ORB paper strategy", {
        "balance": cfg.STARTING_BALANCE,
        "date":    session_date,
    })

    print(f"\n  ClawOps Runner — {SYMBOL} | {session_date}")
    print(f"  Poll: {POLL_INTERVAL}s | State: {STATE_DIR}\n")

    last_bar_ts: Optional[datetime] = None
    running = True

    def _shutdown(sig, frame):
        nonlocal running
        print("\n[runner      ] SIGINT — shutting down cleanly...")
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
            signal_agent.reset_session()
            last_bar_ts = None
            write_session(engine)
            log_decision("info", "runner", f"New session — {session_date}")

        if not _is_market_open(now):
            status = "PRE-MARKET" if _is_pre_market(now) else "CLOSED"
            print(f"[runner      ] {status} {now.strftime('%H:%M ET')} — sleeping {POLL_INTERVAL}s")
            time.sleep(POLL_INTERVAL)
            continue

        # --- Inside market hours ---
        bars     = fetch_bars(SYMBOL)
        new_bars = [
            b for b in bars
            if last_bar_ts is None or b["timestamp"] > last_bar_ts
        ]

        for bar in new_bars:
            last_bar_ts = bar["timestamp"]
            signal = signal_agent.on_bar(bar)

            if signal is None:
                continue

            # Signal agent found a breakout — log it and run through risk engine.
            log_signal(signal)
            log_decision(
                "signal", "signal_agent",
                f"ORB breakout {signal['direction'].upper()} {SYMBOL} "
                f"@ {signal['entry_trigger']:.2f} "
                f"(vol_ratio={signal['volume_ratio']}, body={signal['body_ratio']})",
                {
                    "direction":     signal["direction"],
                    "entry_trigger": signal["entry_trigger"],
                    "or_high":       signal["or_high"],
                    "or_low":        signal["or_low"],
                    "volume_ratio":  signal["volume_ratio"],
                    "body_ratio":    signal["body_ratio"],
                },
            )

            # Placeholder premium: 1 % of underlying price (roughly ATM 0DTE).
            # Execution agent will supply the real ask when it is built.
            placeholder_premium = round(signal["entry_trigger"] * 0.01, 2)
            result = engine.evaluate(signal["direction"], placeholder_premium)

            if result["approved"]:
                log_decision(
                    "approved", "risk_engine",
                    f"APPROVED — {result['quantity']} contract(s) "
                    f"@ ${placeholder_premium:.2f} premium, "
                    f"risk ${result['dollar_risk']:.2f}, "
                    f"stop ${result['stop_premium']:.4f}",
                    result,
                )
            else:
                log_decision(
                    "rejected", "risk_engine",
                    f"REJECTED — {result['reason']}",
                    result,
                )

            write_session(engine)

        # Time-based force-close guard (execution agent not built yet — just logs).
        if engine.check_force_close(now) and engine.session.open_positions:
            log_decision(
                "halt", "risk_engine",
                "Force-close window reached — all open positions must be closed",
            )

        write_session(engine)

        t = now.strftime("%H:%M:%S ET")
        bal = engine.session.current_balance
        pnl = engine.session.daily_pnl
        print(
            f"[runner      ] {t} | new bars: {len(new_bars):2d} | "
            f"balance: ${bal:.2f} | daily P&L: ${pnl:+.2f} | "
            f"halted: {engine.session.halted}"
        )

        time.sleep(POLL_INTERVAL)

    log_decision("info", "runner", "Runner stopped (clean shutdown)")
    write_session(engine)
    print("[runner      ] Stopped.")


if __name__ == "__main__":
    run()
