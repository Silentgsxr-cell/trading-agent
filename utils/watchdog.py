#!/usr/bin/env python3
"""
utils/watchdog.py — Security and integrity watchdog for ClawOps.

Runs as a background process alongside runner.py.
Checks every 60 seconds:

  1  API KEY EXPOSURE SCAN
       Loads live secret values from .env and greps all source, docs,
       state, and data files.  CRITICAL Discord alert on any hit.

  2  SESSION STATE INTEGRITY
       Reads state/session.json and validates all fields against config
       thresholds.  WARNING Discord alert with exact field + value.

  3  FILE INTEGRITY CHECK
       Confirms critical files exist and are non-empty.  On missing file:
       CRITICAL alert + auto-halts runner via state_manager.

  4  UNAUTHORIZED WRITE DETECTION
       Tracks mtime + size of config/risk_config.py and
       config/strategy_config.py at startup.  CRITICAL alert if either
       changes during an active session.

  5  RUNNER HEARTBEAT CHECK
       During market hours (9:30–16:00 ET, weekdays), if lastHeartbeat
       in session.json is older than 3 minutes: WARNING alert "Runner
       heartbeat stale — possible crash".

  6  .ENV FILE CHECK
       Confirms .env exists and is NOT tracked by git.
       If tracked: CRITICAL alert + auto-runs `git rm --cached .env`.

Alert deduplication:
  If the same alert key fires 3 consecutive cycles without resolving,
  further repeats are suppressed and replaced with one "persistent issue"
  summary per cycle.

Logging:
  All events written to logs/watchdog.log with AZ timestamps.
  Log rotated to watchdog.log.1 when it exceeds 10 MB.

Usage:
  python3 utils/watchdog.py        # foreground
  Ctrl-C / SIGTERM for clean shutdown.
"""

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, time as dtime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import requests
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from config import risk_config as cfg

try:
    from utils.agent_brain import AgentBrain as _AgentBrain
    _brain = _AgentBrain("WATCHDOG", "#f2b84b")
except Exception:
    _brain = None

_ET = ZoneInfo("America/New_York")
_AZ = ZoneInfo("America/Phoenix")

WEBHOOK_URL    = os.getenv("DISCORD_WATCHDOG_WEBHOOK", "")
LOG_FILE       = PROJECT_ROOT / "logs" / "watchdog.log"
LOG_MAX_BYTES  = 10 * 1024 * 1024   # 10 MB
CHECK_INTERVAL = 60                  # seconds
HB_STALE_SECS  = 180                 # 3 minutes
_MARKET_OPEN   = dtime(9, 30)
_MARKET_CLOSE  = dtime(16, 0)

# ── Secret variable names to watch for ───────────────────────────────────────
_SECRET_VARS = [
    "DISCORD_WEBHOOK_URL",
    "DISCORD_BOT_TOKEN",
    "WEBULL_APP_KEY",
    "WEBULL_APP_SECRET",
    "WEBULL_APP_SECRET_KEY",
    "WEBULL_DEVICE_ID",
    "WEBULL_TRADE_TOKEN",
]

# Files exempt from the exposure scan (expected to hold/reference secrets)
_SCAN_EXEMPT = {
    PROJECT_ROOT / ".env",
    PROJECT_ROOT / ".env.example",
    Path(__file__).resolve(),   # watchdog.py itself references var names
}

# Source trees to scan
_SCAN_DIRS = [
    PROJECT_ROOT / "dashboard",
    PROJECT_ROOT / "utils",
    PROJECT_ROOT / "agents",
]
_SCAN_DOCS = PROJECT_ROOT / "docs"

# State/data flat files to scan
_SCAN_DATA = [
    PROJECT_ROOT / "state" / "session.json",
    PROJECT_ROOT / "state" / "decisions.jsonl",
    PROJECT_ROOT / "data" / "journal.csv",
]

# Files that must exist and be non-empty
_CRITICAL_FILES: List[Path] = [
    PROJECT_ROOT / "config" / "risk_config.py",
    PROJECT_ROOT / "config" / "strategy_config.py",
    PROJECT_ROOT / "agents" / "risk_engine.py",
    PROJECT_ROOT / "agents" / "signaos.py",
    PROJECT_ROOT / "state" / "session.json",
]

