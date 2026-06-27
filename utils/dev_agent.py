#!/usr/bin/env python3
"""
utils/dev_agent.py — Autonomous dev agent for ClawOps.

Picks up open tickets from data/tickets.json, calls the Claude API to
generate code changes, validates and applies them, runs tests, commits,
and merges to master — all autonomously.

6 safety gates run before every ticket.  Any failure aborts the run
without touching a single file.

Ticket execution (11 steps):
  branch → context gather → Claude API → validate → write → smoke test
  → Next.js build → commit → push → merge → ticket completion

Security built-in (from Step 7 Check 1):
  - API response scanned for .env values before any write
  - Path traversal (../) blocked in all generated paths
  - Dangerous imports (subprocess, os.system, eval, exec) flagged if new
  - 500 KB per-file size guard

Rate limiting: max 3 tickets per run, 30s between tickets.

Usage:
  python3 utils/dev_agent.py            # process up to 3 open tickets
  python3 utils/dev_agent.py --dry-run  # safety checks + context only, no writes
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import requests
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

_ET = ZoneInfo("America/New_York")
_AZ = ZoneInfo("America/Phoenix")

WEBHOOK_URL     = os.getenv("DISCORD_DEV_AGENT_WEBHOOK", "")
ANTHROPIC_KEY   = os.getenv("ANTHROPIC_API_KEY", "")

try:
    from utils.agent_brain import AgentBrain as _AgentBrain
    _brain = _AgentBrain("DEV_AGENT", "#5c6bc0")
except Exception:
    _brain = None
TICKETS_FILE    = PROJECT_ROOT / "data" / "tickets.json"
AUDIT_LOG       = PROJECT_ROOT / "logs" / "dev_agent_audit.log"
MAX_TICKETS     = 3
TICKET_DELAY    = 30   # seconds between tickets
MAX_FILE_BYTES  = 500 * 1024   # 500 KB
CLAUDE_MODEL    = "claude-sonnet-4-6"
CLAUDE_MAXTOK   = 4000

# Paths the agent can NEVER write to, regardless of ticket config
GLOBAL_BLOCKED = [
    "agents/",
    "config/",
    "tests/",
    ".env",
    "utils/watchdog.py",
    "utils/state_manager.py",
    "utils/journal_writer.py",
    "utils/event_log.py",
]

# Dangerous patterns to reject in generated code
DANGEROUS_IMPORTS = re.compile(
    r"\b(os\.system|subprocess\.(?:run|Popen|call|check_output)|"
    r"eval\s*\(|exec\s*\()\s*\("
)


# ── Logging ───────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now(_AZ).strftime("%Y-%m-%d %H:%M:%S AZ")


def _log(level: str, msg: str) -> None:
    print(f"[dev-agent] [{level}] {msg}")


def _audit(ticket_id: str, status: str, files_changed: int,
           commit_hash: str, duration: float) -> None:
    AUDIT_LOG.parent.mkdir(exist_ok=True)
    line = (
        f"{_ts()} | {ticket_id} | {status} | "
        f"files:{files_changed} | commit:{commit_hash or 'none'} | "
        f"duration:{duration:.1f}s\n"
    )
    with open(AUDIT_LOG, "a") as f:
        f.write(line)


# ── Discord ───────────────────────────────────────────────────────────────────

def _discord(level: str, title: str, body: str,
             fields: Optional[List[dict]] = None) -> None:
    if not WEBHOOK_URL:
        return
    colors = {"CRITICAL": 0xE53935, "WARNING": 0xF0B429,
              "SUCCESS": 0x00C087, "INFO": 0x607D8B}
    icon = {"CRITICAL": "🚨", "WARNING": "⚠️",
            "SUCCESS": "✅", "INFO": "ℹ️"}.get(level, "•")
    embed: dict = {
        "title":       f"{icon} Dev Agent — {title}",
        "description": body,
        "color":       colors.get(level, colors["INFO"]),
        "footer":      {"text": f"ClawOps · DevAgent · {_ts()}"},
    }
    if fields:
        embed["fields"] = fields
    try:
        r = requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=8)
        if r.status_code not in (200, 204):
            _log("ERROR", f"Discord failed {r.status_code}")
    except Exception as exc:
        _log("ERROR", f"Discord exception: {exc}")


# ── Ticket DB ─────────────────────────────────────────────────────────────────

def _load_tickets() -> dict:
    if not TICKETS_FILE.exists():
        return {"paused": False, "tickets": []}
    return json.loads(TICKETS_FILE.read_text())


def _save_tickets(db: dict) -> None:
    TICKETS_FILE.write_text(json.dumps(db, indent=2, default=str))


def _update_ticket(db: dict, ticket_id: str, diff: dict) -> None:
    for t in db["tickets"]:
        if t["id"] == ticket_id:
            t.update(diff)
    _save_tickets(db)


def _append_log(db: dict, ticket_id: str, entry: str) -> None:
    for t in db["tickets"]:
        if t["id"] == ticket_id:
            if "log" not in t or t["log"] is None:
                t["log"] = []
            t["log"].append(f"[{_ts()}] {entry}")
    _save_tickets(db)


# ── Git helpers ───────────────────────────────────────────────────────────────

def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + list(args),
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=check,
    )


def _git_out(*args: str) -> str:
    return _git(*args).stdout.strip()


# ── Safety checks ─────────────────────────────────────────────────────────────

def _load_secrets() -> Dict[str, str]:
    env_vars = ["DISCORD_WEBHOOK_URL", "DISCORD_BOT_TOKEN",
                "WEBULL_APP_KEY", "WEBULL_APP_SECRET",
                "WEBULL_DEVICE_ID", "WEBULL_TRADE_TOKEN",
                "ANTHROPIC_API_KEY"]
    placeholders = {"your_webhook_url_here", "your_bot_token_here", ""}
    out = {}
    for v in env_vars:
        val = os.getenv(v, "")
        if val and val not in placeholders and len(val) > 8:
            out[v] = val
    return out


def safety_checks(ticket: dict) -> Tuple[bool, str]:
    """
    Run all 6 safety gates.  Returns (ok, reason).
    Reason is empty string on success.
    """

    # 1. Market hours check — only run before 6 AM ET or after 4:30 PM ET
    now_et = datetime.now(_ET)
    et_time = now_et.time()
    from datetime import time as dtime
    market_block_start = dtime(6, 0)
    market_block_end   = dtime(16, 30)
    if market_block_start <= et_time <= market_block_end and now_et.weekday() < 5:
        return False, f"BLOCKED — market hours active ({et_time.strftime('%H:%M')} ET)"

    # 2. Runner active check
    session_file = PROJECT_ROOT / "state" / "session.json"
    if session_file.exists():
        try:
            s = json.loads(session_file.read_text())
            if not s.get("halted", True):
                hb_str = s.get("lastHeartbeat")
                if hb_str:
                    hb = datetime.fromisoformat(hb_str).astimezone(_ET)
                    age = (now_et - hb).total_seconds()
                    if age < 180:
                        return False, f"BLOCKED — runner.py appears active (heartbeat {int(age)}s ago)"
        except Exception:
            pass

    # 3. Watchdog running check
    try:
        result = subprocess.run(
            ["pgrep", "-f", "utils/watchdog.py"],
            capture_output=True, text=True
        )
        if not result.stdout.strip():
            _discord("WARNING", "Watchdog Not Running",
                     "Dev agent aborted — watchdog.py is not running. "
                     "Start it before running the dev agent.")
            return False, "BLOCKED — watchdog.py is not running"
    except Exception:
        pass   # pgrep unavailable — skip this check on non-Unix

    # 4. Clean git working tree
    status = _git_out("status", "--porcelain")
    if status:
        return False, f"BLOCKED — dirty working tree ({status[:80]}). Commit or stash first."

    # 5. Ticket allowed_paths vs global blocked_paths overlap
    allowed = ticket.get("allowed_paths", [])
    blocked = ticket.get("blocked_paths", []) + GLOBAL_BLOCKED
    for ap in allowed:
        for bp in blocked:
            if ap.startswith(bp) or bp.startswith(ap):
                return False, f"BLOCKED — allowed_path '{ap}' overlaps blocked_path '{bp}'"

    # 6. .env git tracking
    tracked = _git_out("ls-files", ".env")
    if tracked:
        _discord("CRITICAL", ".env Is Git-Tracked",
                 "Dev agent aborted — .env is tracked by git. "
                 "Secrets may be exposed. Run: `git rm --cached .env`")
        return False, "BLOCKED — .env is tracked by git"

    return True, ""


# ── Security: response scanner ────────────────────────────────────────────────

def scan_response(response_json: dict, original_files: Dict[str, str],
                  secrets: Dict[str, str]) -> Tuple[bool, str]:
    """
    Scan Claude API response for security violations before any file write.
    Returns (safe, reason).  reason empty = safe.
    """
    raw = json.dumps(response_json)

    # 1. Secret value exposure
    for var_name, val in secrets.items():
        if val in raw:
            return False, f"Response contains value of {var_name} — aborting write"

    for file_entry in response_json.get("files", []):
        path = file_entry.get("path", "")
        content = file_entry.get("content", "")

        # 2. Directory traversal
        if "../" in path or path.startswith("/"):
            return False, f"Path traversal detected in response path: '{path}'"

        # 3. File size guard
        if len(content.encode()) > MAX_FILE_BYTES:
            return False, f"File '{path}' exceeds 500 KB limit ({len(content.encode())} bytes)"

        # 4. Dangerous imports injected into new code
        original = original_files.get(path, "")
        new_matches = set(DANGEROUS_IMPORTS.findall(content))
        old_matches = set(DANGEROUS_IMPORTS.findall(original))
        injected = new_matches - old_matches
        if injected:
            return False, f"Dangerous pattern injected in '{path}': {injected}"

    return True, ""


# ── Path validation ───────────────────────────────────────────────────────────

def validate_paths(file_entries: List[dict], ticket: dict) -> Tuple[bool, str]:
    allowed  = ticket.get("allowed_paths", [])
    blocked  = ticket.get("blocked_paths", []) + GLOBAL_BLOCKED

    for entry in file_entries:
        path = entry.get("path", "")
        norm = path.replace("\\", "/")

        # Must be within at least one allowed path
        if not any(norm.startswith(a.rstrip("/")) for a in allowed):
            return False, f"Path '{path}' not within allowed_paths {allowed}"

        # Must not match any blocked path
        for bp in blocked:
            if norm.startswith(bp.rstrip("/")):
                return False, f"Path '{path}' matches blocked_path '{bp}'"

    return True, ""


# ── Context gathering ─────────────────────────────────────────────────────────

def gather_context(ticket: dict) -> Tuple[Dict[str, str], List[str]]:
    """
    Read files from ticket.allowed_paths. Returns (file_contents, files_read).
    Content truncated to 4000 chars per file to stay within token budget.
    """
    contents: Dict[str, str] = {}
    files_read: List[str] = []

    for rel_path in ticket.get("allowed_paths", []):
        path = PROJECT_ROOT / rel_path
        if path.is_file():
            try:
                text = path.read_text(errors="replace")[:4000]
                contents[rel_path] = text
                files_read.append(rel_path)
            except Exception:
                pass
        elif path.is_dir():
            for f in sorted(path.rglob("*"))[:20]:   # cap at 20 files per dir
                if f.is_file() and f.suffix in (".py", ".ts", ".tsx", ".json", ".css"):
                    try:
                        rel = str(f.relative_to(PROJECT_ROOT))
                        text = f.read_text(errors="replace")[:4000]
                        contents[rel] = text
                        files_read.append(rel)
                    except Exception:
                        pass

    return contents, files_read


# ── Claude API call ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a dev agent building UI features for ClawOps, a trading mission
control dashboard built with Next.js 14 App Router and a Flask backend.

Design system:
- Dark navy background: #0a0e1a
- Card backgrounds: #0d1117 with rgba(255,255,255,0.03) borders
- Accent green: #00e676
- Amber warning: #ffc107
- Red alert: #f44336
- Purple: #9c27b0
- Text primary: #e2e8f0, muted: #64748b
- Font: monospace throughout
- Borders: 1px solid rgba(255,255,255,0.06)

You output ONLY valid code changes. No explanations outside the JSON.
Output format is strictly JSON (no markdown, no code fences):
{
  "files": [
    {
      "path": "relative/path/to/file",
      "action": "modify|create",
      "content": "full file content here"
    }
  ],
  "summary": "one paragraph of what was done and why",
  "files_read": ["list of files that informed the solution"],
  "smoke_test_command": "command to verify"
}

HARD RESTRICTIONS — never output changes to these paths:
- agents/
- config/
- tests/
- .env
- utils/watchdog.py
- utils/state_manager.py
- utils/journal_writer.py
- utils/event_log.py

If asked to modify these paths, return empty files array with summary
explaining why it was blocked.
"""


