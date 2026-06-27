"""
utils/event_log.py — Single writer for state/decisions.jsonl.

log_event() is the only path that appends to the decision audit log.
filelock prevents interleaved writes from concurrent processes.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from filelock import FileLock

PROJECT_ROOT    = Path(__file__).resolve().parent.parent
DECISIONS_FILE  = PROJECT_ROOT / "state" / "decisions.jsonl"
LOCK_FILE       = PROJECT_ROOT / "state" / "decisions.lock"

_ET = ZoneInfo("America/New_York")


def _lock() -> FileLock:
    DECISIONS_FILE.parent.mkdir(exist_ok=True)
    return FileLock(str(LOCK_FILE), timeout=5)


def log_event(
    kind:    str,
    message: str,
    agent:   str,
    meta:    Optional[Dict[str, Any]] = None,
) -> None:
    """
    Append one decision event to state/decisions.jsonl.

    kind    : "signal" | "approved" | "rejected" | "halt" | "open"
              | "close" | "info"
    message : human-readable description
    agent   : canonical agent name ("hawk/ORB", "vault", "runner", etc.)
    meta    : optional dict of structured data attached to the event
    """
    event: Dict[str, Any] = {
        "ts":      datetime.now(_ET).isoformat(),
        "kind":    kind,
        "agent":   agent,
        "message": message,
    }
    if meta:
        event["meta"] = meta

    with _lock():
        with open(DECISIONS_FILE, "a") as f:
            f.write(json.dumps(event) + "\n")