# Files whose mtime + size are tracked for unauthorized-write detection
_WATCHED_CONFIGS: List[Path] = [
    PROJECT_ROOT / "config" / "risk_config.py",
    PROJECT_ROOT / "config" / "strategy_config.py",
]

# JSON files that must parse cleanly
_JSON_FILES: List[Path] = [
    PROJECT_ROOT / "state" / "session.json",
    PROJECT_ROOT / "data" / "finance.json",
]

# Embed colors
_COLOR = {"CRITICAL": 0xE53935, "WARNING": 0xF0B429, "CLEAN": 0x00C087, "INFO": 0x607D8B}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_et() -> datetime:
    return datetime.now(_ET)


def _is_market_hours(now: datetime) -> bool:
    if now.weekday() >= 5:
        return False
    t = now.time().replace(tzinfo=None)
    return _MARKET_OPEN <= t < _MARKET_CLOSE


def _file_stat(path: Path) -> Optional[Tuple[float, int]]:
    """Returns (mtime, size) or None if file missing."""
    try:
        s = path.stat()
        return (s.st_mtime, s.st_size)
    except FileNotFoundError:
        return None


# ── Logging with rotation ─────────────────────────────────────────────────────

def _log(level: str, message: str, detail: str = "") -> None:
    LOG_FILE.parent.mkdir(exist_ok=True)

    # Rotate if over 10 MB
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > LOG_MAX_BYTES:
        rotated = LOG_FILE.with_suffix(".log.1")
        shutil.move(str(LOG_FILE), str(rotated))

    ts = datetime.now(_AZ).strftime("%Y-%m-%d %H:%M:%S AZ")
    lines = [f"[{ts}] [{level}] {message}"]
    if detail:
        for line in detail.splitlines():
            lines.append(f"          {line}")
    entry = "\n".join(lines)
    print(entry)
    with open(LOG_FILE, "a") as f:
        f.write(entry + "\n")


# ── Discord ───────────────────────────────────────────────────────────────────

def _alert(level: str, title: str, body: str, fields: Optional[List[dict]] = None) -> None:
    """Fire-and-forget Discord embed. Never raises."""
    if not WEBHOOK_URL:
        return
    icon = "🚨" if level == "CRITICAL" else ("⚠️" if level == "WARNING" else "ℹ️")
    embed: dict = {
        "title":       f"{icon} Watchdog {level} — {title}",
        "description": body,
        "color":       _COLOR.get(level, _COLOR["WARNING"]),
        "footer":      {"text": f"ClawOps · Watchdog · {datetime.now(_AZ).strftime('%-I:%M %p AZ')}"},
    }
    if fields:
        embed["fields"] = fields
    try:
        r = requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=8)
        if r.status_code not in (200, 204):
            _log("ERROR", f"Discord POST failed ({r.status_code})", r.text[:120])
    except Exception as exc:
        _log("ERROR", f"Discord exception: {exc}")


# ── Alert deduplication ───────────────────────────────────────────────────────

class _AlertTracker:
    """
    Tracks consecutive fires per alert key.
    First 2 fires → send normally.
    3rd+ fires without resolution → suppress individual alerts,
    send one "persistent issue" summary per cycle instead.
    """
    SUPPRESS_AFTER = 3

    def __init__(self) -> None:
        self._counts: Dict[str, int] = {}
        self._suppressed: Dict[str, bool] = {}

    def fire(self, key: str, level: str, title: str, body: str,
             fields: Optional[List[dict]] = None) -> None:
        self._counts[key] = self._counts.get(key, 0) + 1
        count = self._counts[key]

        if count < self.SUPPRESS_AFTER:
            _alert(level, title, body, fields)
        elif count == self.SUPPRESS_AFTER:
            _alert(
                "WARNING",
                f"Persistent Issue — {title}",
                f"This alert has fired {count} consecutive cycles without resolving. "
                f"Further repeats suppressed until the condition clears.\n\n"
                f"**Original alert:** {body}",
            )
            self._suppressed[key] = True
        # count > SUPPRESS_AFTER: silent (already notified it's persistent)

    def resolve(self, key: str) -> None:
        """Call when a condition clears so the counter resets."""
        prev = self._counts.pop(key, 0)
        if prev >= self.SUPPRESS_AFTER:
            _alert("INFO", f"Resolved — {key}", "The condition has cleared.")
        self._suppressed.pop(key, None)

    def is_suppressed(self, key: str) -> bool:
        return self._suppressed.get(key, False)


