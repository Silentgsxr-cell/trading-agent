"""
chief.py — CHIEF: Chief of Staff Orchestrator

The operator's primary interface agent. Runs at 6:00 AM and 4:30 PM AZ.
Reads state from all agents, makes one Claude API call, and writes a
structured assessment to logs/chief_assessment.json for Mission Control
to display on the /chief home page.

Launch: python3 agents/chief.py
        python3 agents/chief.py --dry-run  (no API call, no writes)
"""

import json
import os
import sys
import argparse
import logging
import traceback
from datetime import datetime
from typing import Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from utils.agent_brain import AgentBrain, _post_discord

log = logging.getLogger("chief")
log.setLevel(logging.INFO)
log.propagate = False
if not log.handlers:
    _log_path = os.path.join(_ROOT, "logs", "chief.log")
    os.makedirs(os.path.dirname(_log_path), exist_ok=True)
    _fmt = logging.Formatter("%(asctime)s [chief] %(levelname)s %(message)s")
    _fh  = logging.FileHandler(_log_path)
    _fh.setFormatter(_fmt)
    _sh  = logging.StreamHandler(sys.stdout)
    _sh.setFormatter(_fmt)
    log.addHandler(_fh)
    log.addHandler(_sh)

brain = AgentBrain("CHIEF", "#7c3aed")

ASSESSMENT_FILE = os.path.join(_ROOT, "logs", "chief_assessment.json")
MAX_CHARS = 1200


# ── Context gathering ──────────────────────────────────────────────────────────

def _read_file_tail(path: str, max_lines: int = 30) -> str:
    try:
        with open(path) as f:
            lines = f.readlines()
        return "".join(lines[-max_lines:])
    except OSError:
        return ""