def call_claude(ticket: dict, file_contents: Dict[str, str]) -> Optional[dict]:
    """
    Call Claude API. Returns parsed JSON dict or None on failure.
    """
    if not ANTHROPIC_KEY:
        _log("ERROR", "ANTHROPIC_API_KEY not set in .env — cannot call Claude API")
        return None

    files_block = "\n\n".join(
        f"=== FILE: {path} ===\n{content}"
        for path, content in file_contents.items()
    )

    user_message = f"""
TICKET: {ticket['id']} — {ticket['title']}

DESCRIPTION:
{ticket['description']}

WHAT TO COMPLETE:
{ticket['what_to_complete']}

WHAT DONE LOOKS LIKE:
{ticket['what_done_looks_like']}

RESTRICTIONS:
{json.dumps(ticket.get('restrictions', []), indent=2)}

ALLOWED PATHS:
{json.dumps(ticket.get('allowed_paths', []), indent=2)}

BLOCKED PATHS:
{json.dumps(ticket.get('blocked_paths', []) + GLOBAL_BLOCKED, indent=2)}

CURRENT FILE CONTENTS:
{files_block}

Produce the minimal code changes needed to complete this ticket.
Return ONLY the JSON object — no markdown, no prose, no code fences.
"""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":      CLAUDE_MODEL,
                "max_tokens": CLAUDE_MAXTOK,
                "system":     SYSTEM_PROMPT,
                "messages":   [{"role": "user", "content": user_message}],
            },
            timeout=120,
        )
        if resp.status_code != 200:
            _log("ERROR", f"Claude API error {resp.status_code}: {resp.text[:200]}")
            return None

        raw_content = resp.json()["content"][0]["text"].strip()
        # Strip markdown fences if Claude wraps it anyway
        raw_content = re.sub(r"^```(?:json)?\s*", "", raw_content)
        raw_content = re.sub(r"\s*```$", "", raw_content)
        return json.loads(raw_content)

    except json.JSONDecodeError as exc:
        _log("ERROR", f"Claude response was not valid JSON: {exc}")
        return None
    except Exception as exc:
        _log("ERROR", f"Claude API call failed: {exc}")
        return None


