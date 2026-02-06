#!/usr/bin/env python3
"""
LinkedIn Direct Posting - Browser Automation

Logs in with username/password, posts directly via web interface.
NO OAuth, NO API tokens needed. Just direct browser automation.
"""

import os
import subprocess  # nosec B404
import sys
import time

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("📦 Installing playwright...")
    subprocess.run(  # nosec B603 B607
        ["pip", "install", "playwright"],
        check=True,
    )
    subprocess.run(  # nosec B603 B607
        ["playwright", "install", "chromium"],
        check=True,
    )
    from playwright.sync_api import sync_playwright

# User credentials
LINKEDIN_EMAIL = os.environ.get("LINKEDIN_EMAIL", "ig5973700@gmail.com")
LINKEDIN_PASSWORD = os.environ.get("LINKEDIN_PASSWORD", "Rockland26&*")


def post_to_linkedin(text: str, dry_run: bool = False) -> bool:
    """Post to LinkedIn using direct browser automation."""
    if dry_run:
        print(f"📝 Would post ({len(text)} chars):")
        print(f"\n{text}\n")
        return True

    print("🌐 Opening LinkedIn in browser...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Visible so you can see what's happening
        context = browser.new_context()
        page = context.new_page()

        try:
            # Go to LinkedIn login page directly
            print("   Navigating to LinkedIn login page...")
            page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
            time.sleep(3)

            # Login with credentials
            print(f"   Logging in as {LINKEDIN_EMAIL}...")

            # Wait for login form
            page.wait_for_selector("#username", timeout=10000)

            # Fill login form (LinkedIn uses #username and #password)
            page.fill("#username", LINKEDIN_EMAIL)
            page.fill("#password", LINKEDIN_PASSWORD)
            time.sleep(1)

            # Click sign in button
            page.click('button[type="submit"]')
            print("   Submitted login form...")
            time.sleep(8)

            # Handle potential 2FA or verification
            current_url = page.url
            if "checkpoint" in current_url or "challenge" in current_url:
                print("   ⚠️  2FA/verification required - waiting 45s for manual completion...")
                time.sleep(45)

            # Go to feed/home to create post
            print("   Opening post composer...")
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            time.sleep(3)

            # Click "Start a post" button - try multiple selectors
            try:
                selectors = [
                    "button.share-box-feed-entry__trigger",
                    "[data-test-share-box-trigger]",
                    ".share-box-feed-entry__trigger",
                    'button:has-text("Start a post")',
                    '[aria-label*="Start a post"]',
                    ".artdeco-button--tertiary",
                ]

                start_post_btn = None
                for selector in selectors:
                    start_post_btn = page.query_selector(selector)
                    if start_post_btn:
                        print(f"   Found button with selector: {selector}")
                        break

                if start_post_btn:
                    start_post_btn.click()
                    print("   Clicked 'Start a post'...")
                    time.sleep(3)
                else:
                    print("   ❌ Could not find 'Start a post' button with any selector")
                    print("   Available buttons:")
                    buttons = page.query_selector_all("button")
                    for btn in buttons[:10]:  # Show first 10 buttons
                        text = btn.inner_text()[:50] if btn.inner_text() else "(no text)"
                        print(f"      - {text}")
                    browser.close()
                    return False

            except Exception as e:
                print(f"   ❌ Error clicking post button: {e}")
                browser.close()
                return False

            # Fill post text
            try:
                # LinkedIn uses contenteditable div
                text_area = page.query_selector('.ql-editor[contenteditable="true"]')
                if not text_area:
                    text_area = page.query_selector('[role="textbox"]')

                if text_area:
                    print("   Filling post text...")
                    text_area.fill(text)
                    time.sleep(2)
                else:
                    print("   ❌ Could not find text area")
                    browser.close()
                    return False

            except Exception as e:
                print(f"   ❌ Error filling text: {e}")
                browser.close()
                return False

            # Click Post button
            try:
                # Wait for Post button to become enabled
                print("   Waiting for Post button...")
                time.sleep(3)

                # Try multiple selectors
                post_selectors = [
                    "button.share-actions__primary-action",
                    "[data-test-share-box-post-button]",
                    'button:has-text("Post")',
                    '[aria-label="Post"]',
                    ".share-actions__primary-action",
                ]

                post_btn = None
                for selector in post_selectors:
                    try:
                        post_btn = page.wait_for_selector(selector, state="visible", timeout=5000)
                        if post_btn:
                            print(f"   Found Post button: {selector}")
                            break
                    except:
                        continue

                if post_btn:
                    print("   Clicking Post button...")
                    post_btn.click(timeout=10000)
                    time.sleep(5)

                    print("✅ Posted to LinkedIn successfully!")

                    # Keep browser open for 5s so you can see the result
                    time.sleep(5)
                    browser.close()
                    return True
                else:
                    print("   ❌ Could not find visible Post button")
                    print("   Keeping browser open for 10s so you can click it manually...")
                    time.sleep(10)
                    browser.close()
                    return False

            except Exception as e:
                print(f"   ❌ Error posting: {e}")
                browser.close()
                return False

        except Exception as e:
            print(f"❌ Browser automation error: {e}")
            import traceback

            traceback.print_exc()
            browser.close()
            return False

    return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Post to LinkedIn directly")
    parser.add_argument("--text", required=True, help="Post text")
    parser.add_argument("--dry-run", action="store_true", help="Don't post, just preview")

    args = parser.parse_args()

    print("=" * 60)
    print("LINKEDIN DIRECT POSTING")
    print("=" * 60)

    success = post_to_linkedin(args.text, dry_run=args.dry_run)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
