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


# ─── System / Risk Engine Status ─────────────────────────────────────────────

@app.route('/api/status')
def api_status():
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
    })


@app.route('/api/status/halt', methods=['POST'])
def api_status_halt():
    _engine._halt("manual kill switch")
    notify.session_halted("manual kill switch")
    return jsonify({'success': True, 'message': 'Session halted.'})


@app.route('/api/status/reset', methods=['POST'])
def api_status_reset():
    global _engine
    _engine = RiskEngine()
    notify.session_reset()
    return jsonify({'success': True, 'message': 'Session reset — new trading day.'})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
