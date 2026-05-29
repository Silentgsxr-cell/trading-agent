"""
run.py — Start the trading dashboard.

Usage:
  python run.py

Then open http://localhost:5000 in your browser.

The server runs in debug mode by default so it auto-reloads when you
edit any Python file. Turn debug=False for a more stable session.
"""

import os
import sys

# Make sure the project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()  # Loads any keys you add to .env in the future

from dashboard.app import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n  Trading Dashboard → http://localhost:{port}\n")
    app.run(debug=True, port=port, host='127.0.0.1')
