"""
DaiTaos — Daily Intelligence Agent.

Role: Morning briefing officer and information filter.
This is the first thing you look at every day.

DaiTaos owns:
  - Daily Brief (sent to Discord at 6:20 AM AZ via utils/daitaos.py)
  - Discord bot commands (!brief, !tsla, !watchlist, !status, !rules, !pnl)
  - Overnight news and premarket summary
  - Economic calendar highlights
  - Agent crew status highlights
  - Watchlist scan with movers flagged

Questions DaiTaos answers every morning:
  - What happened overnight?
  - What does the tape look like for TSLA?
  - Which watchlist names are moving?
  - What is SPY/QQQ bias right now?
  - What are my rules today?
  - How is my journal looking?

Output format (Discord embeds):
  Section 1 — Date & Market Status
  Section 2 — TSLA Direction Bias (premarket price, EMA 9, prior H/L)
  Section 3 — Watchlist Scan (10-symbol table, movers flagged ≥ ±1.5%)
  Section 4 — SPY Market Bias (RISK ON / RISK OFF / NEUTRAL)
  Section 5 — Today's Trading Rules (from risk_config.py — live values)
  Section 6 — Agent & Session Status (engine state, trades remaining)
  Section 7 — Journal Edge Summary (win rate, P&L, streak)
  Section 8 — Edge Reminder

Data sources (read-only):
  - yfinance — premarket prices, EMA, prior day H/L
  - state/session.json — engine status, P&L, trades today
  - data/journal.csv — win rate, streak
  - config/risk_config.py — rules (daily loss limit, max trades, etc.)
  - data/daitaos_config.json — watchlist, send time

Implementation: utils/daitaos.py (brief) + utils/daitaos_bot.py (Discord bot)
Discord token: DISCORD_BOT_TOKEN in .env
Discord webhook: DISCORD_WEBHOOK_URL in .env

Scheduled: 6:20 AM AZ via launchd (com.silent.dataos.plist)
Bot: runs continuously via com.silent.dataos.bot.plist
"""


class DaiTaos:
    """
    DaiTaos is implemented as a scheduled script + Discord bot (utils/).
    This class exists for Mission Control crew registration and documentation.

    To send the brief manually:
        python3 utils/daitaos.py

    To run the interactive bot:
        python3 utils/daitaos_bot.py
    """
    pass
