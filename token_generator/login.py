"""
login.py — Headless Flattrade Authentication
=============================================
Automates the full Flattrade login flow using Playwright:
  1. Opens auth URL in a hidden Chromium browser
  2. Fills User ID and Password
  3. Clicks "Get OTP" link → fills popup User ID + PAN
  4. Waits for user to enter the OTP from their phone
  5. Logs in, captures the redirect code, exchanges it for a token

Screenshots are saved at each key step to: screenshots/
These help debug if the login flow ever breaks.

Usage:
    from login import get_token
    token = get_token()   # returns token string on success, None on failure
"""

import hashlib
import requests
import socket
import time
import getpass
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright
from config import API_KEY, API_SECRET, USER_ID, SCREENSHOT_DIR

# ── Force IPv4 so Flattrade sees your registered IPv4 address ──────────────────
# (servers with IPv6 would otherwise send requests from an IPv6 address that
#  Flattrade doesn't recognise, causing INVALID_IP errors)
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_only
# ───────────────────────────────────────────────────────────────────────────────

os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def _generate_hash(api_key, request_token, api_secret):
    raw = f"{api_key}{request_token}{api_secret}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _exchange_code_for_token(request_code):
    """POST to Flattrade API to exchange auth code for session token."""
    hashed = _generate_hash(API_KEY, request_code, API_SECRET)
    payload = {"api_key": API_KEY, "request_code": request_code, "api_secret": hashed}
    try:
        resp = requests.post("https://authapi.flattrade.in/trade/apitoken", json=payload)
        return resp.json() if resp.status_code == 200 else {"error": f"HTTP {resp.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def _save_screenshot(page, name):
    """Save a timestamped screenshot for debugging."""
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(SCREENSHOT_DIR, f"{ts}_{name}.png")
    page.screenshot(path=path)
    print(f"    📸 Screenshot → {path}")
    return path


def get_token(password=None, pan_or_dob=None):
    """
    Run the full headless login and return the session token string.
    If password / pan_or_dob are not provided, prompts interactively.

    Returns:
        str  — session token on success
        None — on failure
    """
    if password is None:
        password = getpass.getpass("  Enter your Password (hidden): ")
    if pan_or_dob is None:
        pan_or_dob = input("  Enter your PAN / DOB (DDMMYYYY): ").strip()

    auth_url    = f"https://auth.flattrade.in/?app_key={API_KEY}"
    redirect_url = None

    print("\n  → Starting headless browser...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page    = browser.new_page()

        # Capture any request to localhost (the OAuth redirect)
        def on_request(req):
            nonlocal redirect_url
            if "localhost" in req.url and "code=" in req.url:
                redirect_url = req.url
                print(f"  ✅ Redirect captured!")
        page.on("request", on_request)

        # ── Step 1: Open login page ────────────────────────────────────────────
        print(f"  → Loading: {auth_url}")
        page.goto(auth_url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(2)
        _save_screenshot(page, "01_login_page")

        # ── Step 2: Fill User ID & Password ───────────────────────────────────
        page.fill('input[placeholder="User ID"]', USER_ID)
        page.fill('input[placeholder="Password"]', password)
        print(f"  ✅ Filled User ID & Password")
        _save_screenshot(page, "02_credentials_filled")

        # ── Step 3: Click "Get OTP" link ──────────────────────────────────────
        page.click('a:has-text("Get OTP")', timeout=5000)
        time.sleep(2)
        print("  ✅ Clicked 'Get OTP'")
        _save_screenshot(page, "03_after_get_otp_click")

        # ── Step 4: Fill popup User ID & PAN ──────────────────────────────────
        for inp in page.query_selector_all("input"):
            ph = (inp.get_attribute("placeholder") or "").lower()
            if "user" in ph or "id" in ph:
                inp.fill(USER_ID)
                print(f"  ✅ Popup User ID filled")
                break

        for inp in page.query_selector_all("input"):
            ph = (inp.get_attribute("placeholder") or "").lower()
            if "pan" in ph or "dob" in ph:
                inp.fill(pan_or_dob)
                print(f"  ✅ Popup PAN/DOB filled")
                break

        _save_screenshot(page, "04_popup_filled")

        # ── Step 5: Click OK in popup ─────────────────────────────────────────
        for sel in ['button:has-text("OK")', 'button:has-text("Send")',
                    'button:has-text("Generate")', 'button:has-text("Confirm")',
                    'button[type="submit"]']:
            try:
                page.click(sel, timeout=2000)
                print("  ✅ Clicked popup OK — OTP sent to your mobile")
                break
            except Exception:
                continue

        time.sleep(2)
        _save_screenshot(page, "05_after_popup_ok")

        # ── Step 6: User enters OTP ───────────────────────────────────────────
        print("\n" + "=" * 50)
        print("  📱 OTP sent to your registered mobile number.")
        otp = input("  Enter the OTP: ").strip()
        print("=" * 50 + "\n")

        page.fill('input[placeholder="OTP / TOTP"]', otp)
        print("  ✅ Filled OTP")
        _save_screenshot(page, "06_otp_filled")

        # ── Step 7: Click Log In ──────────────────────────────────────────────
        page.click('button:has-text("Log In")', timeout=5000)
        print("  ✅ Clicked Log In")

        # ── Step 8: Wait for redirect ─────────────────────────────────────────
        print("  → Waiting for redirect...")
        for _ in range(30):
            time.sleep(1)
            if redirect_url:
                break
            if "localhost" in page.url and "code=" in page.url:
                redirect_url = page.url
                break

        _save_screenshot(page, "07_final_state")
        browser.close()

    # ── Step 9: Extract code and get token ────────────────────────────────────
    if not redirect_url:
        print("\n  ⚠ Could not capture redirect automatically.")
        redirect_url = input("  Paste the redirect URL manually: ").strip()

    params        = parse_qs(urlparse(redirect_url).query)
    request_code  = params.get("code", [None])[0]
    if not request_code:
        print("  ❌ ERROR: No 'code' found in redirect URL.")
        return None

    print(f"  ✅ Code: {request_code[:10]}...")
    result = _exchange_code_for_token(request_code)

    if result.get("stat") == "Ok":
        token = result["token"]
        print(f"\n{'*-'*40}")
        print("  ✅ LOGIN SUCCESSFUL!")
        print(f"{'*-'*40}")
        print(f"  Client ID : {result.get('client')}")
        print(f"  Token     : {token}")
        print(f"{'*-'*40}\n")
        return token
    else:
        print(f"\n  ❌ Token exchange failed: {result.get('emsg', result)}")
        return None


if __name__ == "__main__":
    print(f"\n{'*-'*40}")
    print(" Flattrade Headless Login")
    print(f"{'*-'*40}\n")
    token = get_token()
