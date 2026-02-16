#!/usr/bin/env python3
"""
Build and verify the Unified Search Index.

Indexes all data sources (lessons, trades, session decisions, market signals)
into a single searchable index and runs verification queries.

Usage:
    python3 scripts/build_unified_index.py
    python3 scripts/build_unified_index.py --skip-verify  # Skip verification queries
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


VERIFICATION_QUERIES = [
    {
        "query": "iron condor position sizing risk",
        "expected_types": {"lesson", "trade"},
        "description": "should return lessons + trades",
    },
    {
        "query": "SPY REJECTED",
        "expected_types": {"session_decision"},
        "description": "should return session decisions",
    },
    {
        "query": "credit stress",
        "expected_types": {"market_signal"},
        "description": "should return market signals",
    },
    {
        "query": "exit strategy when to close",
        "expected_types": {"lesson"},
        "description": "should return lessons",
    },
]


def print_summary(stats: dict) -> None:
    """Print the index build summary."""
    lessons = stats.get("lessons", 0)
    trades = stats.get("trades", 0)
    decisions = stats.get("session_decisions", 0)
    signals = stats.get("market_signals", 0)
    total = lessons + trades + decisions + signals
    vocab_size = stats.get("bm25_vocabulary", 0)
    avg_doc_len = stats.get("avg_doc_length", 0)

    print("\n📊 Unified Search Index Built")
    print("─────────────────────────────")
    print(f"  Lessons:           {lessons:>5,} documents")
    print(f"  Trades:            {trades:>5,} documents")
    print(f"  Session Decisions: {decisions:>5,} documents")
    print(f"  Market Signals:    {signals:>5,} documents")
    print("─────────────────────────────")
    print(f"  Total:             {total:>5,} documents")
    print(f"  BM25 vocabulary:  {vocab_size:>5,} terms")
    print(f"  Avg doc length:    {avg_doc_len:>5,} tokens")


def run_verification(search) -> int:
    """Run verification queries and print results. Returns number of failures."""
    failures = 0

    print("\n\n🔎 Running Verification Queries")
    print("═" * 60)

    for vq in VERIFICATION_QUERIES:
        query = vq["query"]
        expected = vq["expected_types"]
        desc = vq["description"]

        print(f'\n🔍 Query: "{query}"')
        print(f"   ({desc})")

        try:
            results = search.search(query, top_k=5)
        except Exception as e:
            print(f"   ❌ Search failed: {e}")
            failures += 1
            continue

        if not results:
            print("   ⚠️  No results returned")
            failures += 1
            continue

        found_types = set()
        for result in results:
            doc_type = result.get("type", "unknown")
            doc_id = result.get("id", "unknown")
            score = result.get("score", 0.0)
            found_types.add(doc_type)
            print(f"   [{doc_type:<18}] {doc_id:<40} score: {score:.2f}")

        if expected & found_types:
            print(f"   ✅ Found expected types: {expected & found_types}")
        else:
            print(f"   ⚠️  Expected {expected}, got {found_types}")
            failures += 1

    return failures


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build and verify Unified Search Index")
    parser.add_argument("--skip-verify", action="store_true", help="Skip verification queries")
    args = parser.parse_args()

    # Import UnifiedSearch
    try:
        from src.rag.unified_search import get_unified_search
    except ImportError as e:
        logger.error(f"❌ Failed to import UnifiedSearch: {e}")
        logger.error("   Ensure src/rag/unified_search.py exists and dependencies are installed.")
        return 1

    print("🏗️  Building Unified Search Index...")
    print("═" * 60)

    t0 = time.time()

    try:
        search = get_unified_search()
    except Exception as e:
        logger.error(f"❌ Failed to initialize UnifiedSearch: {e}")
        return 1

    try:
        stats = search.build_index()
    except Exception as e:
        logger.error(f"❌ Index build failed: {e}")
        return 1

    elapsed = time.time() - t0

    print_summary(stats)
    print(f"\n⏱️  Index built in {elapsed:.2f}s")

    # Verification
    if args.skip_verify:
        print("\n⏭️  Skipping verification (--skip-verify)")
        return 0

    failures = run_verification(search)

    print("\n" + "═" * 60)
    if failures == 0:
        print("✅ All verification queries passed!")
    else:
        print(f"⚠️  {failures}/{len(VERIFICATION_QUERIES)} verification queries had issues")

    return 1 if failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
