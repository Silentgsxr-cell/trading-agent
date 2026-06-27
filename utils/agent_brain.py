"""
agent_brain.py — Shared brain module for all ClawOps agents.

Every agent imports AgentBrain to:
  - post suggestion cards to data/suggestions.json
  - send tiered Discord alerts to the correct channel webhook
  - append reasoning traces to logs/agent_reasoning.log

Single file. No circular imports. No agent-specific logic.
"""

import json
import os
import re
import time
import logging
from datetime import datetime, date
from typing import Optional

try:
    from filelock import FileLock
except ImportError:
    FileLock = None  # graceful degradation — writes proceed without lock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SUGGESTIONS_FILE = os.path.join(_ROOT, "data", "suggestions.json")
_REASONING_LOG    = os.path.join(_ROOT, "logs", "agent_reasoning.log")

# Paths that trigger auto "locked_file" flag when found in affected_files
_BLOCKED_PATHS = [
    "agents/", "config/", "tests/", ".env",
    "utils/watchdog.py", "utils/state_manager.py",
    "utils/journal_writer.py", "utils/event_log.py",
]

# Webhook env var name per logical channel name
_WEBHOOK_MAP = {
    "morning_brief":  "DISCORD_MORNING_BRIEF_WEBHOOK",
    "trade_alerts":   "DISCORD_TRADE_ALERTS_WEBHOOK",
    "watchdog":       "DISCORD_WATCHDOG_WEBHOOK",
    "dev_agent":      "DISCORD_DEV_AGENT_WEBHOOK",
    "suggestions":    "DISCORD_SUGGESTIONS_WEBHOOK",
    "agent_activity": "DISCORD_AGENT_ACTIVITY_WEBHOOK",
}

# Flag emoji display map
FLAG_EMOJIS = {
    "locked_file":    "⚠️",
    "critical":       "🚨",
    "pii_risk":       "🔴",
    "tricky_code":    "🔧",
    "auth_problem":   "🔑",
    "time_sensitive": "⏰",
}

# Agent avatar names (used in UI for avatar selection)
AGENT_AVATARS = {
    "VAULT":     "shield",
    "HAWK":      "radar",
    "DATAOS":    "database",
    "TRIGGER":   "bolt",
    "LEDGER":    "book",
    "WATCHDOG":  "eye",
    "DEV_AGENT": "code",
}

logging.basicConfig(level=logging.WARNING)
_log = logging.getLogger("agent_brain")


def _load_suggestions() -> list:
    if not os.path.exists(_SUGGESTIONS_FILE):
        return []
    try:
        with open(_SUGGESTIONS_FILE) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_suggestions(cards: list) -> None:
    lock_path = _SUGGESTIONS_FILE + ".lock"
    if FileLock is not None:
        lock = FileLock(lock_path, timeout=5)
        with lock:
            with open(_SUGGESTIONS_FILE, "w") as f:
                json.dump(cards, f, indent=2, default=str)
    else:
        with open(_SUGGESTIONS_FILE, "w") as f:
            json.dump(cards, f, indent=2, default=str)


def _next_sug_id(cards: list) -> str:
    nums = []
    for c in cards:
        m = re.match(r"SUG-(\d+)", c.get("id", ""))
        if m:
            nums.append(int(m.group(1)))
    return f"SUG-{max(nums, default=0) + 1:03d}"


def _has_locked_path(affected_files: list) -> bool:
    for af in affected_files:
        for bp in _BLOCKED_PATHS:
            if af.startswith(bp) or bp.rstrip("/") == af:
                return True
    return False


def _post_discord(webhook_url: str, embed: dict) -> None:
    """Fire-and-forget Discord POST. Never raises — failure is logged only."""
    try:
        import urllib.request
        payload = json.dumps({"embeds": [embed]}).encode()
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status not in (200, 204):
                _log.warning("Discord POST returned %s", resp.status)
    except Exception as exc:
        _log.warning("Discord alert failed: %s", exc)


def _color_for_level(level: str) -> int:
    return {"critical": 0xC02A44, "warning": 0xF2B84B, "info": 0x3DDC97}.get(level, 0x5B6680)


