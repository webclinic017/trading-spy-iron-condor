#!/usr/bin/env python3
"""
LinkedIn OAuth 2.0 Authentication - Automated via Playwright.

Gets access token for posting to LinkedIn API.
"""

import json
import os
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Installing playwright...")
    os.system("pip install playwright && playwright install chromium")
    from playwright.sync_api import sync_playwright

# Load credentials
CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET")
LINKEDIN_EMAIL = os.environ.get("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.environ.get("LINKEDIN_PASSWORD", "Rockland26&*")

REDIRECT_URI = "https://localhost:8443/callback"
SCOPES = ["openid", "profile", "w_member_social"]
TOKEN_FILE = Path(__file__).parent.parent / "data" / "linkedin_token.json"


def get_authorization_code():
    """Use Playwright to automate LinkedIn OAuth login."""
    auth_url = "https://www.linkedin.com/oauth/v2/authorization?" + urlencode(
        {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": " ".join(SCOPES),
            "state": "rlhf_blog_auth",
        }
    )

    print("🔐 Starting LinkedIn OAuth flow...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Visible for 2FA if needed
        context = browser.new_context()
        page = context.new_page()

        # Go to auth URL
        page.goto(auth_url)
        time.sleep(2)

        # Fill login form
        try:
            page.fill('input[name="session_key"]', LINKEDIN_EMAIL)
            page.fill('input[name="session_password"]', LINKEDIN_PASSWORD)
            page.click('button[type="submit"]')
            print("   Submitted login form...")
            time.sleep(3)
        except Exception as e:
            print(f"   Login form not found or already logged in: {e}")

        # Wait for redirect with auth code (or approval page)
        try:
            # May need to click "Allow" button
            allow_btn = page.query_selector('button:has-text("Allow")')
            if allow_btn:
                allow_btn.click()
                print("   Clicked Allow button...")
                time.sleep(2)
        except:
            pass

        # Wait for redirect
        print("   Waiting for redirect...")
        for _ in range(30):
            current_url = page.url
            if "localhost" in current_url and "code=" in current_url:
                parsed = urlparse(current_url)
                params = parse_qs(parsed.query)
                code = params.get("code", [None])[0]
                browser.close()
                return code
            time.sleep(1)

        browser.close()
        return None


def exchange_code_for_token(code: str) -> dict:
    """Exchange authorization code for access token."""
    response = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )

    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Token exchange failed: {response.status_code} - {response.text}")
        return None


def get_user_info(access_token: str) -> dict:
    """Get LinkedIn user info (for person URN)."""
    response = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    if response.status_code == 200:
        return response.json()
    return None


def save_token(token_data: dict, user_info: dict):
    """Save token and user info to file."""
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "access_token": token_data["access_token"],
        "expires_in": token_data.get("expires_in", 3600),
        "token_type": token_data.get("token_type", "Bearer"),
        "person_urn": f"urn:li:person:{user_info.get('sub', '')}",
        "name": user_info.get("name", ""),
        "created_at": time.time(),
    }

    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Token saved to {TOKEN_FILE}")
    return data


def load_token() -> dict | None:
    """Load existing token if valid."""
    if not TOKEN_FILE.exists():
        return None

    with open(TOKEN_FILE) as f:
        data = json.load(f)

    # Check if expired (tokens last ~60 days)
    created = data.get("created_at", 0)
    expires_in = data.get("expires_in", 3600)
    if time.time() - created > expires_in - 3600:  # Refresh 1hr before expiry
        print("⚠️ Token expired, need to re-authenticate")
        return None

    return data


def main():
    """Main auth flow."""
    print("=" * 50)
    print("LinkedIn OAuth 2.0 Authentication")
    print("=" * 50)

    if not CLIENT_ID or not CLIENT_SECRET:
        print("❌ LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set")
        return 1

    # Check for existing valid token
    existing = load_token()
    if existing:
        print(f"✅ Valid token exists for {existing.get('name', 'user')}")
        print(f"   Person URN: {existing.get('person_urn')}")
        return 0

    # Get new token
    code = get_authorization_code()
    if not code:
        print("❌ Failed to get authorization code")
        return 1

    print(f"✅ Got authorization code: {code[:20]}...")

    token_data = exchange_code_for_token(code)
    if not token_data:
        return 1

    print("✅ Got access token")

    user_info = get_user_info(token_data["access_token"])
    if user_info:
        print(f"✅ User: {user_info.get('name')}")

    save_token(token_data, user_info or {})

    # Update .env with token
    env_file = Path(__file__).parent.parent.parent / ".env"
    with open(env_file, "a") as f:
        f.write(f"\nLINKEDIN_ACCESS_TOKEN={token_data['access_token']}\n")
        if user_info:
            f.write(f"LINKEDIN_PERSON_URN=urn:li:person:{user_info.get('sub', '')}\n")

    print("✅ Credentials added to .env")
    return 0


if __name__ == "__main__":
    exit(main())
