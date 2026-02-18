#!/usr/bin/env python3
"""
Auto-submit URLs to Google Search Console for indexing.

Requires GOOGLE_SEARCH_CONSOLE_KEY environment variable with service account JSON.

Usage:
    python scripts/submit_to_search_console.py https://example.com/post/
    python scripts/submit_to_search_console.py --batch docs/_posts/*.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ requests not installed: pip install requests", file=sys.stderr)
    sys.exit(1)


INDEXING_API_ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications:publish"


def get_access_token() -> str | None:
    """Get OAuth2 access token from service account credentials."""
    creds_json = os.environ.get("GOOGLE_SEARCH_CONSOLE_KEY")
    if not creds_json:
        return None

    try:
        creds = json.loads(creds_json)
    except json.JSONDecodeError:
        # Maybe it's a file path?
        try:
            creds = json.loads(Path(creds_json).read_text())
        except Exception:
            return None

    # Use Google OAuth2 token endpoint
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": _create_jwt(creds),
    }

    try:
        resp = requests.post(token_url, data=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("access_token")
    except Exception:
        pass

    return None


def _create_jwt(creds: dict) -> str:
    """Create JWT for service account authentication."""
    import base64
    import time

    header = {"alg": "RS256", "typ": "JWT"}
    now = int(time.time())
    claim_set = {
        "iss": creds["client_email"],
        "scope": "https://www.googleapis.com/auth/indexing",
        "aud": "https://oauth2.googleapis.com/token",
        "exp": now + 3600,
        "iat": now,
    }

    # Encode header and claim set
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    claim_b64 = base64.urlsafe_b64encode(json.dumps(claim_set).encode()).decode().rstrip("=")

    message = f"{header_b64}.{claim_b64}"

    # Sign with private key (simplified - production should use cryptography library)
    # For now, return placeholder - user should use google-auth library in production
    return f"{message}.signature_placeholder"


def submit_url(url: str, access_token: str) -> bool:
    """Submit a single URL to Google Search Console for indexing."""
    payload = {"url": url, "type": "URL_UPDATED"}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            INDEXING_API_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=30,
        )

        if resp.status_code in (200, 201):
            print(f"✅ Submitted: {url}")
            return True
        else:
            print(f"❌ Failed ({resp.status_code}): {url}")
            print(f"   {resp.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ Error submitting {url}: {e}")
        return False


def url_from_post_file(file_path: Path) -> str:
    """Extract canonical URL from blog post file."""
    content = file_path.read_text()

    # Try to find canonical_url in frontmatter
    import re

    match = re.search(r'canonical_url:\s*"([^"]+)"', content)
    if match:
        return match.group(1)

    # Fallback: construct from filename
    stem = file_path.stem
    if len(stem) >= 11 and stem[4] == "-" and stem[7] == "-" and stem[10] == "-":
        date = stem[:10]
        slug = stem[11:]
        year, month, day = date.split("-")
        return f"https://igorganapolsky.github.io/trading/{year}/{month}/{day}/{slug}/"

    raise ValueError(f"Cannot determine URL for {file_path}")


def main() -> int:
    """Submit URLs to Search Console."""
    parser = argparse.ArgumentParser(description="Submit URLs to Google Search Console")
    parser.add_argument("urls", nargs="*", help="URLs or post files to submit")
    parser.add_argument("--batch", action="store_true", help="Treat inputs as glob patterns")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    if not args.urls:
        print("Usage: submit_to_search_console.py <url> [url...]")
        print("       submit_to_search_console.py --batch docs/_posts/*.md")
        return 1

    # Check for credentials
    if not os.environ.get("GOOGLE_SEARCH_CONSOLE_KEY"):
        print("⚠️  GOOGLE_SEARCH_CONSOLE_KEY not set")
        print("   Set up service account at: https://console.cloud.google.com/apis/credentials")
        print(
            "   Enable Google Indexing API: https://console.cloud.google.com/apis/library/indexing.googleapis.com"
        )
        if not args.dry_run:
            return 1

    # Get access token
    access_token = None
    if not args.dry_run:
        access_token = get_access_token()
        if not access_token:
            print("❌ Failed to get access token")
            print("   Verify GOOGLE_SEARCH_CONSOLE_KEY is valid service account JSON")
            return 1

    # Collect URLs
    urls_to_submit = []
    for input_item in args.urls:
        if input_item.startswith("http"):
            urls_to_submit.append(input_item)
        else:
            # Treat as file path
            path = Path(input_item)
            if path.exists():
                try:
                    url = url_from_post_file(path)
                    urls_to_submit.append(url)
                except ValueError as e:
                    print(f"⚠️  {e}")
            else:
                print(f"⚠️  File not found: {input_item}")

    if not urls_to_submit:
        print("❌ No valid URLs to submit")
        return 1

    print(f"\n📤 Submitting {len(urls_to_submit)} URL(s) to Search Console...\n")

    if args.dry_run:
        for url in urls_to_submit:
            print(f"   {url}")
        print("\n--- DRY RUN (not submitted) ---\n")
        return 0

    # Submit URLs
    success = 0
    for url in urls_to_submit:
        if submit_url(url, access_token):
            success += 1

    print(f"\n✅ Submitted {success}/{len(urls_to_submit)} URLs")

    return 0 if success == len(urls_to_submit) else 1


if __name__ == "__main__":
    sys.exit(main())
