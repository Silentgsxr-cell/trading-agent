"""
utils/journal_writer.py — Single writer for data/journal.csv.

append_trade() is the only path that adds rows. filelock prevents
concurrent appends from runner and dashboard hitting the file at once.
"""

import csv
import os
from pathlib import Path
from typing import List, Optional

from filelock import FileLock

PROJECT_ROOT  = Path(__file__).resolve().parent.parent
JOURNAL_FILE  = PROJECT_ROOT / "data" / "journal.csv"
LOCK_FILE     = PROJECT_ROOT / "data" / "journal.lock"

FIELDNAMES = [
    "date", "ticker", "strategy", "entry", "stop", "target",
    "exit", "pnl", "trade_type", "was_planned", "chased",
    "followed_stop", "lesson", "discipline_grade",
]


def _lock() -> FileLock:
    JOURNAL_FILE.parent.mkdir(exist_ok=True)
    return FileLock(str(LOCK_FILE), timeout=5)


def get_trades() -> List[dict]:
    """Read all journal rows. Returns [] if file missing."""
    try:
        with _lock():
            with open(JOURNAL_FILE, newline="") as f:
                return list(csv.DictReader(f))
    except FileNotFoundError:
        return []
    except Exception:
        return []


def append_trade(trade: dict) -> None:
    """
    Append one row to journal.csv. Creates file with header if missing.
    trade dict keys should match FIELDNAMES; unknown keys are silently dropped.
    """
    row = {k: trade.get(k, "") for k in FIELDNAMES}
    with _lock():
        exists = JOURNAL_FILE.exists()
        with open(JOURNAL_FILE, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            if not exists:
                writer.writeheader()
            writer.writerow(row)
