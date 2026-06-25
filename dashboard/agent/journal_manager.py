"""
CSV-backed trade journal.

Writes to data/journal.csv at the project root (next to agents/, config/, etc.).
The CSV file and data/ directory are created on first write if they don't exist.
"""

import csv
from pathlib import Path

_JOURNAL = Path(__file__).parent.parent.parent / "data" / "journal.csv"

_FIELDS = [
    "date", "ticker", "strategy", "entry", "stop", "target", "exit",
    "pnl", "trade_type", "was_planned", "chased", "followed_stop",
    "lesson", "discipline_grade",
]


def _ensure():
    _JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    if not _JOURNAL.exists():
        with open(_JOURNAL, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=_FIELDS).writeheader()


def save_entry(data: dict):
    _ensure()
    with open(_JOURNAL, "a", newline="") as f:
        csv.DictWriter(f, fieldnames=_FIELDS).writerow(
            {k: data.get(k, "") for k in _FIELDS}
        )


def get_entries(limit: int = 10) -> list:
    _ensure()
    with open(_JOURNAL, newline="") as f:
        rows = list(csv.DictReader(f))
    return list(reversed(rows[-limit:]))


def get_stats() -> dict:
    _ensure()
    with open(_JOURNAL, newline="") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    if not total:
        return {"total_trades": 0, "win_rate": 0, "avg_grade": "—", "total_pnl": 0.0}

    wins     = sum(1 for r in rows if r.get("pnl") and float(r["pnl"]) > 0)
    pnl_vals = [float(r["pnl"]) for r in rows if r.get("pnl")]

    _gmap  = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
    gvals  = [_gmap[r["discipline_grade"]] for r in rows
               if r.get("discipline_grade") in _gmap]
    avg_grade = (["F", "D", "C", "B", "A"][round(sum(gvals) / len(gvals))]
                 if gvals else "—")

    return {
        "total_trades": total,
        "win_rate":     round(wins / total * 100, 1),
        "avg_grade":    avg_grade,
        "total_pnl":    round(sum(pnl_vals), 2),
    }
