"""
journal_manager.py — Read and write trades to data/journal.csv.

The CSV is the single source of truth for Silent's trade history.
Every trade — paper or live — should be logged here immediately after exit.
"""

import csv
import os
from datetime import datetime

# Absolute path so the file is always in data/ regardless of where Flask is started from
JOURNAL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'journal.csv',
)

# Column order in the CSV — do not reorder without migrating existing data
COLUMNS = [
    'date', 'ticker', 'strategy', 'entry', 'stop', 'target',
    'exit', 'pnl', 'trade_type', 'was_planned', 'chased',
    'followed_stop', 'lesson', 'discipline_grade',
]

# Mapping grade letters ↔ numbers for averaging
GRADE_TO_NUM = {'A': 4, 'B': 3, 'C': 2, 'D': 1, 'F': 0}
NUM_TO_GRADE = {4: 'A', 3: 'B', 2: 'C', 1: 'D', 0: 'F'}


def _ensure_journal_exists() -> None:
    """Create the CSV with headers if it does not already exist."""
    os.makedirs(os.path.dirname(JOURNAL_PATH), exist_ok=True)
    if not os.path.exists(JOURNAL_PATH):
        with open(JOURNAL_PATH, 'w', newline='') as f:
            csv.DictWriter(f, fieldnames=COLUMNS).writeheader()


def save_entry(entry: dict) -> bool:
    """Append one trade to the journal. Missing fields default to empty string."""
    _ensure_journal_exists()
    row = {col: str(entry.get(col, '')).strip() for col in COLUMNS}
    if not row['date']:
        row['date'] = datetime.now().strftime('%Y-%m-%d')

    with open(JOURNAL_PATH, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writerow(row)
    return True


def get_entries(n: int = 10) -> list[dict]:
    """Return the last n entries, most-recent first."""
    _ensure_journal_exists()
    try:
        with open(JOURNAL_PATH, 'r', newline='') as f:
            rows = list(csv.DictReader(f))
        return list(reversed(rows[-n:]))
    except Exception:
        return []


def get_stats() -> dict:
    """Compute summary statistics across all logged trades."""
    _ensure_journal_exists()
    try:
        with open(JOURNAL_PATH, 'r', newline='') as f:
            rows = list(csv.DictReader(f))
    except Exception:
        rows = []

    total = len(rows)

    if total == 0:
        return {
            'total_trades':    0,
            'win_rate':        0.0,
            'avg_grade':       'N/A',
            'total_pnl':       0.0,
            'winning_trades':  0,
            'losing_trades':   0,
        }

    # Win rate — only rows that have a numeric P/L value count
    wins = 0
    losses = 0
    total_pnl = 0.0
    for row in rows:
        raw = row.get('pnl', '').strip()
        if raw:
            try:
                pnl = float(raw)
                total_pnl += pnl
                if pnl > 0:
                    wins += 1
                elif pnl < 0:
                    losses += 1
            except ValueError:
                pass

    graded = [row for row in rows if row.get('discipline_grade', '').strip().upper() in GRADE_TO_NUM]
    if graded:
        avg_num  = sum(GRADE_TO_NUM[r['discipline_grade'].strip().upper()] for r in graded) / len(graded)
        avg_grade = NUM_TO_GRADE[max(0, min(4, round(avg_num)))]
    else:
        avg_grade = 'N/A'

    pnl_total_trades = wins + losses
    win_rate = round((wins / pnl_total_trades) * 100, 1) if pnl_total_trades > 0 else 0.0

    return {
        'total_trades':   total,
        'win_rate':       win_rate,
        'avg_grade':      avg_grade,
        'total_pnl':      round(total_pnl, 2),
        'winning_trades': wins,
        'losing_trades':  losses,
    }
