"""
app.py — Flask web application for Silent's trading dashboard.

Routes
------
GET  /              — Render full dashboard (server-side initial data)
GET  /api/market    — JSON: refresh market data (called every 5 min by JS)
POST /api/orb       — JSON: ORB setup calculation
POST /api/validate  — JSON: trade GO/NO-GO validation
POST /api/risk      — JSON: position-size and risk metrics
GET  /api/journal   — JSON: last 10 entries + stats
POST /api/journal   — JSON: save a new journal entry
"""

import sys
import os

# Make the project root importable when running from dashboard/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify

from agent.market_data     import get_all_market_data, get_sparklines, get_news
from agent.orb_calculator  import calculate_orb
from agent.risk_calculator import calculate_risk, validate_trade
from agent.journal_manager import save_entry, get_entries, get_stats

# template_folder is relative to this file's directory (dashboard/)
app = Flask(__name__, template_folder='templates')


# ─── Main page ───────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """
    Render the dashboard on first load.
    Market data and journal stats are fetched server-side so the page isn't
    blank while the browser's first AJAX call completes.
    """
    try:
        market = get_all_market_data()
    except Exception as e:
        # If yfinance is completely unreachable, show empty placeholders
        market = {
            'tickers':      {t: {'error': str(e)} for t in ['QQQ', 'TSLA', 'MSFT', 'AMZN']},
            'spy':          {'bias': 'N/A', 'bias_class': 'neutral', 'spy_pct': 0},
            'market_times': {
                'today': 'Unavailable', 'current_time': '--',
                'market_open': '--', 'market_close': '--',
                'market_status': 'UNKNOWN', 'is_open': False, 'is_premarket': False,
            },
        }

    journal_entries = get_entries(10)
    journal_stats   = get_stats()

    return render_template(
        'index.html',
        tickers = market['tickers'],
        spy     = market['spy'],
        times   = market['market_times'],
        entries = journal_entries,
        stats   = journal_stats,
    )


# ─── API: Market data refresh ────────────────────────────────────────────────

@app.route('/api/market')
def api_market():
    """Called by the JS auto-refresh every 5 minutes."""
    try:
        return jsonify(get_all_market_data())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── API: ORB Planner ────────────────────────────────────────────────────────

@app.route('/api/orb', methods=['POST'])
def api_orb():
    """Calculate ORB levels. Expects JSON body with ticker, high, low, account_size, risk_pct."""
    data = request.get_json(force=True) or {}
    try:
        result = calculate_orb(
            ticker       = data.get('ticker', 'TSLA'),
            high         = float(data.get('high', 0)),
            low          = float(data.get('low', 0)),
            account_size = float(data.get('account_size', 1000)),
            risk_pct     = float(data.get('risk_pct', 1.0)),
        )
        return jsonify(result)
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid input: {e}'}), 400


# ─── API: Trade Validator ────────────────────────────────────────────────────

@app.route('/api/validate', methods=['POST'])
def api_validate():
    """
    Validate a proposed trade. Returns GO or NO-GO with reasons.

    Stop loss is a hard requirement — the backend enforces this in addition
    to the client-side JS check so it can never be bypassed.
    """
    data = request.get_json(force=True) or {}

    stop_raw = data.get('stop', '')
    if not str(stop_raw).strip():
        return jsonify({
            'error':       'Stop loss is required. Define your stop before entering.',
            'go_nogo':     'NO-GO',
            'go_class':    'nogo',
            'rr_ratio':    0,
            'dollar_risk': None,
            'warnings':    ['No stop loss defined.'],
            'meets_rules': False,
        })

    try:
        entry        = float(data.get('entry', 0))
        stop         = float(stop_raw)
        target       = float(data.get('target', 0))
        account_size = float(data.get('account_size', 0) or 0)

        result = validate_trade(entry, stop, target, account_size)
        # Echo back the trade metadata the UI needs
        result['ticker']     = data.get('ticker', '').upper()
        result['setup']      = data.get('setup', '')
        result['trade_type'] = data.get('trade_type', 'Paper')
        return jsonify(result)

    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid input: {e}'}), 400


# ─── API: Risk Calculator ────────────────────────────────────────────────────

@app.route('/api/risk', methods=['POST'])
def api_risk():
    """Calculate position size and risk metrics."""
    data = request.get_json(force=True) or {}
    try:
        result = calculate_risk(
            account_size = float(data.get('account_size', 1000)),
            risk_pct     = float(data.get('risk_pct', 1.0)),
            entry_price  = float(data.get('entry_price', 0)),
            stop_price   = float(data.get('stop_price', 0)),
        )
        return jsonify(result)
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid input: {e}'}), 400


# ─── API: Trade Journal ──────────────────────────────────────────────────────

@app.route('/api/journal', methods=['GET'])
def api_journal_get():
    """Return last 10 entries and stats as JSON (for JS table refresh)."""
    return jsonify({
        'entries': get_entries(10),
        'stats':   get_stats(),
    })


@app.route('/api/journal', methods=['POST'])
def api_journal_post():
    """Save a new journal entry and confirm."""
    data = request.get_json(force=True) or {}
    try:
        save_entry(data)
        return jsonify({'success': True, 'message': 'Trade logged successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ─── API: News ───────────────────────────────────────────────────────────────

@app.route('/api/news')
def api_news():
    """Fetch recent news headlines for all watchlist tickers."""
    try:
        return jsonify(get_news())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── API: Sparklines ─────────────────────────────────────────────────────────

@app.route('/api/sparkline')
def api_sparkline():
    """Return last 5 closing prices per ticker for watchlist sparklines."""
    try:
        return jsonify(get_sparklines())
    except Exception as e:
        return jsonify({'error': str(e)}), 500