# ── Ticket execution ──────────────────────────────────────────────────────────

def run_ticket(ticket: dict, db: dict, dry_run: bool = False) -> bool:
    """
    Execute one ticket through the full 11-step pipeline.
    Returns True on success, False on any failure.
    """
    tid       = ticket["id"]
    title     = ticket["title"]
    start_ts  = time.time()
    branch    = f"dev-agent/{tid}"
    secrets   = _load_secrets()
    orig_branch = _git_out("rev-parse", "--abbrev-ref", "HEAD")

    def abort(reason: str, discord_level: str = "WARNING") -> bool:
        _log("ABORT", f"{tid}: {reason}")
        _append_log(db, tid, f"ABORT: {reason}")
        _update_ticket(db, tid, {"status": "failed"})
        _discord(discord_level, f"{tid} Failed", reason)
        _audit(tid, "failed", 0, "", time.time() - start_ts)
        # Attempt clean recovery to original branch
        try:
            _git("checkout", orig_branch, check=False)
            _git("branch", "-D", branch, check=False)
        except Exception:
            pass
        return False

    _log("START", f"Processing {tid}: {title}")

    # Post planning suggestion so the change is logged before any write
    if _brain:
        try:
            _brain.suggest(
                title=f"Dev Agent planning: {title}",
                reasoning=(
                    f"Dev Agent is about to execute ticket {tid}. "
                    f"Planned files: {ticket.get('allowed_paths', [])}. "
                    "This entry serves as the pre-execution confirmation log."
                ),
                category="Agents",
                priority=5,
                affected_files=ticket.get("allowed_paths", []),
            )
        except Exception:
            pass

    _update_ticket(db, tid, {
        "status":     "in_progress",
        "started_at": datetime.now(_AZ).isoformat(),
        "git_branch": branch,
    })
    _append_log(db, tid, f"Started — complexity:{ticket.get('complexity')} priority:{ticket.get('priority')}")

    # Step 1: Complexity gate for complex tickets
    if ticket.get("complexity") == "complex" and ticket.get("approval_gate") != "approved":
        _discord(
            "WARNING",
            f"🟣 {tid} Needs Review",
            f"**{title}**\n\nThis ticket is marked `complex` and requires your approval "
            f"before the dev agent starts.\n\nReply `!approve {tid}` to proceed.",
        )
        _update_ticket(db, tid, {"status": "needs_review"})
        _append_log(db, tid, "Complex ticket — set to needs_review, awaiting !approve")
        return False

    if dry_run:
        _log("DRY-RUN", f"{tid}: safety + context check only")
        file_contents, files_read = gather_context(ticket)
        _log("DRY-RUN", f"Context: {len(files_read)} files, {sum(len(v) for v in file_contents.values())} chars")
        _update_ticket(db, tid, {"status": "open", "started_at": None})
        return True

    # Step 2: Branch creation
    try:
        _git("checkout", "-b", branch)
        _append_log(db, tid, f"Branch created: {branch}")
    except subprocess.CalledProcessError as exc:
        return abort(f"Branch creation failed: {exc.stderr[:200]}")

    # Step 3: Context gathering
    file_contents, files_read = gather_context(ticket)
    _update_ticket(db, tid, {"files_read": files_read})
    _append_log(db, tid, f"Context: {len(files_read)} files gathered")

    # Step 4: Claude API call
    _log("API", f"{tid}: calling Claude ({CLAUDE_MODEL})")
    response = call_claude(ticket, file_contents)
    if response is None:
        return abort(f"Claude API call failed — check ANTHROPIC_API_KEY and logs", "CRITICAL")

    file_entries = response.get("files", [])
    agent_summary = response.get("summary", "")
    _append_log(db, tid, f"Claude response: {len(file_entries)} file change(s)")

    # Step 5: Response validation (security scan + path validation)
    safe, reason = scan_response(response, file_contents, secrets)
    if not safe:
        _discord("CRITICAL", f"{tid} Security Scan Failed", reason)
        return abort(f"Security scan failed: {reason}", "CRITICAL")

    ok, reason = validate_paths(file_entries, ticket)
    if not ok:
        _discord("CRITICAL", f"{tid} Path Validation Failed", reason)
        return abort(f"Path validation failed: {reason}", "CRITICAL")

    if not file_entries:
        _append_log(db, tid, "Claude returned 0 file changes — no work to do")
        _git("checkout", orig_branch, check=False)
        _git("branch", "-D", branch, check=False)
        _update_ticket(db, tid, {"status": "done", "agent_summary": agent_summary,
                                  "completed_at": datetime.now(_AZ).isoformat()})
        return True

    # Step 6: File writes
    files_modified = []
    files_created  = []
    for entry in file_entries:
        rel_path = entry["path"]
        action   = entry.get("action", "modify")
        content  = entry["content"]
        dest     = PROJECT_ROOT / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        existed  = dest.exists()
        dest.write_text(content)
        if existed or action == "modify":
            files_modified.append(rel_path)
        else:
            files_created.append(rel_path)
        _append_log(db, tid, f"Wrote: {rel_path} ({len(content)} chars)")

    _update_ticket(db, tid, {
        "files_modified": files_modified,
        "files_created":  files_created,
    })

    # Step 7: Smoke test
    _log("TEST", f"{tid}: running smoke test")
    smoke = subprocess.run(
        [sys.executable, "-m", "tests.smoke_test"],
        cwd=str(PROJECT_ROOT),
        capture_output=True, text=True,
    )
    _append_log(db, tid, f"Smoke test exit={smoke.returncode}")
    if smoke.returncode != 0:
        _discord("CRITICAL", f"{tid} Smoke Test Failed",
                 f"```\n{smoke.stdout[-800:]}\n{smoke.stderr[-400:]}```")
        return abort(f"Smoke test failed (exit {smoke.returncode})")

    # Step 8: Next.js build check (only if .tsx/.ts files changed)
    ts_changed = any(p.endswith((".tsx", ".ts")) for p in files_modified + files_created)
    if ts_changed:
        _log("BUILD", f"{tid}: running Next.js build")
        mc_dir = PROJECT_ROOT / "mission-control"
        build = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(mc_dir),
            capture_output=True, text=True,
            timeout=300,
        )
        _append_log(db, tid, f"Next.js build exit={build.returncode}")
        if build.returncode != 0:
            _discord("WARNING", f"{tid} Next.js Build Failed",
                     f"```\n{build.stderr[-800:]}```")
            return abort(f"Next.js build failed")

    # Step 9: Commit and push
    all_written = files_modified + files_created
    for f in all_written:
        _git("add", f)

    commit_msg = f"dev-agent: {tid} — {title}\n\nCo-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
    try:
        _git("commit", "-m", commit_msg)
        commit_hash = _git_out("rev-parse", "--short", "HEAD")
        _git("push", "origin", branch)
        _append_log(db, tid, f"Committed: {commit_hash}, pushed {branch}")
    except subprocess.CalledProcessError as exc:
        return abort(f"Commit/push failed: {exc.stderr[:200]}")

    # Step 10: Merge to master
    try:
        _git("checkout", orig_branch)
        _git("merge", branch, "--no-ff", "-m", f"Merge dev-agent/{tid}: {title}")
        _git("push", "origin", orig_branch)
        _git("branch", "-d", branch)
        _append_log(db, tid, f"Merged {branch} → {orig_branch}, branch deleted")
    except subprocess.CalledProcessError as exc:
        return abort(f"Merge failed: {exc.stderr[:200]}", "CRITICAL")

    # Step 11: Ticket completion
    duration = time.time() - start_ts
    _update_ticket(db, tid, {
        "status":           "done",
        "completed_at":     datetime.now(_AZ).isoformat(),
        "git_commit_hash":  commit_hash,
        "agent_summary":    agent_summary,
        "smoke_test_passed": True,
    })
    _append_log(db, tid, f"DONE — {duration:.0f}s elapsed")
    _audit(tid, "done",
           len(all_written), commit_hash, duration)

    _discord(
        "SUCCESS",
        f"{tid} Complete — {title}",
        agent_summary or "Ticket completed successfully.",
        fields=[
            {"name": "Files modified", "value": str(len(files_modified)),  "inline": True},
            {"name": "Files created",  "value": str(len(files_created)),   "inline": True},
            {"name": "Commit",         "value": f"`{commit_hash}`",        "inline": True},
            {"name": "Duration",       "value": f"{duration:.0f}s",        "inline": True},
            {"name": "Branch",         "value": f"merged → {orig_branch}", "inline": True},
        ],
    )

    _log("DONE", f"{tid} complete in {duration:.0f}s — {commit_hash}")
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def main(dry_run: bool = False) -> None:
    _log("BOOT", f"Dev agent starting {'(DRY RUN) ' if dry_run else ''}— {_ts()}")

    # Pre-flight: ANTHROPIC_API_KEY
    if not ANTHROPIC_KEY and not dry_run:
        _log("ERROR", "ANTHROPIC_API_KEY not set in .env — dev agent cannot run")
        _discord("WARNING", "Dev Agent Config Error",
                 "ANTHROPIC_API_KEY is missing from .env. "
                 "Add it to enable autonomous ticket processing.")
        sys.exit(1)

    db = _load_tickets()

    if db.get("paused") and not dry_run:
        _log("INFO", "Dev agent is paused (!ticket resume to unpause)")
        return

    # Filter open tickets, sort by priority
    open_tickets = [
        t for t in db["tickets"]
        if t.get("status") == "open"
    ]
    open_tickets.sort(key=lambda t: PRIORITY_ORDER.get(t.get("priority", "low"), 3))

    if not open_tickets:
        _log("INFO", "No open tickets — nothing to do")
        return

    _log("INFO", f"Found {len(open_tickets)} open ticket(s), will process up to {MAX_TICKETS}")

    processed = 0
    for ticket in open_tickets[:MAX_TICKETS]:
        tid = ticket["id"]

        # Safety checks (fresh db read each ticket)
        db = _load_tickets()
        ticket = next((t for t in db["tickets"] if t["id"] == tid), None)
        if ticket is None:
            continue

        ok, reason = safety_checks(ticket)
        if not ok:
            _log("SAFETY", reason)
            if "market hours" in reason:
                break   # All future tickets blocked too — stop the run
            continue

        success = run_ticket(ticket, db, dry_run=dry_run)
        processed += 1

        if processed < min(len(open_tickets), MAX_TICKETS):
            _log("RATE", f"Waiting {TICKET_DELAY}s before next ticket…")
            time.sleep(TICKET_DELAY)

    _log("DONE", f"Run complete — {processed} ticket(s) processed")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    main(dry_run=dry)
