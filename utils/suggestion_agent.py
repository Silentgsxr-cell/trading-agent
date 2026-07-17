"""
suggestion_agent.py — Autonomous suggestion agent for ClawOps.

Runs at 5:00 AM and 5:30 PM Arizona MST via LaunchAgent.
Makes ONE Claude API call per run with all context bundled,
then posts suggestions via AgentBrain.

Launch: python3 utils/suggestion_agent.py
        python3 utils/suggestion_agent.py --dry-run  (no API call, no writes)
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

from utils.agent_brain import AgentBrain, AGENT_AVATARS, _post_discord

# Status-reporting identity for SAGE itself (separate from the per-suggestion
# AgentBrain instances created below, which post cards under other agents'
# names — e.g. a suggestion about VAULT posts as VAULT, not SAGE).
_status_brain = AgentBrain("SAGE", "#eab308")

log = logging.getLogger("suggestion_agent")
log.setLevel(logging.INFO)
log.propagate = False
if not log.handlers:
    _log_path = os.path.join(_ROOT, "logs", "suggestion_agent.log")
    _fmt = logging.Formatter("%(asctime)s [suggestion_agent] %(levelname)s %(message)s")
    _fh  = logging.FileHandler(_log_path)
    _fh.setFormatter(_fmt)
    _sh  = logging.StreamHandler(sys.stdout)
    _sh.setFormatter(_fmt)
    log.addHandler(_fh)
    log.addHandler(_sh)

# Agent color palette for suggestions
AGENT_COLORS = {
    "VAULT":     "#c02a44",
    "HAWK":      "#3ddc97",
    "DATAOS":    "#4fc3f7",
    "TRIGGER":   "#ff7043",
    "LEDGER":    "#ab47bc",
    "WATCHDOG":  "#f2b84b",
    "DEV_AGENT": "#5c6bc0",
}

CYCLE_LOG = os.path.join(_ROOT, "logs", "suggestion_cycles.log")
MAX_CHARS  = 1000   # truncate each data source before bundling


def _read_file_tail(path: str, max_lines: int = 20) -> str:
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


def _truncate(text: str, limit: int = MAX_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"... [{len(text) - limit} chars truncated]"


def _stub_scan(agents_dir: str) -> dict:
    """Scan agents/ for file sizes and stub status."""
    result = {}
    try:
        for fn in os.listdir(agents_dir):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(agents_dir, fn)
            try:
                with open(path) as f:
                    src = f.read()
                result[fn] = {
                    "lines":   src.count("\n"),
                    "is_stub": "raise NotImplementedError" in src,
                }
            except OSError:
                pass
    except OSError:
        pass
    return result


def _gather_context() -> dict:
    """Read all data sources and return a size-capped context bundle."""
    data_dir  = os.path.join(_ROOT, "data")
    state_dir = os.path.join(_ROOT, "state")
    logs_dir  = os.path.join(_ROOT, "logs")

    journal_raw      = _read_file_tail(os.path.join(data_dir, "journal.csv"), 50)
    session_raw      = json.dumps(_read_json(os.path.join(state_dir, "session.json")) or {})
    decisions_raw    = _read_file_tail(os.path.join(state_dir, "decisions.jsonl"), 50)
    tickets_raw      = json.dumps(_read_json(os.path.join(data_dir, "tickets.json")) or {})
    suggestions_raw  = json.dumps(_read_json(os.path.join(data_dir, "suggestions.json")) or [])
    finance_raw      = json.dumps(_read_json(os.path.join(data_dir, "finance.json")) or {})
    watchdog_tail    = _read_file_tail(os.path.join(logs_dir, "watchdog.log"), 20)
    tab_usage_raw    = json.dumps(_read_json(os.path.join(data_dir, "tab_usage.json")) or {})
    agents_scan      = json.dumps(_stub_scan(os.path.join(_ROOT, "agents")))

    return {
        "journal_csv":       _truncate(journal_raw),
        "session_json":      _truncate(session_raw),
        "decisions_jsonl":   _truncate(decisions_raw),
        "tickets_json":      _truncate(tickets_raw),
        "suggestions_json":  _truncate(suggestions_raw),
        "finance_json":      _truncate(finance_raw),
        "watchdog_log_tail": _truncate(watchdog_tail),
        "tab_usage_json":    _truncate(tab_usage_raw),
        "agents_stub_scan":  _truncate(agents_scan),
    }


SYSTEM_PROMPT = """\
You are a suggestion agent for a trading mission control dashboard called ClawOps.
Analyze the provided data and generate exactly 3 suggestions per agent category.
Output ONLY valid JSON, no explanation, no markdown, no code fences.

Output format:
{
  "suggestions": [
    {
      "agent_id": "VAULT|HAWK|DATAOS|TRIGGER|LEDGER|WATCHDOG|DEV_AGENT",
      "title": "concise suggestion title",
      "reasoning": "2-3 sentences explaining why this matters based on the data",
      "category": "UI|Trading|Risk|Life|Agents|Security",
      "priority": 1,
      "flags": [],
      "affected_files": []
    }
  ],
  "cycle_summary": "one paragraph summary of overall system health"
}