class AgentBrain:
    """
    Import once per agent at module level:
        from utils.agent_brain import AgentBrain
        brain = AgentBrain("VAULT", "#c02a44")
    """

    def __init__(self, agent_id: str, agent_color: str):
        self.agent_id    = agent_id.upper()
        self.agent_color  = agent_color
        self.agent_avatar = AGENT_AVATARS.get(self.agent_id, "circle")
        self._cycle_date: Optional[str] = None
        self._cycle_count: int = 0

    # ── Internal cycle tracking ───────────────────────────────────────────

    def _reset_cycle_if_new(self) -> None:
        today = date.today().isoformat()
        if self._cycle_date != today:
            self._cycle_date  = today
            self._cycle_count = 0

    # ── Public API ────────────────────────────────────────────────────────

    def suggest(
        self,
        title: str,
        reasoning: str,
        category: str,
        priority: int,
        flags: Optional[list] = None,
        affected_files: Optional[list] = None,
    ) -> dict:
        """
        Create a suggestion card and append it to data/suggestions.json.

        Hard cap: 3 suggestions per agent per calendar day.
        Override: priority >= 9 always posts regardless of cap.
        Blocked paths in affected_files → auto-adds 'locked_file' flag.
        Returns the created card dict.
        """
        flags          = list(flags or [])
        affected_files = list(affected_files or [])

        # Enforce cap
        self._reset_cycle_if_new()
        if self._cycle_count >= 3 and priority < 9:
            _log.info("%s cap reached for today, skipping '%s'", self.agent_id, title)
            return {}

        # Auto-locked-file detection
        locked = _has_locked_path(affected_files)
        if locked and "locked_file" not in flags:
            flags.append("locked_file")
            if not title.startswith("⚠️"):
                title = "⚠️ " + title

        flag_emojis = " ".join(FLAG_EMOJIS[f] for f in flags if f in FLAG_EMOJIS)

        cards = _load_suggestions()
        card = {
            "id":              _next_sug_id(cards),
            "agent_id":        self.agent_id,
            "agent_color":     self.agent_color,
            "agent_avatar":    self.agent_avatar,
            "title":           title,
            "reasoning":       reasoning,
            "category":        category,
            "priority":        int(priority),
            "flags":           flags,
            "flag_emojis":     flag_emojis,
            "affected_files":  affected_files,
            "has_locked_files": locked,
            "status":          "open",
            "queue":           None,
            "completed_by":    None,
            "archive_reason":  "",
            "progress_pct":    0,
            "dev_ticket_id":   None,
            "user_edits":      "",
            "created_at":      datetime.now().isoformat(),
            "updated_at":      datetime.now().isoformat(),
            "archived_at":     None,
            "discord_posted":  False,
            "cycle_id":        f"{self.agent_id}-{date.today().isoformat()}",
        }

        cards.append(card)
        _save_suggestions(cards)

        self._cycle_count += 1

        # High-priority Discord notification
        if priority >= 9:
            self._post_suggestion_alert(card)

        return card

    def urgent_alert(
        self,
        message: str,
        level: str = "warning",
        channel: str = "agent_activity",
    ) -> None:
        """
        Send a Discord embed to the specified channel webhook.

        channel must be one of: morning_brief | trade_alerts | watchdog |
            dev_agent | suggestions | agent_activity
        Priority < 9 always routes to agent_activity regardless of channel.
        """
        env_var = _WEBHOOK_MAP.get(channel, _WEBHOOK_MAP["agent_activity"])
        webhook_url = os.getenv(env_var, "")
        if not webhook_url:
            _log.debug("No webhook configured for channel '%s' (%s)", channel, env_var)
            return

        embed = {
            "title":       f"[{self.agent_id}] {level.upper()}",
            "description": message,
            "color":       _color_for_level(level),
            "footer":      {"text": f"ClawOps · {datetime.now().strftime('%H:%M:%S')}"},
        }
        _post_discord(webhook_url, embed)

    def log_reasoning(self, thought: str, confidence: float) -> None:
        """
        Append a reasoning trace to logs/agent_reasoning.log.
        Format: {timestamp} | {agent_id} | {confidence:.2f} | {thought}
        """
        os.makedirs(os.path.dirname(_REASONING_LOG), exist_ok=True)
        line = (
            f"{datetime.now().isoformat()} | {self.agent_id} | "
            f"{confidence:.2f} | {thought}\n"
        )
        try:
            with open(_REASONING_LOG, "a") as f:
                f.write(line)
        except OSError as exc:
            _log.warning("Could not write reasoning log: %s", exc)

    # ── Internal helpers ──────────────────────────────────────────────────

    def _post_suggestion_alert(self, card: dict) -> None:
        webhook_url = os.getenv("DISCORD_SUGGESTIONS_WEBHOOK", "")
        if not webhook_url:
            return
        priority = card["priority"]
        color    = 0xC02A44 if priority >= 9 else 0xF2B84B
        embed = {
            "title":       f"[{card['agent_id']}] {card['flag_emojis']} {card['title']}",
            "description": card["reasoning"][:500],
            "color":       color,
            "fields": [
                {"name": "Category", "value": card["category"], "inline": True},
                {"name": "Priority", "value": str(priority),    "inline": True},
                {"name": "ID",       "value": card["id"],        "inline": True},
            ],
            "footer": {"text": f"ClawOps Suggestions · {card['created_at'][:19]}"},
        }
        _post_discord(webhook_url, embed)
