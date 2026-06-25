"""
Discord webhook notifier — fire-and-forget, never blocks the trading flow.

Set DISCORD_WEBHOOK_URL in .env to enable. Silent if the variable is unset
or the POST fails (network down, bad URL, etc.).
"""

import json
import os
import threading
import urllib.request
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")

_COLOR = {
    "green":  0x00C087,
    "red":    0xF6465D,
    "yellow": 0xF0B429,
    "blue":   0x1A6FD4,
}

_AZ = ZoneInfo("America/Phoenix")


def _now_az() -> str:
    return datetime.now(_AZ).strftime("%I:%M:%S %p AZ")


def _post(payload: dict):
    if not _WEBHOOK:
        return
    try:
        req = urllib.request.Request(
            _WEBHOOK,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def _send(payload: dict):
    threading.Thread(target=_post, args=(payload,), daemon=True).start()


def _embed(title: str, description: str, color: str,
           fields: Optional[list] = None) -> dict:
    e = {
        "title":       title,
        "description": description,
        "color":       _COLOR.get(color, _COLOR["blue"]),
        "footer":      {"text": _now_az()},
    }
    if fields:
        e["fields"] = [
            {"name": f["name"], "value": str(f["value"]), "inline": f.get("inline", True)}
            for f in fields
        ]
    return {"embeds": [e]}


# ─── Public API ───────────────────────────────────────────────────────────────

def signal_fired(symbol: str, direction: str, entry_trigger: float,
                 or_high: float, or_low: float, volume_ratio: float):
    _send(_embed(
        title=f"⚡ ORB Signal — {symbol} {direction.upper()}",
        description=f"Entry trigger: **${entry_trigger:.2f}**",
        color="green" if direction == "long" else "red",
        fields=[
            {"name": "OR High",      "value": f"${or_high:.2f}"},
            {"name": "OR Low",       "value": f"${or_low:.2f}"},
            {"name": "Volume Ratio", "value": f"{volume_ratio:.1f}×"},
        ],
    ))


def risk_decision(approved: bool, reason: str = "",
                  quantity: int = 0, dollar_risk: float = 0.0):
    if approved:
        _send(_embed(
            title="✅ Risk Engine — APPROVED",
            description=f"{quantity} contract(s) · **${dollar_risk:.2f}** at risk",
            color="green",
        ))
    else:
        _send(_embed(
            title="🚫 Risk Engine — REJECTED",
            description=reason,
            color="red",
        ))


def trade_validated(ticker: str, setup: str, go_nogo: str,
                    rr_ratio: float, dollar_risk):
    ok = go_nogo == "GO"
    dr = f"${float(dollar_risk):.2f}" if dollar_risk else "—"
    _send(_embed(
        title=f"{'✅' if ok else '❌'} Validator — {go_nogo}",
        description=f"**{ticker}** · {setup}",
        color="green" if ok else "red",
        fields=[
            {"name": "R/R",         "value": f"{rr_ratio}R"},
            {"name": "Dollar Risk", "value": dr},
        ],
    ))


def trade_logged(ticker: str, strategy: str, pnl: str):
    try:
        pnl_f = float(pnl) if pnl else None
    except ValueError:
        pnl_f = None
    color   = "green" if (pnl_f or 0) >= 0 else "red"
    pnl_str = (f"+${pnl_f:.2f}" if pnl_f >= 0 else f"-${abs(pnl_f):.2f}") if pnl_f is not None else "—"
    _send(_embed(
        title=f"📓 Trade Logged — {ticker}",
        description=f"{strategy} · P&L: **{pnl_str}**",
        color=color,
    ))


def session_halted(reason: str):
    _send(_embed(
        title="🛑 Session HALTED",
        description=reason,
        color="red",
    ))


def session_reset():
    _send(_embed(
        title="🔄 New Trading Day",
        description="Session reset — risk engine cleared.",
        color="blue",
    ))
