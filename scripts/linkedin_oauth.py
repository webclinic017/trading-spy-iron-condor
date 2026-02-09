#!/usr/bin/env python3
"""
LinkedIn OAuth 2.0 Helper

Gets an access token for LinkedIn API posting.
Run once to get the token, then store in environment.
"""

from __future__ import annotations

import http.server
import os
import urllib.parse
import webbrowser

# LinkedIn OAuth endpoints
LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

# Your app credentials (from environment)
CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET", "")
REDIRECT_URI = "http://localhost:8585/callback"
SCOPES = ["openid", "profile", "w_member_social"]


def get_auth_url() -> str:
    """Generate the LinkedIn authorization URL."""
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "state": "rlhf_blog_auth",
    }
    return f"{LINKEDIN_AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(code: str) -> dict | None:
    """Exchange authorization code for access token."""
    import requests

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(LINKEDIN_TOKEN_URL, data=data, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Token exchange failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None


class OAuthHandler(http.server.BaseHTTPRequestHandler):
    """Handle OAuth callback."""

    def do_GET(self):
        """Handle the OAuth callback."""
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            code = params["code"][0]
            print("\n✅ Authorization code received!")

            # Exchange for token
            print("Exchanging code for access token...")
            token_data = exchange_code_for_token(code)

            if token_data:
                access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 0)

                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                html = f"""
                <html>
                <head><title>LinkedIn OAuth Success</title></head>
                <body style="font-family: Arial; padding: 40px; text-align: center;">
                    <h1>✅ LinkedIn Authorization Successful!</h1>
                    <p>Your access token has been generated.</p>
                    <p><strong>Expires in:</strong> {expires_in // 3600} hours</p>
                    <hr>
                    <p>Add this to your environment:</p>
                    <pre style="background: #f4f4f4; padding: 20px; text-align: left; overflow-x: auto;">
export LINKEDIN_ACCESS_TOKEN="{access_token}"
                    </pre>
                    <p>Or add to GitHub Secrets for CI/CD.</p>
                    <p>You can close this window now.</p>
                </body>
                </html>
                """
                self.wfile.write(html.encode())

                print("\n" + "=" * 60)
                print("SUCCESS! Add this to your environment:")
                print("=" * 60)
                print(f'\nexport LINKEDIN_ACCESS_TOKEN="{access_token}"\n')
                print(f"Token expires in: {expires_in // 3600} hours")
                print("=" * 60)
            else:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Token exchange failed")
        else:
            error = params.get("error", ["Unknown error"])[0]
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"Error: {error}".encode())
            print(f"❌ Authorization failed: {error}")

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def main():
    """Run the OAuth flow."""
    print("=" * 60)
    print("LINKEDIN OAUTH 2.0 SETUP")
    print("=" * 60)
    print()

    # Check for required credentials
    if not CLIENT_ID or not CLIENT_SECRET:
        print("❌ Missing LinkedIn credentials!")
        print()
        print("Set these environment variables:")
        print("  export LINKEDIN_CLIENT_ID='your-client-id'")
        print("  export LINKEDIN_CLIENT_SECRET='your-client-secret'")
        print()
        print("Get credentials from: https://www.linkedin.com/developers/apps")
        return 1

    print("This will open your browser to authorize the app.")
    print("After authorizing, you'll be redirected back here.")
    print()

    # Generate auth URL
    auth_url = get_auth_url()
    print(f"Authorization URL:\n{auth_url}\n")

    # Start local server
    server = http.server.HTTPServer(("localhost", 8585), OAuthHandler)
    print("Starting local server on http://localhost:8585 ...")
    print("Waiting for OAuth callback...\n")

    # Open browser
    webbrowser.open(auth_url)

    # Handle one request (the OAuth callback)
    server.handle_request()
    server.server_close()

    print("\nDone!")


if __name__ == "__main__":
    main()
