#!/usr/bin/env python3
"""
utils/daitaos_bot.py — DaiTaos Discord bot.
Responds to !commands in any channel. Runs alongside the scheduled brief.
Requires DISCORD_BOT_TOKEN in .env and Message Content Intent enabled
in the Discord developer portal.
"""

import sys
import os
import json
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UTILS_DIR    = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, UTILS_DIR)

import discord
from discord.ext import commands
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from daitaos import (
    s1_date_status, s2_tsla_bias, s3_watchlist, s4_spy_bias,
    s5_rules, s6_session, s7_journal, s8_edge,
    EMBED_COLOR, DEFAULT_CONFIG, load_config,
)
from daitaos_logger import log

BOT_TOKEN   = os.getenv("DISCORD_BOT_TOKEN", "")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "data", "daitaos_config.json")
PLIST_PATH  = os.path.join(PROJECT_ROOT, "com.silent.dataos.plist")

intents = discord.Intents.default()
intents.message_content = True

bot   = commands.Bot(command_prefix="!", intents=intents, help_command=None)
_pool = ThreadPoolExecutor(max_workers=4)


async def _run(fn, *args):
    """Run a blocking function in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_pool, fn, *args)


def _save_config(data: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _embed(title: str, value: str, footer: str = "") -> discord.Embed:
    e = discord.Embed(title=title, color=EMBED_COLOR)
    e.add_field(name="​", value=value or "—", inline=False)
    if footer:
        e.set_footer(text=footer)
    return e


# ── Bot events ────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"✅  DaiTaos bot connected as {bot.user}")
    log("🤖", "Bot Online", f"Connected as {bot.user}")
    if WEBHOOK_URL:
        try:
            requests.post(
                WEBHOOK_URL,
                json={"content": "🤖 DaiTaos online. Type `!help` for commands."},
                timeout=10,
            )
        except Exception as ex:
            print(f"Startup webhook failed: {ex}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"❌ Unknown command. Type `!help` for the full list.")
    else:
        await ctx.send(f"⚠️ Error: {error}")


# ── Commands ──────────────────────────────────────────────────────────────────

@bot.command(name="brief")
async def cmd_brief(ctx):
    """Send the full morning brief."""
    async with ctx.typing():
        fields = [
            ("📅  DATE & MARKET STATUS",   await _run(s1_date_status)),
            ("📈  TSLA DIRECTION BIAS",     await _run(s2_tsla_bias)),
            ("🔍  WATCHLIST SCAN",          await _run(s3_watchlist)),
            ("📊  SPY MARKET BIAS",         await _run(s4_spy_bias)),
            ("⚙️   TODAY'S TRADING RULES",  s5_rules()),
            ("🤖  AGENT & SESSION STATUS",  s6_session()),
            ("📓  JOURNAL EDGE SUMMARY",    s7_journal()),
            ("💡  SILENT'S EDGE REMINDER",  s8_edge()),
        ]
        total = sum(len(n) + len(v) for n, v in fields) + 40
        split = total > 5800

        embed1 = discord.Embed(title="🌅  Silent's Morning Brief", color=EMBED_COLOR)
        for name, value in (fields[:4] if split else fields):
            embed1.add_field(name=name, value=value, inline=False)
        if not split:
            embed1.set_footer(text="ClawOps · DaiTaos · Paper Mode")
        await ctx.send(embed=embed1)

        if split:
            embed2 = discord.Embed(color=EMBED_COLOR)
            for name, value in fields[4:]:
                embed2.add_field(name=name, value=value, inline=False)
            embed2.set_footer(text="ClawOps · DaiTaos · Paper Mode")
            await ctx.send(embed=embed2)

        log("🤖", "Bot: !brief", f"On-demand brief sent in #{ctx.channel.name}")


@bot.command(name="tsla")
async def cmd_tsla(ctx):
    """TSLA premarket bias: price, EMA 9, prior/premarket H/L."""
    async with ctx.typing():
        await ctx.send(embed=_embed("📈 TSLA Direction Bias", await _run(s2_tsla_bias)))
    log("🤖", "Bot: !tsla", f"TSLA bias requested in #{ctx.channel.name}")


@bot.command(name="watchlist")
async def cmd_watchlist(ctx):
    """Watchlist scan table for all configured symbols."""
    async with ctx.typing():
        cfg = load_config()
        e = _embed("🔍 Watchlist Scan", await _run(s3_watchlist))
        e.set_footer(text=f"Symbols: {', '.join(cfg.get('watchlist', DEFAULT_CONFIG['watchlist']))}")
        await ctx.send(embed=e)


@bot.command(name="status")
async def cmd_status(ctx):
    """Agent crew and session status from state/session.json."""
    await ctx.send(embed=_embed("🤖 Agent & Session Status", s6_session()))


@bot.command(name="rules")
async def cmd_rules(ctx):
    """Today's trading rules from risk_config.py."""
    await ctx.send(embed=_embed("⚙️ Today's Trading Rules", s5_rules()))