# ── Check 1 — API key exposure scan ──────────────────────────────────────────

def _load_secrets() -> Dict[str, str]:
    placeholders = {"your_webhook_url_here", "your_bot_token_here", ""}
    out = {}
    for var in _SECRET_VARS:
        val = os.getenv(var, "")
        if val and val not in placeholders and len(val) > 8:
            out[var] = val
    return out


def _scan_targets() -> List[Path]:
    files: List[Path] = []
    for d in _SCAN_DIRS:
        if d.exists():
            files.extend(d.rglob("*.py"))
    if _SCAN_DOCS.exists():
        files.extend(_SCAN_DOCS.rglob("*.md"))
    for f in _SCAN_DATA:
        if f.exists():
            files.append(f)
    return [f for f in files if f.resolve() not in _SCAN_EXEMPT]


def check_api_exposure(secrets: Dict[str, str]) -> List[str]:
    """Returns violation strings — never includes actual secret values."""
    if not secrets:
        return []
    violations = []
    for path in _scan_targets():
        try:
            content = path.read_text(errors="replace")
        except Exception:
            continue
        for var_name, val in secrets.items():
            if val in content:
                violations.append(f"`{path.relative_to(PROJECT_ROOT)}`  contains value of **{var_name}**")
    return violations


# ── Check 2 — Session state integrity ────────────────────────────────────────

def check_session_integrity() -> List[str]:
    """Returns violation strings. Empty = clean."""
    session_file = PROJECT_ROOT / "state" / "session.json"
    if not session_file.exists():
        return []
    try:
        s = json.loads(session_file.read_text())
    except Exception as exc:
        return [f"session.json unreadable/corrupt: {exc}"]

    violations = []

    balance = s.get("currentBalance")
    if balance is not None and balance < 0:
        violations.append(f"**currentBalance** = ${balance:.2f} (below $0)")

    trades = s.get("tradesToday", 0)
    if trades > cfg.MAX_TRADES_PER_DAY:
        violations.append(
            f"**tradesToday** = {trades} exceeds MAX_TRADES_PER_DAY={cfg.MAX_TRADES_PER_DAY}"
        )

    daily_pnl  = s.get("dailyPnl", 0.0)
    start_bal  = s.get("startingBalance", cfg.STARTING_BALANCE)
    loss_limit = start_bal * cfg.DAILY_MAX_LOSS_PCT
    halted     = s.get("halted", False)
    if daily_pnl < 0 and abs(daily_pnl) > loss_limit and not halted:
        violations.append(
            f"**dailyPnl** = ${daily_pnl:.2f} exceeds loss limit "
            f"(-${loss_limit:.2f}) but **halted=false** — circuit breaker not set"
        )

    consec = s.get("consecutiveLosses", 0)
    if consec > cfg.CONSECUTIVE_LOSS_COOLDOWN:
        violations.append(
            f"**consecutiveLosses** = {consec} exceeds CONSECUTIVE_LOSS_COOLDOWN="
            f"{cfg.CONSECUTIVE_LOSS_COOLDOWN} — verify no new entries were approved"
        )

    return violations


# ── Check 3 — File integrity ──────────────────────────────────────────────────

def check_file_integrity() -> List[str]:
    """Returns violation strings. Auto-halts runner on any missing critical file."""
    violations = []
    halted_runner = False

    for path in _CRITICAL_FILES:
        if not path.exists():
            msg = f"MISSING: `{path.relative_to(PROJECT_ROOT)}`"
            violations.append(msg)
            if not halted_runner:
                try:
                    import utils.state_manager as sm
                    sm.halt_session(f"watchdog: critical file missing — {path.name}")
                    _log("CRITICAL", f"Auto-halted runner because {path.name} is missing")
                    halted_runner = True
                except Exception as exc:
                    _log("ERROR", f"Failed to auto-halt runner: {exc}")
        elif path.stat().st_size == 0:
            violations.append(f"EMPTY: `{path.relative_to(PROJECT_ROOT)}`")

    for path in _JSON_FILES:
        if path.exists():
            try:
                json.loads(path.read_text())
            except Exception as exc:
                violations.append(f"CORRUPT JSON: `{path.relative_to(PROJECT_ROOT)}` — {exc}")

    return violations


# ── Check 4 — Unauthorized write detection ────────────────────────────────────

