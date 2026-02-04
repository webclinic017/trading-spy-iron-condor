#!/usr/bin/env python3
"""
X.com (Twitter) Publisher - Browser Automation

Posts to X.com using Playwright browser automation.
Uses Google SSO for auth, posts via web interface (not API).

This avoids X.com API approval requirements and rate limits.
"""

import os
import sys
import time

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("📦 Installing playwright...")
    os.system("pip install playwright && playwright install chromium")
    from playwright.sync_api import sync_playwright

# User credentials
GOOGLE_EMAIL = os.environ.get("TWITTER_EMAIL", "iganapolsky@gmail.com")
POST_MAX_LENGTH = 280  # X.com character limit


def post_to_twitter(text: str, dry_run: bool = False) -> bool:
    """Post to X.com using browser automation."""
    if len(text) > POST_MAX_LENGTH:
        print(f"⚠️  Text too long ({len(text)} chars), truncating to {POST_MAX_LENGTH}")
        text = text[: POST_MAX_LENGTH - 3] + "..."

    if dry_run:
        print(f"📝 Would post ({len(text)} chars):")
        print(f"\n{text}\n")
        return True

    print("🌐 Opening X.com in browser...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Visible for debugging
        context = browser.new_context()
        page = context.new_page()

        try:
            # Go to X.com login page
            print("   Navigating to X.com login page...")
            page.goto("https://x.com/login", wait_until="domcontentloaded")
            time.sleep(3)

            # Click Google SSO button
            print(f"   Using Google SSO for {GOOGLE_EMAIL}...")
            try:
                google_btn = page.wait_for_selector(
                    'span:has-text("Continue with Google")', timeout=10000
                )
                if google_btn:
                    google_btn.click()
                    print("   Clicked Google SSO...")
                    time.sleep(5)

                    # Google login popup should open
                    # Wait for it to complete (user may need to select account)
                    print("   ⏳ Waiting for Google auth (30s)...")
                    time.sleep(30)

            except Exception as e:
                print(f"   ⚠️  Google SSO error: {e}")

            # Wait for compose page
            page.goto("https://x.com/compose/tweet")
            time.sleep(3)

            # Find tweet text area
            try:
                # X.com uses contenteditable divs
                text_area = page.query_selector(
                    '[contenteditable="true"][data-testid="tweetTextarea_0"]'
                )
                if not text_area:
                    # Try alternate selector
                    text_area = page.query_selector('[role="textbox"][aria-label*="Post"]')

                if text_area:
                    print("   Filling tweet text...")
                    text_area.fill(text)
                    time.sleep(2)

                    # Click Post button
                    post_btn = page.query_selector('[data-testid="tweetButton"]')
                    if not post_btn:
                        post_btn = page.query_selector('button:has-text("Post")')

                    if post_btn:
                        print("   Clicking Post button...")
                        post_btn.click()
                        time.sleep(3)

                        print("✅ Posted to X.com successfully!")
                        browser.close()
                        return True
                    else:
                        print("❌ Post button not found")
                else:
                    print("❌ Tweet text area not found")

            except Exception as e:
                print(f"❌ Error posting tweet: {e}")

        except Exception as e:
            print(f"❌ Browser automation error: {e}")
        finally:
            browser.close()

    return False


def generate_twitter_post(signal: str, title: str, devto_url: str = None) -> str:
    """Generate concise X.com post (280 char limit)."""
    emoji = "✅" if signal == "positive" else "📚"

    # X.com posts need to be VERY short
    link = devto_url or "https://igorganapolsky.github.io/trading/"

    # Keep it under 280 chars
    base_text = f"{emoji} {title}\n\n"
    tags = "#AITrading #RLHF #BuildingInPublic"

    # Calculate remaining space for link
    remaining = POST_MAX_LENGTH - len(base_text) - len(tags) - 5  # Buffer

    if len(link) < remaining:
        text = f"{base_text}{link}\n\n{tags}"
    else:
        # Link too long, use short version
        text = f"{base_text}{tags}\n\n{link[: remaining - 3]}..."

    return text


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Publish to X.com (Twitter)")
    parser.add_argument("--signal", required=True, choices=["positive", "negative"])
    parser.add_argument("--title", required=True, help="Post title")
    parser.add_argument("--url", help="Article URL")
    parser.add_argument("--dry-run", action="store_true", help="Don't post, just preview")

    args = parser.parse_args()

    print("=" * 60)
    print("X.COM (TWITTER) PUBLISHER")
    print("=" * 60)

    # Generate post text
    text = generate_twitter_post(args.signal, args.title, args.url)

    # Post
    success = post_to_twitter(text, dry_run=args.dry_run)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