def _read_json(path: str) -> object:
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _read_jsonl_tail(path: str, max_lines: int = 20) -> list:
    try:
        with open(path) as f:
            lines = [l.strip() for l in f if l.strip()]
        out = []
        for line in lines[-max_lines:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return out
    except OSError:
        return []


def _truncate(text: str, limit: int = MAX_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"... [{len(text) - limit} chars truncated]"


def _agent_status_scan(agents_dir: str, utils_dir: str) -> dict:
    """Scan agent files and return live/stub/missing status for each."""
    targets = {
        "HAWK":    ("agents", "signaos.py"),
        "VAULT":   ("agents", "risk_engine.py"),
        "PULSE":   ("agents", "dataos.py"),
        "TRIGGER": ("agents", "execution_agent.py"),
        "LEDGER":  ("agents", "review_agent.py"),
        "INTEL":   ("utils",  "daitaos.py"),
        "WATCH":   ("utils",  "watchdog.py"),
        "SAGE":    ("utils",  "suggestion_agent.py"),
    }
    status = {}
    for name, (loc, fname) in targets.items():
        base = agents_dir if loc == "agents" else utils_dir
        path = os.path.join(base, fname)
        try:
            with open(path) as f:
                src = f.read()
            status[name] = "stub" if "raise NotImplementedError" in src else "live"
        except OSError:
            status[name] = "missing"
    return status


def _gather_context() -> dict:
    data_dir   = os.path.join(_ROOT, "data")
    state_dir  = os.path.join(_ROOT, "state")
    logs_dir   = os.path.join(_ROOT, "logs")
    agents_dir = os.path.join(_ROOT, "agents")
    utils_dir  = os.path.join(_ROOT, "utils")

    session       = _read_json(os.path.join(state_dir, "session.json")) or {}
    decisions     = _read_jsonl_tail(os.path.join(state_dir, "decisions.jsonl"), 30)
    suggestions   = _read_json(os.path.join(data_dir, "suggestions.json")) or []
    journal_tail  = _read_file_tail(os.path.join(data_dir, "journal.csv"), 20)
    watchdog_tail = _read_file_tail(os.path.join(logs_dir, "watchdog.log"), 20)
    morning_brief = _read_json(os.path.join(logs_dir, "morning_brief_log.json"))
    tickets_raw   = _read_json(os.path.join(data_dir, "tickets.json")) or {}
    agent_status  = _agent_status_scan(agents_dir, utils_dir)

    open_sugs    = [s for s in suggestions if isinstance(s, dict) and s.get("status") == "open"]
    critical_sugs = [s for s in open_sugs if s.get("priority", 0) >= 9]

    # Tickets may be a dict with a list or a bare list
    tickets_list = tickets_raw if isinstance(tickets_raw, list) else tickets_raw.get("tickets", [])
    open_tickets = [t for t in tickets_list if isinstance(t, dict) and t.get("status") == "open"]

    return {
        "session":              _truncate(json.dumps(session)),
        "recent_decisions":     _truncate(json.dumps(decisions)),
        "open_suggestions":     _truncate(json.dumps(open_sugs[:8])),
        "critical_suggestions": _truncate(json.dumps(critical_sugs)),
        "journal_tail":         _truncate(journal_tail),
        "watchdog_tail":        _truncate(watchdog_tail),
        "morning_brief":        _truncate(json.dumps(morning_brief or {})),
        "open_tickets":         _truncate(json.dumps(open_tickets[:5])),
        "agent_status":         json.dumps(agent_status),
        "current_time":         datetime.now().strftime("%Y-%m-%d %H:%M AZ"),
    }


# ── Claude API call ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are CHIEF — the Chief of Staff orchestrator for ClawOps, a paper options-trading system for TSLA.
The operator is Silent, a solo trader building a disciplined ORB trading system.

Analyze all provided agent state and produce a structured master assessment.
Output ONLY valid JSON. No explanation, no markdown, no code fences.

Output format:
{
  "assessment": "2-3 sentences on overall system state and readiness. Specific, direct, honest.",
  "directive": "The single most important thing the operator must act on right now. Max 120 chars.",
  "handoffs": [
    {"from_agent": "AGENT_NAME", "to_agent": "AGENT_NAME_OR_OPERATOR", "note": "What needs to happen. Under 100 chars."}
  ],
  "readiness_pct": 0,
  "system_health": "nominal",
  "key_blocker": "One sentence on the primary thing blocking live trading readiness, or null.",
  "next_session_prep": "What to do before next trading session. Max 150 chars."
}

Rules:
- readiness_pct: integer 0-100 based on live agents vs total. HAWK+VAULT both live = at least tradeable on paper.
- system_health: "nominal" (core agents live, no circuit breaker), "degraded" (stubs present or watchdog alerts), "critical" (session halted or CRITICAL watchdog alert).
- handoffs: only real coordination needs from the data — max 3 items. Omit array if none needed.
- directive: if session is halted → address halt first. If HAWK+VAULT live but PULSE is stub → flag data gap.
- key_blocker: be specific (e.g., "PULSE is a stub — no live bar data for HAWK ORB signals"). null if system is paper-ready.
- Vague advice is useless. Silent needs to know exactly what to do next.
"""


def _call_claude(context: dict, dry_run: bool = False) -> Optional[dict]:
    if dry_run:
        log.info("[DRY RUN] Skipping Claude API call")
        return {
            "assessment": "Dry run — CHIEF online. All data sources accessible. Context gathered from all 8 agents.",
            "directive": "Add Anthropic API credits to run CHIEF live and surface real intelligence.",
            "handoffs": [],
            "readiness_pct": 25,
            "system_health": "degraded",
            "key_blocker": "Several agents are stubs — PULSE, TRIGGER, and LEDGER need implementation before paper trading is fully wired.",
            "next_session_prep": "Review HAWK signal config and confirm VAULT circuit breaker thresholds before 9:30 AM ET.",
        }

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        log.error("ANTHROPIC_API_KEY not set — cannot call Claude API")
        return None

    import urllib.request
    import urllib.error

    payload = json.dumps({
        "model":      "claude-sonnet-4-6",
        "max_tokens": 1200,
        "system":     SYSTEM_PROMPT,
        "messages":   [{"role": "user", "content": json.dumps(context)}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode())
            text = body["content"][0]["text"].strip()
            result = json.loads(text)
            result["generated_at"] = datetime.now().isoformat()
            return result
    except urllib.error.HTTPError as e:
        log.error("Claude API HTTP %s: %s", e.code, e.read().decode()[:300])
        return None
    except (json.JSONDecodeError, KeyError) as e:
        log.error("Failed to parse Claude response: %s", e)
        return None
    except Exception as e:
        log.error("Claude API call failed: %s", e)
        return None


# ── Output ─────────────────────────────────────────────────────────────────────

def _write_assessment(data: dict) -> None:
    data.setdefault("generated_at", datetime.now().isoformat())
    os.makedirs(os.path.dirname(ASSESSMENT_FILE), exist_ok=True)
    with open(ASSESSMENT_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)
    log.info("Assessment written → %s", ASSESSMENT_FILE)


def _post_to_discord(data: dict) -> None:
    webhook_url = os.getenv("DISCORD_AGENT_ACTIVITY_WEBHOOK", "")
    if not webhook_url:
        return

    health = data.get("system_health", "nominal")
    color  = {"nominal": 0x3DDC97, "degraded": 0xF2B84B, "critical": 0xC02A44}.get(health, 0x5B6680)

    fields = [
        {"name": "Health",    "value": health.upper(),                          "inline": True},
        {"name": "Readiness", "value": f"{data.get('readiness_pct', 0)}%",      "inline": True},
    ]
    if data.get("key_blocker"):
        fields.append({"name": "Key Blocker", "value": data["key_blocker"][:200], "inline": False})
    if data.get("next_session_prep"):
        fields.append({"name": "Next Session", "value": data["next_session_prep"], "inline": False})

    embed = {
        "title":       f"[CHIEF] {data.get('directive', 'Assessment complete')}",
        "description": data.get("assessment", ""),
        "color":       color,
        "fields":      fields,
        "footer":      {"text": f"ClawOps CHIEF · {datetime.now().strftime('%Y-%m-%d %H:%M')}"},
    }
    _post_discord(webhook_url, embed)


# ── Main ───────────────────────────────────────────────────────────────────────

def run(dry_run: bool = False) -> None:
    log.info("=== CHIEF starting (dry_run=%s) ===", dry_run)

    env_path = os.path.join(_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())

    log.info("Gathering context from all agents...")
    context = _gather_context()
    log.info("Context bundle: %d bytes", sum(len(str(v)) for v in context.values()))

    log.info("Calling Claude API...")
    result = _call_claude(context, dry_run=dry_run)

    if result is None:
        log.error("No result from Claude — aborting cycle")
        return

    if not dry_run:
        _write_assessment(result)
        _post_to_discord(result)
    else:
        log.info("[DRY RUN] Assessment:\n%s", json.dumps(result, indent=2))

    log.info("=== CHIEF cycle complete ===")
    log.info("Health: %s | Readiness: %s%% | Directive: %s",
             result.get("system_health"), result.get("readiness_pct"), result.get("directive"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CHIEF — ClawOps Chief of Staff")
    parser.add_argument("--dry-run", action="store_true", help="Gather context but skip API call and writes")
    args = parser.parse_args()
    try:
        run(dry_run=args.dry_run)
    except Exception:
        log.error("CHIEF crashed:\n%s", traceback.format_exc())
        sys.exit(1)