@bot.command(name="pnl")
async def cmd_pnl(ctx):
    """Journal edge summary: win rate, net P&L, streak."""
    await ctx.send(embed=_embed("📓 Journal Edge Summary", s7_journal()))


@bot.command(name="config")
async def cmd_config(ctx, *args):
    """Show or update DaiTaos config. Subcommands: time HH:MM, watchlist add/remove SYMBOL."""
    cfg = load_config()

    # !config — show current config
    if not args:
        wl = ", ".join(cfg.get("watchlist", []))
        await ctx.send(embed=_embed(
            "⚙️ DaiTaos Config",
            f"**Brief time:** `{cfg.get('send_time','06:20')}` {cfg.get('timezone','America/Phoenix')}\n"
            f"**Watchlist ({len(cfg.get('watchlist',[]))}):** {wl}"
        ))
        return

    # !config time HH:MM
    if args[0] == "time" and len(args) >= 2:
        try:
            h, m = map(int, args[1].split(":"))
            assert 0 <= h <= 23 and 0 <= m <= 59
        except Exception:
            await ctx.send("❌ Invalid time. Use `!config time HH:MM` (24-hour, e.g. `06:20`)")
            return

        old_time = cfg.get("send_time", "06:20")
        cfg["send_time"] = args[1]
        _save_config(cfg)
        log("⚙️", f"Config: Brief time changed", f"`{old_time}` → `{args[1]}` {cfg.get('timezone','America/Phoenix')}")

        # Update Hour/Minute in the plist file so next launchctl reload uses the new time
        plist_note = ""
        try:
            with open(PLIST_PATH) as f:
                xml = f.read()
            xml = re.sub(
                r'(<key>Hour</key>\s*<integer>)\d+(</integer>)',
                rf'\g<1>{h}\g<2>', xml
            )
            xml = re.sub(
                r'(<key>Minute</key>\s*<integer>)\d+(</integer>)',
                rf'\g<1>{m}\g<2>', xml
            )
            with open(PLIST_PATH, "w") as f:
                f.write(xml)
            plist_note = "\nPlist updated — to apply: `launchctl unload && launchctl load ~/Library/LaunchAgents/com.silent.dataos.plist`"
        except Exception as ex:
            plist_note = f"\nConfig saved. Plist update failed: {ex}"

        tz = cfg.get("timezone", "America/Phoenix")
        await ctx.send(f"✅ Brief time → **{args[1]}** {tz}{plist_note}")
        return

    # !config watchlist add/remove SYMBOL
    if args[0] == "watchlist" and len(args) >= 3:
        action = args[1].lower()
        symbol = args[2].upper()
        wl = list(cfg.get("watchlist", list(DEFAULT_CONFIG["watchlist"])))

        if action == "add":
            if symbol in wl:
                await ctx.send(f"⚠️ **{symbol}** is already in the watchlist.")
            else:
                wl.append(symbol)
                cfg["watchlist"] = wl
                _save_config(cfg)
                await ctx.send(f"✅ Added **{symbol}** to watchlist ({len(wl)} symbols).")
                log("⚙️", f"Config: Watchlist +{symbol}", f"Added {symbol} · {len(wl)} symbols total")

        elif action == "remove":
            if symbol not in wl:
                await ctx.send(f"⚠️ **{symbol}** is not in the watchlist.")
            else:
                wl.remove(symbol)
                cfg["watchlist"] = wl
                _save_config(cfg)
                await ctx.send(f"✅ Removed **{symbol}** from watchlist ({len(wl)} symbols).")
                log("⚙️", f"Config: Watchlist -{symbol}", f"Removed {symbol} · {len(wl)} symbols remaining")

        else:
            await ctx.send("❌ Usage: `!config watchlist add SYMBOL` or `!config watchlist remove SYMBOL`")
        return

    await ctx.send(
        "❌ Unknown config option. Available:\n"
        "`!config` — show current config\n"
        "`!config time HH:MM` — update brief send time\n"
        "`!config watchlist add SYMBOL` — add to watchlist\n"
        "`!config watchlist remove SYMBOL` — remove from watchlist"
    )


# ── Dev Agent ticket commands ─────────────────────────────────────────────────

TICKETS_FILE = os.path.join(PROJECT_ROOT, "data", "tickets.json")


