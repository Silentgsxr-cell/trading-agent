#!/usr/bin/env python3
"""
utils/daitaos_sync.py — Commit activity logs and config to GitHub.
Runs daily at 4:30 PM AZ via launchd (after market close).
Requires ~/trading-agent 2/ to be a git repo with origin set.
Setup: cd ~/trading-agent\ 2 && git init -b master &&
       git remote add origin https://github.com/Silentgsxr-cell/trading-agent.git &&
       git fetch origin && git checkout -f -B master origin/master
"""
import os
import sys
import subprocess
import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UTILS_DIR    = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, UTILS_DIR)

from daitaos_logger import log

STAGE_PATHS = [
    "logs/",
    "data/daitaos_config.json",
    "data/finance.json",
    "state/session.json",
]


def run(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)


def sync():
    today = datetime.date.today().isoformat()

    # Pull latest so we don't diverge from Desktop commits
    pull = run(["git", "pull", "--rebase", "--autostash"])
    if pull.returncode != 0:
        print(f"git pull warning:\n{pull.stderr.strip()}")

    # Stage logs and runtime data
    run(["git", "add"] + STAGE_PATHS)

    # Nothing to commit → exit cleanly
    diff = run(["git", "diff", "--cached", "--quiet"])
    if diff.returncode == 0:
        print(f"✅  Nothing to sync on {today}")
        return

    # Commit
    msg = f"auto: activity log {today}"
    commit = run(["git", "commit", "-m", msg,
                  "--author=DaiTaos Bot <daitaos@silent.local>"])
    if commit.returncode != 0:
        print(f"❌  git commit failed:\n{commit.stderr.strip()}")
        log("⚠️", "GitHub Sync Failed", f"git commit error: {commit.stderr.strip()[:200]}")
        return

    # Push
    push = run(["git", "push", "origin", "master"])
    if push.returncode != 0:
        print(f"❌  git push failed:\n{push.stderr.strip()}")
        log("⚠️", "GitHub Sync Failed", f"git push error: {push.stderr.strip()[:200]}")
        return

    print(f"✅  Synced to GitHub: {msg}")
    log("📊", "GitHub Sync", f"Committed and pushed: `{msg}`")


if __name__ == "__main__":
    sync()
