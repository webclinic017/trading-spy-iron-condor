#!/usr/bin/env python3
"""
LinkedIn OAuth 2.0 - Simple approach using system browser.

Opens OAuth URL in your default browser (where you're already logged in),
catches the redirect with a local server, exchanges code for token.

100% automated, no copy-paste needed.
"""
from __future__ import annotations

import http.server
import json
import os
import socketserver
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

# OAuth config
CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8443/callback"
SCOPES = ["openid", "profile", "w_member_social", "email"]
STATE = f"rlhf_{int(time.time())}"

# File paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TOKEN_FILE = DATA_DIR / "linkedin_token.json"
ENV_FILE = PROJECT_ROOT.parent / ".env"

# Global to capture auth code
auth_code = None
auth_error = None


class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler to catch OAuth redirect."""

    def do_GET(self):
        global auth_code, auth_error

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"""
                <html><body style="font-family: sans-serif; padding: 50px; text-align: center;">
                <h1 style="color: #0a66c2;">&#x2705; Authorization Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
                <script>setTimeout(() => window.close(), 2000);</script>
                </body></html>
            """
            )
        elif "error" in params:
            auth_error = params["error"][0]
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                f"""
                <html><body style="font-family: sans-serif; padding: 50px; text-align: center;">
                <h1 style="color: #d32f2f;">❌ Authorization Failed</h1>
                <p>Error: {auth_error}</p>
                <p>Close this window and check the terminal.</p>
                </body></html>
            """.encode()
            )
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        pass


def start_callback_server():
    """Start local HTTP server to catch OAuth callback."""
    handler = OAuthCallbackHandler
    with socketserver.TCPServer(("localhost", 8443), handler) as httpd:
        print("   Local server listening on http://localhost:8443")
        httpd.timeout = 120  # 2 minute timeout
        while auth_code is None and auth_error is None:
            httpd.handle_request()


def exchange_code_for_token(code: str) -> dict | None:
    """Exchange authorization code for access token."""
    print("\n🔄 Exchanging code for token...")

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
        print(f"❌ Token exchange failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None


def get_user_info(access_token: str) -> dict | None:
    """Get LinkedIn user info."""
    print("🔄 Getting user info...")

    response = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )

    if response.status_code == 200:
        return response.json()
    else:
        print(f"⚠️  User info failed: {response.status_code}")
        return None


def save_credentials(token_data: dict, user_info: dict | None):
    """Save token and URN to files."""
    access_token = token_data["access_token"]
    person_id = user_info.get("sub", "") if user_info else ""
    person_urn = f"urn:li:person:{person_id}"
    name = user_info.get("name", "User") if user_info else "User"

    # Save to token file
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(
            {
                "access_token": access_token,
                "person_urn": person_urn,
                "name": name,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            f,
            indent=2,
        )

    print(f"✅ Token saved to {TOKEN_FILE}")

    # Update .env file
    env_content = ENV_FILE.read_text() if ENV_FILE.exists() else ""

    # Remove old LinkedIn tokens if present
    lines = env_content.split("\n")
    filtered_lines = [
        line
        for line in lines
        if not line.startswith("LINKEDIN_ACCESS_TOKEN=")
        and not line.startswith("LINKEDIN_PERSON_URN=")
    ]

    # Append new tokens
    filtered_lines.append("")
    filtered_lines.append(
        f"# LinkedIn OAuth Token (Generated {time.strftime('%Y-%m-%d %H:%M:%S')})"
    )
    filtered_lines.append(f"LINKEDIN_ACCESS_TOKEN={access_token}")
    filtered_lines.append(f"LINKEDIN_PERSON_URN={person_urn}")

    ENV_FILE.write_text("\n".join(filtered_lines))
    print(f"✅ Credentials added to {ENV_FILE}")

    return {"access_token": access_token, "person_urn": person_urn, "name": name}


def main():
    """Main OAuth flow."""
    print("=" * 60)
    print("LinkedIn OAuth 2.0 - Automated")
    print("=" * 60)

    if not CLIENT_ID or not CLIENT_SECRET:
        print("❌ Missing credentials in environment:")
        print("   LINKEDIN_CLIENT_ID")
        print("   LINKEDIN_CLIENT_SECRET")
        return 1

    # Check for existing valid token
    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE) as f:
                existing = json.load(f)
            print(f"✅ Valid token exists for {existing.get('name', 'user')}")
            print(f"   Person URN: {existing.get('person_urn')}")
            print("\n   Token ready for use in RLHF blog publisher")
            return 0
        except Exception:
            pass

    # Build OAuth URL
    auth_url = "https://www.linkedin.com/oauth/v2/authorization?" + urlencode(
        {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": " ".join(SCOPES),
            "state": STATE,
        }
    )

    print("\n🌐 Opening LinkedIn OAuth in your browser...")
    print("   (You should already be logged in)\n")

    # Start local server in background
    server_thread = threading.Thread(target=start_callback_server, daemon=True)
    server_thread.start()

    # Give server time to start
    time.sleep(1)

    # Open browser
    webbrowser.open(auth_url)

    print("⏳ Waiting for authorization (up to 2 minutes)...")

    # Wait for auth code
    timeout = 120
    start_time = time.time()
    while auth_code is None and auth_error is None:
        if time.time() - start_time > timeout:
            print("\n❌ Timeout waiting for authorization")
            return 1
        time.sleep(0.5)

    if auth_error:
        print(f"\n❌ Authorization failed: {auth_error}")
        return 1

    if not auth_code:
        print("\n❌ No authorization code received")
        return 1

    print(f"\n✅ Got authorization code: {auth_code[:20]}...")

    # Exchange for token
    token_data = exchange_code_for_token(auth_code)
    if not token_data:
        return 1

    print("✅ Got access token")

    # Get user info
    user_info = get_user_info(token_data["access_token"])
    if user_info:
        print(f"✅ User: {user_info.get('name')}")

    # Save credentials
    creds = save_credentials(token_data, user_info)

    print("\n" + "=" * 60)
    print("✅ LINKEDIN OAUTH COMPLETE")
    print("=" * 60)
    print(f"   User: {creds['name']}")
    print(f"   Person URN: {creds['person_urn']}")
    print("\n🚀 RLHF blogs will now auto-post to LinkedIn")

    return 0


if __name__ == "__main__":
    sys.exit(main())
