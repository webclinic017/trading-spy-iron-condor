#!/usr/bin/env python3
"""
X.com (Twitter) Publisher - API Version

Posts to X.com using Twitter API v2 with OAuth 1.0a.
Reliable, fast, no browser automation needed.
"""

import os
import sys

try:
    import tweepy
except ImportError:
    print("📦 Installing tweepy...")
    os.system("pip3 install --break-system-packages tweepy")
    import tweepy

# API credentials from environment (NOT hardcoded)
API_KEY = os.environ.get("TWITTER_API_KEY")
API_SECRET = os.environ.get("TWITTER_API_SECRET")
ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

POST_MAX_LENGTH = 280  # X.com character limit


def post_to_twitter(text: str, dry_run: bool = False) -> bool:
    """Post to X.com using Twitter API v2."""
    if len(text) > POST_MAX_LENGTH:
        print(f"⚠️  Text too long ({len(text)} chars), truncating to {POST_MAX_LENGTH}")
        text = text[: POST_MAX_LENGTH - 3] + "..."

    if dry_run:
        print(f"📝 Would post ({len(text)} chars):")
        print(f"\n{text}\n")
        return True

    # Check credentials
    if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
        print("❌ Missing Twitter API credentials in environment")
        print("   Required: TWITTER_API_KEY, TWITTER_API_SECRET,")
        print("             TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET")
        return False

    print("📡 Posting to X.com via API...")

    try:
        # Authenticate with Twitter API v2
        client = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
        )

        # Post tweet
        response = client.create_tweet(text=text)

        if response.data:
            tweet_id = response.data.get("id")
            print("✅ Posted to X.com successfully!")
            print(f"   URL: https://x.com/IgorGanapolsky/status/{tweet_id}")
            return True
        else:
            print("❌ No response data from Twitter API")
            return False

    except tweepy.TweepyException as e:
        print(f"❌ Twitter API error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
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
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't post, just preview"
    )

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
