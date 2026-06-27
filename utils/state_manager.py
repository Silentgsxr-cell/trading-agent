"""
utils/state_manager.py — Single writer for state/session.json.

All writes go through here. filelock prevents concurrent corruption
when runner.py and dashboard/app.py are both running.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from filelock import FileLock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR    = PROJECT_ROOT / "state"
SESSION_FILE = STATE_DIR / "session.json"
LOCK_FILE    = STATE_DIR / "session.lock"

_DEFAULTS = {
    "date":              "",
    "startingBalance":   1000.0,
    "currentBalance":    1000.0,
    "dailyPnl":          0.0,
    "consecutiveLosses": 0,
    "halted":            False,
    "haltReason":        None,
    "openPositions":     0,
    "tradesToday":       0,
    "runnerOnline":      False,
    "lastHeartbeat":     None,
}


def _lock() -> FileLock:
    STATE_DIR.mkdir(exist_ok=True)
    return FileLock(str(LOCK_FILE), timeout=5)


def get_session() -> dict:
    """Read current session state. Returns defaults if file missing."""
    try:
        with _lock():
            return json.loads(SESSION_FILE.read_text())
    except Exception:
        return {**_DEFAULTS, "date": datetime.now().strftime("%Y-%m-%d")}


def update_session(diff: dict) -> dict:
    """Merge diff into current session state and write atomically."""
    with _lock():
        try:
            current = json.loads(SESSION_FILE.read_text())
        except Exception:
            current = {**_DEFAULTS, "date": datetime.now().strftime("%Y-%m-%d")}
        current.update(diff)
        _write(current)
        return current


def halt_session(reason: str) -> dict:
    return update_session({"halted": True, "haltReason": reason})


def reset_session(starting_balance: float = 1000.0) -> dict:
    fresh = {
        **_DEFAULTS,
        "date":            datetime.now().strftime("%Y-%m-%d"),
        "startingBalance": starting_balance,
        "currentBalance":  starting_balance,
        "runnerOnline":    True,
        "lastHeartbeat":   datetime.now().isoformat(),
    }
    with _lock():
        _write(fresh)
    return fresh


def heartbeat() -> None:
    """Called by runner every loop to prove it's alive."""
    update_session({"runnerOnline": True, "lastHeartbeat": datetime.now().isoformat()})


def set_offline() -> None:
    update_session({"runnerOnline": False})


# ---------------------------------------------------------------------------

def _write(data: dict) -> None:
    """Atomic write via temp file + rename."""
    tmp = SESSION_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(SESSION_FILE)