def _load_tickets_bot() -> dict:
    if not os.path.exists(TICKETS_FILE):
        return {"paused": False, "tickets": []}
    with open(TICKETS_FILE) as f:
        return json.load(f)


def _save_tickets_bot(db: dict) -> None:
    with open(TICKETS_FILE, "w") as f:
        json.dump(db, f, indent=2)


def _ticket_by_id(db: dict, ticket_id: str):
    tid = ticket_id.upper()
    return next((t for t in db["tickets"] if t["id"].upper() == tid), None)


STATUS_EMOJI = {
    "open":         "🟢",
    "in_progress":  "🔵",
    "done":         "✅",
    "failed":       "🔴",
    "needs_review": "🟡",
}

PRIORITY_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}


@bot.command(name="approve")
async def cmd_approve(ctx, ticket_id: str = ""):
    """Approve a complex ticket for dev agent execution. !approve TICKET-XXX"""
    if not ticket_id:
        await ctx.send("❌ Usage: `!approve TICKET-XXX`")
        return
    db = _load_tickets_bot()
    t = _ticket_by_id(db, ticket_id)
    if t is None:
        await ctx.send(f"❌ Ticket `{ticket_id.upper()}` not found.")
        return
    if t["status"] not in ("needs_review", "open"):
        await ctx.send(f"⚠️ `{t['id']}` is `{t['status']}` — only needs_review or open tickets can be approved.")
        return
    t["status"] = "open"
    t["approval_gate"] = "approved"
    _save_tickets_bot(db)
    await ctx.send(embed=_embed(
        f"✅ {t['id']} Approved",
        f"**{t['title']}**\n\nTicket approved — dev agent will pick it up on the next scheduled run.",
    ))
    log("🟢", f"Bot: !approve {t['id']}", f"Approved by {ctx.author}")


@bot.command(name="ticket")
async def cmd_ticket(ctx, *args):
    """Dev agent ticket commands. !ticket status|pause|resume|log TICKET-XXX"""
    if not args:
        await ctx.send(
            "❌ Usage:\n"
            "`!ticket status` — all ticket statuses\n"
            "`!ticket pause` — pause dev agent\n"
            "`!ticket resume` — resume dev agent\n"
            "`!ticket log TICKET-XXX` — execution log for a ticket"
        )
        return

    sub = args[0].lower()

    # !ticket status
    if sub == "status":
        db = _load_tickets_bot()
        tickets = db.get("tickets", [])
        paused  = db.get("paused", False)
        if not tickets:
            await ctx.send("📋 No tickets in the queue.")
            return

        lines = []
        for t in tickets:
            em  = STATUS_EMOJI.get(t.get("status", ""), "•")
            pri = PRIORITY_EMOJI.get(t.get("priority", ""), "")
            lines.append(
                f"{em} `{t['id']}` {pri} **{t['title'][:40]}** "
                f"— _{t.get('status', '?')}_ / {t.get('complexity', '?')}"
            )

        footer = "⏸ Dev agent PAUSED" if paused else "▶ Dev agent active"
        chunks = []
        cur = ""
        for line in lines:
            if len(cur) + len(line) + 1 > 900:
                chunks.append(cur)
                cur = line
            else:
                cur = (cur + "\n" + line).strip()
        if cur:
            chunks.append(cur)

        for i, chunk in enumerate(chunks):
            e = discord.Embed(
                title=f"📋 Dev Queue ({len(tickets)} tickets)" if i == 0 else "📋 (continued)",
                color=EMBED_COLOR,
            )
            e.add_field(name="​", value=chunk, inline=False)
            if i == len(chunks) - 1:
                e.set_footer(text=footer)
            await ctx.send(embed=e)

    # !ticket pause
    elif sub == "pause":
        db = _load_tickets_bot()
        db["paused"] = True
        _save_tickets_bot(db)
        await ctx.send("⏸ Dev agent **paused** — won't pick up new tickets until `!ticket resume`.")
        log("⏸", "Bot: !ticket pause", f"Paused by {ctx.author}")

    # !ticket resume
    elif sub == "resume":
        db = _load_tickets_bot()
        db["paused"] = False
        _save_tickets_bot(db)
        await ctx.send("▶ Dev agent **resumed** — will pick up open tickets on next scheduled run.")
        log("▶", "Bot: !ticket resume", f"Resumed by {ctx.author}")

    # !ticket log TICKET-XXX
    elif sub == "log" and len(args) >= 2:
        ticket_id = args[1]
        db = _load_tickets_bot()
        t = _ticket_by_id(db, ticket_id)
        if t is None:
            await ctx.send(f"❌ Ticket `{ticket_id.upper()}` not found.")
            return
        entries = t.get("log") or []
        if not entries:
            await ctx.send(f"📋 `{t['id']}` has no log entries yet.")
            return
        # Show last 15 entries to stay within Discord limits
        shown = entries[-15:]
        text  = "\n".join(shown)
        if len(text) > 1800:
            text = text[-1800:]
        await ctx.send(embed=_embed(
            f"📋 Log — {t['id']} ({t.get('status','?')})",
            f"```\n{text}\n```",
            footer=f"{len(entries)} total entries" + (" (showing last 15)" if len(entries) > 15 else ""),
        ))

    else:
        await ctx.send(
            "❌ Unknown subcommand.\n"
            "`!ticket status` | `!ticket pause` | `!ticket resume` | `!ticket log TICKET-XXX`"
        )


