#!/usr/bin/env python3
"""
utils/dataos_logger.py — Append-only activity log.
Writes Obsidian-compatible markdown to logs/YYYY-MM-DD.md.
Never raises — failures are silently swallowed so callers never crash.
"""
import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"


def _today_path() -> Path:
    return LOG_DIR / f"{datetime.date.today().isoformat()}.md"


def _init_file(path: Path) -> None:
    today = datetime.date.today()
    path.write_text(
        f"---\n"
        f"date: {today.isoformat()}\n"
        f"tags: [dataos, activity-log]\n"
        f"---\n\n"
        f"# DataOS — {today.strftime('%A, %B %-d, %Y')}\n"
    )


def log(emoji: str, title: str, body: str = "") -> None:
    """Append a timestamped markdown entry to today's log file."""
    try:
        LOG_DIR.mkdir(exist_ok=True)
        path = _today_path()
        if not path.exists():
            _init_file(path)

        ts = datetime.datetime.now().strftime("%-I:%M %p")
        lines = [f"\n## {emoji} {ts} — {title}"]
        if body:
            lines.append(body.rstrip())
        lines.append("\n---")

        with open(path, "a") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass
