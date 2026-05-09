"""
main.py — FlatTrade API Ready-To-Use
=====================================
Master entry point. Run this file to access all features:

  1. Login (headless browser, gets your daily session token)
  2. Stock Data Manager (search, quotes, download, resample)
  3. Trading Panel (buy, sell, orders, positions, holdings)

Usage:
    python3 main.py
"""

import logging
import sys
import os

logging.basicConfig(level=logging.WARNING)

from api_helper import NorenApiPy
from config import USER_ID
from data_manager import run_data_menu
from trader import run_trader_menu

BANNER = f"""
{'*-'*40}
  🚀 FlatTrade API — Ready To Use
     Headless Login + Data + Trading
{'*-'*40}
"""

SESSION_FILE = ".session_token"


def load_session():
    """Load a saved session token from disk (valid for current trading day)."""
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE) as f:
            token = f.read().strip()
        if token:
            return token
    return None


def save_session(token):
    """Persist the session token so you don't need to re-login within the day."""
    with open(SESSION_FILE, 'w') as f:
        f.write(token)


def init_session(token):
    """Initialise the NorenApiPy session with a token."""
    api = NorenApiPy()
    api.set_session(userid=USER_ID, password='', usertoken=token)
    return api


def verify_token(api):
    """Quick check that the current token is still valid."""
    ret = api.get_limits()
    return ret and ret.get('stat') == 'Ok'


def main():
    print(BANNER)

    api   = None
    token = None

    # ── Try loading saved token first ─────────────────────────────────────────
    saved_token = load_session()
    if saved_token:
        print("  📂 Found saved session token. Verifying...")
        api = init_session(saved_token)
        if verify_token(api):
            token = saved_token
            print("  ✅ Session is valid! Skipping login.\n")
        else:
            print("  ⚠ Saved token is expired. Please login again.\n")
            api   = None
            token = None

    # ── Login if no valid session ─────────────────────────────────────────────
    if not token:
        print("  🔐 Starting headless login...\n")
        try:
            from token_generator.login import get_token
            token = get_token()
        except ImportError as e:
            print(f"  ❌ Playwright not installed: {e}")
            print("  Run: pip install playwright && python3 -m playwright install chromium")
            sys.exit(1)

        if not token:
            print("  ❌ Login failed. Exiting.")
            sys.exit(1)

        save_session(token)
        api = init_session(token)
        print("  ✅ Session saved. You won't need to login again today.\n")

    # ── Main menu ─────────────────────────────────────────────────────────────
    while True:
        print("  ┌─────────────────────────────────────────────┐")
        print("  │              Main Menu                      │")
        print("  ├─────────────────────────────────────────────┤")
        print("  │  1. Stock Data Manager                      │")
        print("  │     (search, quotes, download, resample)    │")
        print("  │  2. Trading Panel                           │")
        print("  │     (buy, sell, orders, positions)          │")
        print("  │  3. Account balance & limits                │")
        print("  │  4. Re-login (get new token)                │")
        print("  │  q. Quit                                    │")
        print("  └─────────────────────────────────────────────┘")
        choice = input("\n  Choice: ").strip().lower()

        if choice == '1':
            run_data_menu(api)

        elif choice == '2':
            run_trader_menu(api)

        elif choice == '3':
            from trader import get_account_limits
            get_account_limits(api)

        elif choice == '4':
            print("\n  🔐 Re-logging in...\n")
            from token_generator.login import get_token
            new_token = get_token()
            if new_token:
                token = new_token
                save_session(token)
                api = init_session(token)
                print("  ✅ New token saved!\n")
            else:
                print("  ❌ Login failed.\n")

        elif choice == 'q':
            print("\n  Bye! 👋\n")
            break
        else:
            print("  Invalid choice.\n")


if __name__ == "__main__":
    main()