@bot.command(name="revert")
async def cmd_revert(ctx, ticket_id: str = ""):
    """Revert a completed ticket by reverting its commit. !revert TICKET-XXX"""
    if not ticket_id:
        await ctx.send("❌ Usage: `!revert TICKET-XXX`")
        return

    db = _load_tickets_bot()
    t = _ticket_by_id(db, ticket_id)
    if t is None:
        await ctx.send(f"❌ Ticket `{ticket_id.upper()}` not found.")
        return
    if t.get("status") != "done":
        await ctx.send(f"⚠️ `{t['id']}` is `{t.get('status', '?')}` — only done tickets can be reverted.")
        return

    commit_hash = t.get("git_commit_hash", "")
    if not commit_hash:
        await ctx.send(f"❌ `{t['id']}` has no commit hash recorded — cannot revert automatically.")
        return

    await ctx.send(f"⏳ Reverting `{t['id']}` (commit `{commit_hash}`)…")

    def _do_revert():
        import subprocess as sp
        r1 = sp.run(
            ["git", "revert", "--no-edit", commit_hash],
            cwd=PROJECT_ROOT, capture_output=True, text=True,
        )
        if r1.returncode != 0:
            return False, r1.stderr[:400]
        r2 = sp.run(
            ["git", "push", "origin", "master"],
            cwd=PROJECT_ROOT, capture_output=True, text=True,
        )
        return r2.returncode == 0, r2.stderr[:400]

    success, err = await _run(_do_revert)
    if success:
        t["status"] = "open"
        t["git_commit_hash"] = ""
        t["agent_summary"] = ""
        t["completed_at"] = None
        t["smoke_test_passed"] = None
        _save_tickets_bot(db)
        await ctx.send(embed=_embed(
            f"↩️ {t['id']} Reverted",
            f"Commit `{commit_hash}` reverted and pushed to master.\n"
            f"Ticket reset to `open` — will be picked up on next dev agent run.",
        ))
        log("↩️", f"Bot: !revert {t['id']}", f"Reverted by {ctx.author}, commit={commit_hash}")
    else:
        await ctx.send(f"❌ Revert failed:\n```\n{err}\n```")


@bot.command(name="help")
async def cmd_help(ctx):
    """List all available commands."""
    await ctx.send(embed=_embed(
        "🤖 DaiTaos Commands",
        "`!brief` — full morning brief\n"
        "`!tsla` — TSLA bias (price, EMA 9, H/L, direction)\n"
        "`!watchlist` — watchlist scan table\n"
        "`!status` — agent crew + session status\n"
        "`!rules` — today's trading rules\n"
        "`!pnl` — journal edge summary (win rate, P&L, streak)\n"
        "`!config` — show current config\n"
        "`!config time HH:MM` — update brief send time\n"
        "`!config watchlist add SYMBOL` — add to watchlist\n"
        "`!config watchlist remove SYMBOL` — remove from watchlist\n"
        "——\n"
        "`!ticket status` — all tickets and statuses\n"
        "`!ticket pause` — pause dev agent\n"
        "`!ticket resume` — resume dev agent\n"
        "`!ticket log TICKET-XXX` — ticket execution log\n"
        "`!approve TICKET-XXX` — approve complex ticket\n"
        "`!revert TICKET-XXX` — revert a completed ticket\n"
        "`!help` — this message",
        footer="ClawOps · DaiTaos · Paper Mode"
    ))


if __name__ == "__main__":
    if not BOT_TOKEN:
        print("ERROR: DISCORD_BOT_TOKEN not set in .env")
        print("Create a bot at https://discord.com/developers/applications")
        print("Enable Message Content Intent in Bot settings, then add the token to .env")
        sys.exit(1)
    print("Starting DaiTaos bot…")
    bot.run(BOT_TOKEN)