Rules:
- Generate exactly 3 suggestions total (across all agents) — quality over quantity
- Priority 9-10 only for genuine security risks or patterns that could cause real financial loss
- If a suggestion requires modifying agents/ or config/ files, add "locked_file" to flags
- Base every suggestion on specific data provided — no generic advice
- Do not repeat suggestions already present in suggestions_json
- Keep each title under 80 characters
- Keep reasoning under 300 characters
"""


def _call_claude(context: dict, dry_run: bool = False) -> Optional[dict]:
    if dry_run:
        log.info("[DRY RUN] Skipping Claude API call")
        return {
            "suggestions": [
                {
                    "agent_id":       "WATCHDOG",
                    "title":          "Dry run — suggestion agent online",
                    "reasoning":      "Suggestion agent ran in dry-run mode. All data sources accessible.",
                    "category":       "Security",
                    "priority":       3,
                    "flags":          [],
                    "affected_files": [],
                }
            ],
            "cycle_summary": "Dry run completed. System context gathered successfully.",
        }

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        log.error("ANTHROPIC_API_KEY not set — cannot call Claude API")
        return None

    import urllib.request
    import urllib.error

    payload = json.dumps({
        "model":      "claude-sonnet-4-6",
        "max_tokens": 2000,
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
            return json.loads(text)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()[:300]
        log.error("Claude API HTTP %s: %s", e.code, err_body)
        return None
    except (json.JSONDecodeError, KeyError) as e:
        log.error("Failed to parse Claude response: %s", e)
        return None
    except Exception as e:
        log.error("Claude API call failed: %s", e)
        return None


def _post_cycle_summary(summary: str, high_priority: bool) -> None:
    activity_url = os.getenv("DISCORD_AGENT_ACTIVITY_WEBHOOK", "")
    if activity_url:
        embed = {
            "title":       "Suggestion Agent — Cycle Complete",
            "description": summary[:1500],
            "color":       0x5C6BC0,
            "footer":      {"text": f"ClawOps · {datetime.now().strftime('%Y-%m-%d %H:%M')}"},
        }
        _post_discord(activity_url, embed)

    if high_priority:
        sug_url = os.getenv("DISCORD_SUGGESTIONS_WEBHOOK", "")
        if sug_url:
            embed["title"] = "🚨 Suggestion Agent — High Priority Items Found"
            embed["color"]  = 0xC02A44
            _post_discord(sug_url, embed)


def _log_cycle(n_suggestions: int, n_high: int, summary: str) -> None:
    line = (
        f"{datetime.now().isoformat()} | "
        f"suggestions:{n_suggestions} | high_priority:{n_high} | "
        f"summary:{summary[:200]}\n"
    )
    try:
        with open(CYCLE_LOG, "a") as f:
            f.write(line)
    except OSError:
        pass


def run(dry_run: bool = False) -> None:
    log.info("=== Suggestion Agent starting (dry_run=%s) ===", dry_run)

    # Load .env
    env_path = os.path.join(_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())

    # Gather context
    _status_brain.start_task("Reading 9 data sources", queue_len=9)
    log.info("Gathering context from data sources...")
    context = _gather_context()
    log.info("Context bundle: %d bytes total", sum(len(str(v)) for v in context.values()))

    # Claude API call
    _status_brain.update_task("Calling Claude for suggestions", waiting_on="Anthropic API")
    log.info("Calling Claude API...")
    result = _call_claude(context, dry_run=dry_run)

    if result is None:
        log.error("No result from Claude — aborting cycle")
        _status_brain.error("Claude API call failed — check ANTHROPIC_API_KEY")
        return

    suggestions = result.get("suggestions", [])
    cycle_summary = result.get("cycle_summary", "")
    log.info("Received %d suggestions from Claude", len(suggestions))

    # Post suggestions via AgentBrain
    high_priority_found = False
    n_posted = 0

    for s in suggestions:
        agent_id = str(s.get("agent_id", "WATCHDOG")).upper()
        color    = AGENT_COLORS.get(agent_id, "#5b6680")
        brain    = AgentBrain(agent_id, color)

        priority = int(s.get("priority", 5))
        if priority >= 9:
            high_priority_found = True

        if not dry_run:
            card = brain.suggest(
                title          = str(s.get("title", "Untitled")),
                reasoning      = str(s.get("reasoning", "")),
                category       = str(s.get("category", "UI")),
                priority       = priority,
                flags          = list(s.get("flags", [])),
                affected_files = list(s.get("affected_files", [])),
            )
            if card:
                n_posted += 1
                log.info("Posted %s: [%s] %s (priority=%d)", card.get("id"), agent_id, s.get("title"), priority)
        else:
            log.info("[DRY RUN] Would post [%s] %s (priority=%d)", agent_id, s.get("title"), priority)
            n_posted += 1

    # Post cycle summary to Discord
    _post_cycle_summary(cycle_summary, high_priority_found)

    # Append to cycle log
    _log_cycle(n_posted, sum(1 for s in suggestions if int(s.get("priority", 0)) >= 9), cycle_summary)

    log.info("=== Cycle complete: %d suggestions posted ===", n_posted)
    _status_brain.finish_task(f"Posted {n_posted} suggestion(s) — {cycle_summary[:80]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        run(dry_run=args.dry_run)
    except Exception as exc:
        log.error("Suggestion agent crashed:\n%s", traceback.format_exc())
        _status_brain.error(f"Crashed: {exc}")
        sys.exit(1)
