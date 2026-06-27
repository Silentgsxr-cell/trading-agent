"""
app.py — Flask web application for Silent's trading dashboard.

Routes
------
GET  /               — Dashboard page (server-side seed data)
GET  /api/market     — Market prices + bias + clock (every 5 min)
POST /api/orb        — ORB level calculation
POST /api/validate   — Trade GO/NO-GO validation
POST /api/risk       — Position-size + risk metrics
GET  /api/journal    — Last 10 journal entries + stats
POST /api/journal    — Save a new journal entry
GET  /api/news       — Recent news for watchlist tickers
GET  /api/sparkline  — 5-bar sparkline data per ticker
GET  /api/status     — Live risk engine session state
POST /api/status/halt   — Manual kill switch (halt all new entries)
POST /api/status/reset  — Reset session for a new trading day
"""

import sys
import os
import json

_HERE = os.path.dirname(os.path.abspath(__file__))   # dashboard/
_ROOT = os.path.dirname(_HERE)                        # project root
sys.path.insert(0, _ROOT)   # resolves: from agents.* / config.* import ...
sys.path.insert(0, _HERE)   # resolves: from agent.* import ... (must be first to shadow root agent/)

from flask import Flask, render_template, request, jsonify

from agent.market_data     import get_all_market_data, get_sparklines, get_news
from agent.orb_calculator  import calculate_orb
from agent.risk_calculator import calculate_risk, validate_trade
from agent.journal_manager import save_entry, get_entries, get_stats
import agent.notifier as notify

from agents.risk_engine import RiskEngine
from config import risk_config as cfg
from agent.backtester      import run_backtest
import utils.state_manager as state_mgr

app = Flask(__name__, template_folder='templates')

# Single RiskEngine instance for the life of this process.
# Holds session state: trades opened today, consecutive losses, halted flag.
_engine = RiskEngine()


# ─── Main page ───────────────────────────────────────────────────────────────

@app.route('/')
def index():
    try:
        market = get_all_market_data()
    except Exception as e:
        market = {
            'tickers': {t: {'error': str(e)} for t in ['QQQ', 'TSLA', 'MSFT', 'AMZN']},
            'spy': {'bias': 'N/A', 'bias_class': 'neutral', 'spy_pct': 0},
            'market_times': {
                'today': 'Unavailable', 'current_time': '--',
                'market_open': '--', 'market_close': '--',
                'market_status': 'UNKNOWN', 'is_open': False, 'is_premarket': False,
            },
        }
    return render_template(
        'index.html',
        tickers = market['tickers'],
        spy     = market['spy'],
        times   = market['market_times'],
        entries = get_entries(10),
        stats   = get_stats(),
    )


# ─── Market data ─────────────────────────────────────────────────────────────

@app.route('/api/market')
def api_market():
    try:
        return jsonify(get_all_market_data())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── ORB Planner ─────────────────────────────────────────────────────────────

@app.route('/api/orb', methods=['POST'])
def api_orb():
    data = request.get_json(force=True) or {}
    try:
        return jsonify(calculate_orb(
            ticker       = data.get('ticker', 'TSLA'),
            high         = float(data.get('high', 0)),
            low          = float(data.get('low', 0)),
            account_size = float(data.get('account_size', 1000)),
            risk_pct     = float(data.get('risk_pct', 1.0)),
        ))
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid input: {e}'}), 400


# ─── Trade Validator ─────────────────────────────────────────────────────────

@app.route('/api/validate', methods=['POST'])
def api_validate():
    data     = request.get_json(force=True) or {}
    stop_raw = data.get('stop', '')
    if not str(stop_raw).strip():
        return jsonify({
            'error': 'Stop loss is required.',
            'go_nogo': 'NO-GO', 'go_class': 'nogo',
            'rr_ratio': 0, 'dollar_risk': None,
            'warnings': ['No stop loss defined.'], 'meets_rules': False,
        })
    try:
        result = validate_trade(
            entry        = float(data.get('entry', 0)),
            stop         = float(stop_raw),
            target       = float(data.get('target', 0)),
            account_size = float(data.get('account_size', 0) or 0),
        )
        result['ticker']     = data.get('ticker', '').upper()
        result['setup']      = data.get('setup', '')
        result['trade_type'] = data.get('trade_type', 'Paper')
        notify.trade_validated(
            ticker=result['ticker'], setup=result['setup'],
            go_nogo=result['go_nogo'], rr_ratio=result['rr_ratio'],
            dollar_risk=result['dollar_risk'],
        )
        return jsonify(result)
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid input: {e}'}), 400