def check_config_writes(baseline: Dict[str, Tuple[float, int]]) -> List[str]:
    """
    Compare current mtime + size of watched config files against baseline.
    Returns violation strings.
    """
    violations = []
    for path in _WATCHED_CONFIGS:
        key = str(path)
        current = _file_stat(path)
        if current is None:
            violations.append(f"`{path.relative_to(PROJECT_ROOT)}` was deleted")
            continue
        orig = baseline.get(key)
        if orig is None:
            continue
        orig_mtime, orig_size = orig
        cur_mtime, cur_size   = current
        if cur_mtime != orig_mtime or cur_size != orig_size:
            ts = datetime.fromtimestamp(cur_mtime, _AZ).strftime("%Y-%m-%d %H:%M:%S AZ")
            delta_bytes = cur_size - orig_size
            sign = "+" if delta_bytes >= 0 else ""
            violations.append(
                f"`{path.relative_to(PROJECT_ROOT)}` modified at {ts} "
                f"(size: {orig_size} → {cur_size} bytes, {sign}{delta_bytes})"
            )
    return violations


# ── Check 5 — Runner heartbeat ────────────────────────────────────────────────

def check_runner_heartbeat() -> List[str]:
    """
    During market hours, warn if lastHeartbeat in session.json is stale.
    """
    now = _now_et()
    if not _is_market_hours(now):
        return []

    session_file = PROJECT_ROOT / "state" / "session.json"
    if not session_file.exists():
        return []

    try:
        s = json.loads(session_file.read_text())
    except Exception:
        return []

    if not s.get("runnerOnline", False):
        return []

    hb_str = s.get("lastHeartbeat")
    if not hb_str:
        return ["**lastHeartbeat** is null — runner may not have started correctly"]

    try:
        hb_ts = datetime.fromisoformat(hb_str).astimezone(_ET)
        age   = (now - hb_ts).total_seconds()
        if age > HB_STALE_SECS:
            mins = int(age // 60)
            secs = int(age % 60)
            return [f"**lastHeartbeat** is {mins}m {secs}s old — runner may have crashed"]
    except Exception:
        return [f"**lastHeartbeat** could not be parsed: {hb_str!r}"]

    return []


# ── Check 6 — .env git tracking ──────────────────────────────────────────────

def check_env_git_tracking() -> List[str]:
    """
    Confirm .env exists and is NOT tracked by git.
    If tracked, auto-runs `git rm --cached .env` and reports.
    """
    violations = []
    env_path = PROJECT_ROOT / ".env"

    if not env_path.exists():
        violations.append("**.env file is missing** — secrets not loadable")
        return violations

    if env_path.stat().st_size == 0:
        violations.append("**.env file is empty** — no secrets loaded")

    try:
        result = subprocess.run(
            ["git", "ls-files", ".env"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        tracked = result.stdout.strip()
        if tracked:
            violations.append(
                "**.env is tracked by git** — secrets are exposed in git history. "
                "Auto-running `git rm --cached .env`…"
            )
            _log("CRITICAL", ".env is git-tracked — running git rm --cached .env")
            subprocess.run(
                ["git", "rm", "--cached", ".env"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                timeout=10,
            )
            _log("INFO", "git rm --cached .env completed — commit the change to finalize")
    except Exception as exc:
        _log("ERROR", f".env git check failed: {exc}")

    return violations


# ── Check 7 — Dev agent output scanner (called from dev_agent.py also) ────────
# These are re-exported so dev_agent.py can use the same logic before file writes.

_DANGEROUS_CODE = re.compile(
    r"\b(os\.system|subprocess\.(?:run|Popen|call|check_output)|"
    r"eval\s*\(|exec\s*\()\s*\("
)


def scan_dev_agent_output(
    response_str: str,
    file_entries: List[dict],
    original_files: Dict[str, str],
    secrets: Dict[str, str],
) -> List[str]:
    """
    Scan Claude API response for security issues before any file write.
    Returns violation strings (empty = safe).
    """
    violations = []

    # 1. Secret value in response
    for var_name, val in secrets.items():
        if val in response_str:
            violations.append(f"Response contains value of **{var_name}** — key exposure risk")

    for entry in file_entries:
        path    = entry.get("path", "")
        content = entry.get("content", "")

        # 2. Directory traversal
        if "../" in path or path.startswith("/"):
            violations.append(f"Path traversal in generated path: `{path}`")

        # 3. File size guard — 500 KB
        size = len(content.encode())
        if size > 500 * 1024:
            violations.append(f"`{path}` is {size // 1024}KB — exceeds 500KB limit")

        # 4. Dangerous patterns injected (not present in original)
        original = original_files.get(path, "")
        new_hits = set(_DANGEROUS_CODE.findall(content))
        old_hits = set(_DANGEROUS_CODE.findall(original))
        injected = new_hits - old_hits
        if injected:
            violations.append(f"Dangerous pattern injected in `{path}`: {injected}")

    return violations


# ── Check 8 — Git history author audit (hourly) ───────────────────────────────

_ALLOWED_COMMIT_PREFIXES = [
    "dev-agent:",
    "Merge dev-agent/",
    "single-writer rule",
    "security watchdog",
    "naming audit",
    "dev agent",
]


def check_git_history() -> List[str]:
    """
    Scan the last 10 commits for unexpected authors or commit messages.
    An 'unexpected' commit is one not from dev-agent or manual work.
    Returns violation strings.
    """
    violations = []
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-10", "--format=%H|%an|%s"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, timeout=15,
        )
        for line in result.stdout.strip().splitlines():
            parts = line.split("|", 2)
            if len(parts) < 3:
                continue
            commit_hash, author, subject = parts
            # Flag commits not from known authors
            known_authors = {"silent", "silentgsxr", "dev-agent", "Claude Sonnet 4.6"}
            if not any(k in author.lower() for k in known_authors):
                violations.append(
                    f"Unexpected commit author: **{author}** — `{commit_hash[:8]}` {subject[:60]}"
                )
    except Exception as exc:
        _log("ERROR", f"Git history check failed: {exc}")
    return violations


# ── Main watchdog class ───────────────────────────────────────────────────────

class Watchdog:
    def __init__(self) -> None:
        self._running      = True
        self._cycle        = 0
        self._tracker      = _AlertTracker()
        self._secrets      = _load_secrets()
        self._last_git_check = 0   # epoch seconds — run hourly

        # Capture config file baseline (mtime + size) at startup
        self._config_baseline: Dict[str, Tuple[float, int]] = {}
        for path in _WATCHED_CONFIGS:
            stat = _file_stat(path)
            if stat:
                self._config_baseline[str(path)] = stat

        LOG_FILE.parent.mkdir(exist_ok=True)
        _log("INFO", f"Watchdog started — monitoring {len(self._secrets)} secret(s)")
        _log("INFO", f"Config baseline: { {p.name: v for p, v in zip(_WATCHED_CONFIGS, self._config_baseline.values())} }")

        signal.signal(signal.SIGINT,  self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, sig, frame) -> None:
        self._running = False
        _log("INFO", "Watchdog shutting down cleanly (SIGINT/SIGTERM)")

    def run(self) -> None:
        while self._running:
            self._cycle += 1
            try:
                if _brain:
                    _brain.start_task("Running 7 security checks", queue_len=7)
                self._run_checks()
            except Exception as exc:
                _log("ERROR", f"Unexpected error in check cycle: {exc}")
                if _brain:
                    _brain.error(f"Check cycle crashed: {exc}")
            for _ in range(CHECK_INTERVAL):
                if not self._running:
                    break
                time.sleep(1)
        _log("INFO", "Watchdog stopped.")

    # ------------------------------------------------------------------

    def _handle(
        self,
        key: str,
        violations: List[str],
        level: str,
        title: str,
        body_prefix: str,
    ) -> None:
        if violations:
            detail_str = "\n".join(f"  • {v}" for v in violations)
            _log(level, f"{key.upper()}: {title}", detail_str)
            fields = [
                {"name": f"#{i+1}", "value": v, "inline": False}
                for i, v in enumerate(violations[:5])
            ]
            self._tracker.fire(key, level, title, f"{body_prefix}\n{detail_str}", fields)
        else:
            self._tracker.resolve(key)

    def _run_checks(self) -> None:
        ts = datetime.now(_AZ).strftime("%H:%M:%S AZ")
        issues = 0

        # 1 — API key exposure
        exp = check_api_exposure(self._secrets)
        if exp:
            issues += 1
        self._handle(
            "key_exposure", exp, "CRITICAL",
            "API Key Exposure",
            "A live secret value was found in a source or data file. "
            "Rotate the affected key immediately.",
        )
        if not exp:
            _log("CLEAN", f"[{self._cycle}] [{ts}] Check 1 PASS — no key exposure")

        # 2 — Session integrity
        sess = check_session_integrity()
        if sess:
            issues += 1
        self._handle(
            "session_integrity", sess, "WARNING",
            "Session Integrity Violation",
            "session.json violates a risk invariant.",
        )
        if not sess:
            _log("CLEAN", f"[{self._cycle}] [{ts}] Check 2 PASS — session valid")

        # 3 — File integrity
        files = check_file_integrity()
        if files:
            issues += 1
        level3 = "CRITICAL" if any("MISSING" in v or "CORRUPT" in v for v in files) else "WARNING"
        self._handle(
            "file_integrity", files, level3,
            "File Integrity Issue",
            "A critical file is missing, empty, or corrupt. Runner may have been auto-halted.",
        )
        if not files:
            _log("CLEAN", f"[{self._cycle}] [{ts}] Check 3 PASS — all files intact")

        # 4 — Unauthorized config writes
        writes = check_config_writes(self._config_baseline)
        if writes:
            issues += 1
            if _brain:
                try:
                    _brain.suggest(
                        title="🚨 Config modified during active session",
                        reasoning=(
                            "A risk configuration file changed while the runner is active. "
                            f"Details: {writes[0][:200]}"
                        ),
                        category="Security",
                        priority=10,
                        flags=["critical", "time_sensitive", "locked_file"],
                        affected_files=["config/risk_config.py", "config/strategy_config.py"],
                    )
                except Exception:
                    pass
        self._handle(
            "config_write", writes, "CRITICAL",
            "Config File Modified During Session",
            "A risk configuration file was changed while the runner is active. "
            "No agent should modify config at runtime.",
        )
        if not writes:
            _log("CLEAN", f"[{self._cycle}] [{ts}] Check 4 PASS — config files unchanged")

        # 5 — Runner heartbeat
        hb = check_runner_heartbeat()
        if hb:
            issues += 1
        self._handle(
            "heartbeat", hb, "WARNING",
            "Runner Heartbeat Stale — Possible Crash",
            "The runner heartbeat has not been updated recently during market hours.",
        )
        if not hb:
            _log("CLEAN", f"[{self._cycle}] [{ts}] Check 5 PASS — heartbeat fresh")

        # 6 — .env git tracking
        env_issues = check_env_git_tracking()
        if env_issues:
            issues += 1
        self._handle(
            "env_git", env_issues, "CRITICAL",
            ".env File Security Issue",
            ".env file is missing, empty, or tracked by git.",
        )
        if not env_issues:
            _log("CLEAN", f"[{self._cycle}] [{ts}] Check 6 PASS — .env secure")

        # 6b — API key age check (suggest rotation if .env older than 30 days)
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists() and _brain:
            try:
                age_days = (time.time() - env_path.stat().st_mtime) / 86400
                if age_days > 30:
                    _brain.suggest(
                        title="⚠️ API key rotation recommended",
                        reasoning=(
                            f".env file has not been updated in {int(age_days)} days. "
                            "Rotate ANTHROPIC_API_KEY and any other secrets as a security practice."
                        ),
                        category="Security",
                        priority=9,
                        flags=["time_sensitive"],
                    )
            except Exception:
                pass

        # 7 — Git history author audit (hourly)
        now_epoch = time.time()
        if now_epoch - self._last_git_check >= 3600:
            self._last_git_check = now_epoch
            git_issues = check_git_history()
            if git_issues:
                issues += 1
            self._handle(
                "git_history", git_issues, "CRITICAL",
                "Unexpected Commit Author Detected",
                "A commit was found from an unrecognized author. "
                "Review git log immediately.",
            )
            if not git_issues:
                _log("CLEAN", f"[{self._cycle}] [{ts}] Check 7 PASS — git history clean")

        if issues == 0:
            _log("CLEAN", f"[{self._cycle}] [{ts}] All checks passed — system healthy")

        if _brain:
            summary = "All 7 checks passed" if issues == 0 else f"{issues} issue(s) flagged this cycle"
            _brain.finish_task(f"[{ts}] {summary}", next_scheduled_action=f"Next cycle in {CHECK_INTERVAL}s")


if __name__ == "__main__":
    Watchdog().run()