# ─── Risk Calculator ─────────────────────────────────────────────────────────

@app.route('/api/risk', methods=['POST'])
def api_risk():
    data = request.get_json(force=True) or {}
    try:
        return jsonify(calculate_risk(
            account_size = float(data.get('account_size', 1000)),
            risk_pct     = float(data.get('risk_pct', 1.0)),
            entry_price  = float(data.get('entry_price', 0)),
            stop_price   = float(data.get('stop_price', 0)),
        ))
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid input: {e}'}), 400


# ─── Journal ─────────────────────────────────────────────────────────────────

@app.route('/api/journal', methods=['GET'])
def api_journal_get():
    return jsonify({'entries': get_entries(10), 'stats': get_stats()})


@app.route('/api/journal', methods=['POST'])
def api_journal_post():
    data = request.get_json(force=True) or {}
    try:
        save_entry(data)
        notify.trade_logged(
            ticker=data.get('ticker', ''),
            strategy=data.get('strategy', ''),
            pnl=data.get('pnl', ''),
        )
        return jsonify({'success': True, 'message': 'Trade logged successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ─── News ────────────────────────────────────────────────────────────────────

@app.route('/api/news')
def api_news():
    try:
        return jsonify(get_news())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── Sparklines ──────────────────────────────────────────────────────────────

@app.route('/api/sparkline')
def api_sparkline():
    try:
        return jsonify(get_sparklines())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── System / VAULT Status ────────────────────────────────────────────────────

@app.route('/api/status')
def api_status():
    # Prefer runner state (state_manager) when runner is online; fall back to
    # the in-process engine so the Flask terminal works standalone too.
    shared = state_mgr.get_session()
    runner_online = shared.get("runnerOnline", False)
    if runner_online:
        return jsonify({
            'halted':              shared.get('halted', False),
            'halt_reason':         shared.get('haltReason'),
            'trades_opened_today': shared.get('tradesToday', 0),
            'trades_remaining':    max(0, cfg.MAX_TRADES_PER_DAY - shared.get('tradesToday', 0)),
            'consecutive_losses':  shared.get('consecutiveLosses', 0),
            'daily_pnl':           shared.get('dailyPnl', 0.0),
            'open_positions':      shared.get('openPositions', 0),
            'max_trades':          cfg.MAX_TRADES_PER_DAY,
            'max_daily_loss_pct':  cfg.DAILY_MAX_LOSS_PCT * 100,
            'cooldown_threshold':  cfg.CONSECUTIVE_LOSS_COOLDOWN,
            'source':              'runner',
        })
    # Runner offline — fall back to in-process engine (Flask terminal standalone mode)
    s = _engine.session
    return jsonify({
        'halted':              s.halted,
        'halt_reason':         s.halt_reason,
        'trades_opened_today': s.trades_opened_today,
        'trades_remaining':    max(0, cfg.MAX_TRADES_PER_DAY - s.trades_opened_today),
        'consecutive_losses':  s.consecutive_losses,
        'daily_pnl':           round(s.daily_pnl, 2),
        'open_positions':      len(s.open_positions),
        'max_trades':          cfg.MAX_TRADES_PER_DAY,
        'max_daily_loss_pct':  cfg.DAILY_MAX_LOSS_PCT * 100,
        'cooldown_threshold':  cfg.CONSECUTIVE_LOSS_COOLDOWN,
        'source':              'flask',
    })


@app.route('/api/status/halt', methods=['POST'])
def api_status_halt():
    _engine._halt("manual kill switch")
    state_mgr.halt_session("manual kill switch")
    notify.session_halted("manual kill switch")
    return jsonify({'success': True, 'message': 'Session halted.'})


@app.route('/api/status/reset', methods=['POST'])
def api_status_reset():
    global _engine
    _engine = RiskEngine()
    state_mgr.reset_session(cfg.STARTING_BALANCE)
    notify.session_reset()
    return jsonify({'success': True, 'message': 'Session reset — new trading day.'})


# ─── API: Backtest ───────────────────────────────────────────────────────────

@app.route('/api/backtest', methods=['POST'])
def api_backtest():
    data = request.get_json(force=True) or {}
    try:
        result = run_backtest(
            ticker       = data.get('ticker', 'TSLA'),
            trading_days = int(data.get('days', 30)),
            account_size = float(data.get('account_size', 1000)),
            risk_pct     = float(data.get('risk_pct', 1.0)),
            target_r     = float(data.get('target_r', 2.0)),
        )
        return jsonify(result)
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid input: {e}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── API: Dev Agent Tickets ───────────────────────────────────────────────────

import datetime as _dt

TICKETS_FILE = os.path.join(_ROOT, "data", "tickets.json")

TICKET_BLOCKED_PATHS = [
    "agents/", "config/", "tests/", ".env",
    "utils/watchdog.py", "utils/state_manager.py",
    "utils/journal_writer.py", "utils/event_log.py",
]

TICKET_DEFAULTS = {
    "started_at": None, "completed_at": None,
    "files_read": [], "files_modified": [], "files_created": [],
    "git_branch": "", "git_commit_hash": "", "agent_summary": "",
    "smoke_test_passed": None, "log": [],
}


def _load_ticket_db() -> dict:
    if not os.path.exists(TICKETS_FILE):
        return {"paused": False, "tickets": []}
    with open(TICKETS_FILE) as f:
        return json.load(f)


def _save_ticket_db(db: dict) -> None:
    with open(TICKETS_FILE, "w") as f:
        json.dump(db, f, indent=2, default=str)


def _next_ticket_id(tickets: list) -> str:
    nums = []
    for t in tickets:
        m = __import__("re").match(r"TICKET-(\d+)", t.get("id", ""))
        if m:
            nums.append(int(m.group(1)))
    n = max(nums, default=0) + 1
    return f"TICKET-{n:03d}"


@app.route('/api/tickets', methods=['GET'])
def api_tickets_get():
    try:
        return jsonify(_load_ticket_db())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tickets', methods=['POST'])
def api_tickets_post():
    data = request.get_json(force=True) or {}
    try:
        db = _load_ticket_db()

        # Validate no blocked paths in allowed_paths
        allowed = data.get('allowed_paths', [])
        for ap in allowed:
            for bp in TICKET_BLOCKED_PATHS:
                if ap.startswith(bp) or bp.startswith(ap.rstrip('/')):
                    return jsonify({'error': f"allowed_path '{ap}' overlaps blocked path '{bp}'"}), 400

        ticket = {
            **TICKET_DEFAULTS,
            "id":                _next_ticket_id(db["tickets"]),
            "title":             str(data.get("title", "")).strip(),
            "description":       str(data.get("description", "")).strip(),
            "what_to_complete":  str(data.get("what_to_complete", "")).strip(),
            "what_done_looks_like": str(data.get("what_done_looks_like", "")).strip(),
            "connectors_needed": data.get("connectors_needed", []),
            "restrictions":      data.get("restrictions", []),
            "allowed_paths":     allowed,
            "blocked_paths":     data.get("blocked_paths", TICKET_BLOCKED_PATHS),
            "priority":          data.get("priority", "medium"),
            "complexity":        data.get("complexity", "simple"),
            "complexity_color":  data.get("complexity_color", "#00e676"),
            "status":            "open",
            "created_at":        _dt.datetime.now().isoformat(),
            "approval_gate":     data.get("approval_gate", "auto"),
        }

        if not ticket["title"]:
            return jsonify({'error': 'title is required'}), 400

        db["tickets"].append(ticket)
        _save_ticket_db(db)
        return jsonify({'success': True, 'ticket': ticket}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tickets/<ticket_id>', methods=['GET'])
def api_ticket_get(ticket_id: str):
    try:
        db = _load_ticket_db()
        tid = ticket_id.upper()
        t = next((t for t in db["tickets"] if t["id"].upper() == tid), None)
        if t is None:
            return jsonify({'error': f'Ticket {ticket_id} not found'}), 404
        return jsonify(t)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tickets/<ticket_id>/approve', methods=['POST'])
def api_ticket_approve(ticket_id: str):
    try:
        db = _load_ticket_db()
        tid = ticket_id.upper()
        t = next((t for t in db["tickets"] if t["id"].upper() == tid), None)
        if t is None:
            return jsonify({'error': f'Ticket {ticket_id} not found'}), 404
        if t['status'] not in ('needs_review', 'open'):
            return jsonify({'error': f"Ticket is '{t['status']}', not needs_review"}), 400
        t['status'] = 'open'
        t['approval_gate'] = 'approved'
        _save_ticket_db(db)
        return jsonify({'success': True, 'ticket': t})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tickets/<ticket_id>/revert', methods=['POST'])
def api_ticket_revert(ticket_id: str):
    import subprocess as _sp
    try:
        db = _load_ticket_db()
        tid = ticket_id.upper()
        t = next((t for t in db["tickets"] if t["id"].upper() == tid), None)
        if t is None:
            return jsonify({'error': f'Ticket {ticket_id} not found'}), 404
        if t['status'] != 'done':
            return jsonify({'error': 'Only done tickets can be reverted'}), 400
        commit_hash = t.get('git_commit_hash', '')
        if not commit_hash:
            return jsonify({'error': 'No commit hash recorded for this ticket'}), 400

        r1 = _sp.run(['git', 'revert', '--no-edit', commit_hash],
                     cwd=_ROOT, capture_output=True, text=True)
        if r1.returncode != 0:
            return jsonify({'error': f'git revert failed: {r1.stderr[:400]}'}), 500

        r2 = _sp.run(['git', 'push', 'origin', 'master'],
                     cwd=_ROOT, capture_output=True, text=True)
        if r2.returncode != 0:
            return jsonify({'error': f'git push failed: {r2.stderr[:400]}'}), 500

        t['status'] = 'open'
        t['git_commit_hash'] = ''
        t['agent_summary'] = ''
        t['completed_at'] = None
        t['smoke_test_passed'] = None
        _save_ticket_db(db)
        return jsonify({'success': True, 'ticket': t})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── API: Suggestions ────────────────────────────────────────────────────────

SUGGESTIONS_FILE = os.path.join(_ROOT, "data", "suggestions.json")


def _load_suggestions() -> list:
    if not os.path.exists(SUGGESTIONS_FILE):
        return []
    with open(SUGGESTIONS_FILE) as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _save_suggestions(cards: list) -> None:
    with open(SUGGESTIONS_FILE, "w") as f:
        json.dump(cards, f, indent=2, default=str)


def _next_sug_id(cards: list) -> str:
    import re as _re
    nums = [int(m.group(1)) for c in cards for m in [_re.match(r"SUG-(\d+)", c.get("id", ""))] if m]
    return f"SUG-{max(nums, default=0) + 1:03d}"


@app.route('/api/suggestions', methods=['GET'])
def api_suggestions_get():
    try:
        return jsonify(_load_suggestions())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/suggestions', methods=['POST'])
def api_suggestions_post():
    data = request.get_json(force=True) or {}
    try:
        cards = _load_suggestions()
        now = _dt.datetime.now().isoformat()
        card = {
            "id":              _next_sug_id(cards),
            "agent_id":        str(data.get("agent_id", "UNKNOWN")).upper(),
            "agent_color":     str(data.get("agent_color", "#5b6680")),
            "agent_avatar":    str(data.get("agent_avatar", "circle")),
            "title":           str(data.get("title", "")).strip(),
            "reasoning":       str(data.get("reasoning", "")).strip(),
            "category":        str(data.get("category", "UI")),
            "priority":        int(data.get("priority", 5)),
            "flags":           list(data.get("flags", [])),
            "flag_emojis":     str(data.get("flag_emojis", "")),
            "affected_files":  list(data.get("affected_files", [])),
            "has_locked_files": bool(data.get("has_locked_files", False)),
            "status":          "open",
            "queue":           None,
            "completed_by":    None,
            "archive_reason":  "",
            "progress_pct":    0,
            "dev_ticket_id":   None,
            "user_edits":      "",
            "created_at":      now,
            "updated_at":      now,
            "archived_at":     None,
            "discord_posted":  bool(data.get("discord_posted", False)),
            "cycle_id":        str(data.get("cycle_id", "")),
        }
        if not card["title"]:
            return jsonify({'error': 'title is required'}), 400
        cards.append(card)
        _save_suggestions(cards)
        return jsonify({'success': True, 'suggestion': card}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/suggestions/<sug_id>', methods=['PATCH'])
def api_suggestion_patch(sug_id: str):
    data = request.get_json(force=True) or {}
    try:
        cards = _load_suggestions()
        sid = sug_id.upper()
        card = next((c for c in cards if c.get("id", "").upper() == sid), None)
        if card is None:
            return jsonify({'error': f'{sug_id} not found'}), 404
        # Updateable fields only — status/queue changes go through dedicated routes
        for field in ("title", "reasoning", "user_edits", "progress_pct"):
            if field in data:
                card[field] = data[field]
        card["updated_at"] = _dt.datetime.now().isoformat()
        _save_suggestions(cards)
        return jsonify({'success': True, 'suggestion': card})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/suggestions/<sug_id>/approve-dev', methods=['POST'])
def api_suggestion_approve_dev(sug_id: str):
    """Create a dev ticket from the suggestion and move it to dev_queue."""
    data = request.get_json(force=True) or {}
    try:
        cards  = _load_suggestions()
        sid    = sug_id.upper()
        card   = next((c for c in cards if c.get("id", "").upper() == sid), None)
        if card is None:
            return jsonify({'error': f'{sug_id} not found'}), 404
        if card['status'] not in ('open',):
            return jsonify({'error': f"Suggestion is '{card['status']}', cannot approve"}), 400

        # Create a dev ticket from this suggestion
        db = _load_ticket_db()
        allowed = card.get("affected_files", [])
        ticket = {
            **TICKET_DEFAULTS,
            "id":                _next_ticket_id(db["tickets"]),
            "title":             card["title"],
            "description":       card["reasoning"],
            "what_to_complete":  card.get("user_edits") or card["reasoning"],
            "what_done_looks_like": f"Suggestion {card['id']} implemented",
            "connectors_needed": [],
            "restrictions":      [],
            "allowed_paths":     allowed,
            "blocked_paths":     TICKET_BLOCKED_PATHS,
            "priority":          "high" if card["priority"] >= 8 else "medium",
            "complexity":        "complex" if card["has_locked_files"] else "simple",
            "complexity_color":  "#ff5252" if card["has_locked_files"] else "#00e676",
            "status":            "open",
            "created_at":        _dt.datetime.now().isoformat(),
            "approval_gate":     "auto",
            "source_suggestion": card["id"],
        }
        db["tickets"].append(ticket)
        _save_ticket_db(db)

        card["status"]        = "dev_queue"
        card["queue"]         = "dev"
        card["dev_ticket_id"] = ticket["id"]
        card["updated_at"]    = _dt.datetime.now().isoformat()
        _save_suggestions(cards)
        return jsonify({'success': True, 'suggestion': card, 'ticket': ticket})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/suggestions/<sug_id>/approve-silent', methods=['POST'])
def api_suggestion_approve_silent(sug_id: str):
    try:
        cards = _load_suggestions()
        sid   = sug_id.upper()
        card  = next((c for c in cards if c.get("id", "").upper() == sid), None)
        if card is None:
            return jsonify({'error': f'{sug_id} not found'}), 404
        card["status"]     = "silent_queue"
        card["queue"]      = "silent"
        card["updated_at"] = _dt.datetime.now().isoformat()
        _save_suggestions(cards)
        return jsonify({'success': True, 'suggestion': card})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/suggestions/<sug_id>/discard', methods=['POST'])
def api_suggestion_discard(sug_id: str):
    data = request.get_json(force=True) or {}
    archive_reason = str(data.get("archive_reason", "")).strip()
    if not archive_reason:
        return jsonify({'error': 'archive_reason is required when discarding'}), 400
    try:
        cards = _load_suggestions()
        sid   = sug_id.upper()
        card  = next((c for c in cards if c.get("id", "").upper() == sid), None)
        if card is None:
            return jsonify({'error': f'{sug_id} not found'}), 404
        card["status"]         = "discarded"
        card["archive_reason"] = archive_reason
        card["archived_at"]    = _dt.datetime.now().isoformat()
        card["updated_at"]     = _dt.datetime.now().isoformat()
        _save_suggestions(cards)
        return jsonify({'success': True, 'suggestion': card})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/suggestions/stats', methods=['GET'])
def api_suggestions_stats():
    try:
        cards = _load_suggestions()
        by_status: dict = {}
        by_agent:  dict = {}
        unreviewed = 0
        for c in cards:
            s = c.get("status", "open")
            by_status[s] = by_status.get(s, 0) + 1
            a = c.get("agent_id", "UNKNOWN")
            by_agent[a]  = by_agent.get(a, 0) + 1
            if s == "open":
                unreviewed += 1
        return jsonify({
            "total":      len(cards),
            "unreviewed": unreviewed,
            "by_status":  by_status,
            "by_agent":   by_agent,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── API: Tab Analytics ───────────────────────────────────────────────────────

TAB_USAGE_FILE = os.path.join(_ROOT, "data", "tab_usage.json")


def _load_tab_usage() -> dict:
    if not os.path.exists(TAB_USAGE_FILE):
        return {"tab_counts": {}, "last_updated": "", "sessions": []}
    with open(TAB_USAGE_FILE) as f:
        return json.load(f)


def _save_tab_usage(data: dict) -> None:
    with open(TAB_USAGE_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


@app.route('/api/analytics/tab', methods=['POST'])
def api_analytics_tab():
    body = request.get_json(force=True) or {}
    tab  = str(body.get("tab", "")).strip()
    if not tab:
        return jsonify({'error': 'tab is required'}), 400
    try:
        usage = _load_tab_usage()
        usage["tab_counts"][tab] = usage["tab_counts"].get(tab, 0) + 1
        usage["last_updated"]    = _dt.datetime.now().isoformat()
        session_entry = {
            "tab":         tab,
            "timestamp":   str(body.get("timestamp", _dt.datetime.now().isoformat())),
            "duration_ms": int(body.get("duration_ms", 0)),
        }
        usage["sessions"] = usage["sessions"][-999:] + [session_entry]
        _save_tab_usage(usage)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/tabs', methods=['GET'])
def api_analytics_tabs():
    try:
        return jsonify(_load_tab_usage())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── API: Life Tab ────────────────────────────────────────────────────────────

import subprocess as _sub

GOALS_FILE = os.path.join(_ROOT, "data", "goals.json")


def _load_goals() -> list:
    if not os.path.exists(GOALS_FILE):
        return []
    with open(GOALS_FILE) as f:
        return json.load(f)


def _save_goals(goals: list) -> None:
    with open(GOALS_FILE, "w") as f:
        json.dump(goals, f, indent=2, default=str)


@app.route('/api/life/calendar')
def api_life_calendar():
    script = r'''
tell application "Calendar"
    set startDate to current date
    set endDate to startDate + (7 * days)
    set output to ""
    repeat with cal in calendars
        set calName to name of cal
        try
            set evts to every event of cal whose start date >= startDate and start date <= endDate
            repeat with evt in evts
                try
                    set evtTitle to summary of evt
                    set evtStart to (start date of evt) as string
                    set evtEnd to (end date of evt) as string
                    set allD to "false"
                    try
                        if allday event of evt then set allD to "true"
                    end try
                    set output to output & calName & "||" & evtTitle & "||" & evtStart & "||" & evtEnd & "||" & allD & "
"
                end try
            end repeat
        end try
    end repeat
    return output
end tell
'''
    try:
        r = _sub.run(['osascript', '-e', script], capture_output=True, text=True, timeout=12)
        events = []
        for line in r.stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = line.split('||')
            if len(parts) >= 4:
                events.append({
                    'calendar': parts[0].strip(),
                    'title':    parts[1].strip(),
                    'start':    parts[2].strip(),
                    'end':      parts[3].strip(),
                    'allDay':   len(parts) > 4 and parts[4].strip() == 'true',
                })
        events.sort(key=lambda e: e['start'])
        return jsonify({'events': events, 'error': r.stderr.strip() or None})
    except Exception as e:
        return jsonify({'events': [], 'error': str(e)}), 200


@app.route('/api/life/tasks')
def api_life_tasks():
    script = r'''
tell application "Reminders"
    set output to ""
    try
        set allLists to every list
        repeat with rl in allLists
            set listName to name of rl
            try
                set rems to every reminder of rl whose completed is false
                repeat with r in rems
                    set rTitle to name of r
                    set rDue to ""
                    try
                        set rDue to (due date of r) as string
                    end try
                    set output to output & listName & "||" & rTitle & "||" & rDue & "
"
                end repeat
            end try
        end repeat
    end try
    return output
end tell
'''
    try:
        r = _sub.run(['osascript', '-e', script], capture_output=True, text=True, timeout=12)
        tasks = []
        for line in r.stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = line.split('||')
            if len(parts) >= 2:
                tasks.append({
                    'list':  parts[0].strip(),
                    'title': parts[1].strip(),
                    'due':   parts[2].strip() if len(parts) > 2 else '',
                })
        return jsonify({'tasks': tasks, 'error': r.stderr.strip() or None})
    except Exception as e:
        return jsonify({'tasks': [], 'error': str(e)}), 200


@app.route('/api/life/goals', methods=['GET'])
def api_life_goals_get():
    try:
        return jsonify(_load_goals())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/life/goals', methods=['POST'])
def api_life_goals_post():
    data = request.get_json(force=True) or {}
    try:
        goals = _load_goals()
        import re as _re2
        nums = [int(m.group(1)) for g in goals for m in [_re2.match(r'GOAL-(\d+)', g.get('id', ''))] if m]
        new_id = f"GOAL-{max(nums, default=0) + 1:03d}"
        goal = {
            "id":           new_id,
            "title":        str(data.get("title", "")).strip(),
            "notes":        str(data.get("notes", "")).strip(),
            "target_date":  str(data.get("target_date", "")).strip(),
            "status":       "active",
            "created_at":   _dt.datetime.now().isoformat(),
            "completed_at": None,
        }
        if not goal["title"]:
            return jsonify({"error": "title required"}), 400
        goals.append(goal)
        _save_goals(goals)
        return jsonify({"success": True, "goal": goal}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/life/goals/<goal_id>', methods=['PATCH'])
def api_life_goals_patch(goal_id: str):
    data = request.get_json(force=True) or {}
    try:
        goals = _load_goals()
        g = next((g for g in goals if g["id"].upper() == goal_id.upper()), None)
        if g is None:
            return jsonify({"error": "not found"}), 404
        for field in ("title", "notes", "target_date", "status"):
            if field in data:
                g[field] = data[field]
        if data.get("status") == "done" and not g.get("completed_at"):
            g["completed_at"] = _dt.datetime.now().isoformat()
        elif data.get("status") == "active":
            g["completed_at"] = None
        _save_goals(goals)
        return jsonify({"success": True, "goal": g})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/life/goals/<goal_id>', methods=['DELETE'])
def api_life_goals_delete(goal_id: str):
    try:
        goals = _load_goals()
        gid = goal_id.upper()
        goals = [g for g in goals if g["id"].upper() != gid]
        _save_goals(goals)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/life/finance')
def api_life_finance():
    finance_json = os.path.join(_ROOT, "data", "finance.json")
    try:
        if os.path.exists(finance_json):
            with open(finance_json) as f:
                fin = json.load(f)
        else:
            fin = {"accounts": [], "debts": [], "budget": {"month": "", "categories": []}}
        total_assets = sum(a.get("balance", 0) for a in fin.get("accounts", []))
        total_debt   = sum(d.get("balance", 0) for d in fin.get("debts", []))
        net_worth    = round(total_assets - total_debt, 2)
        return jsonify({
            "accounts":     fin.get("accounts", []),
            "debts":        fin.get("debts", []),
            "total_assets": round(total_assets, 2),
            "total_debt":   round(total_debt, 2),
            "net_worth":    net_worth,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
