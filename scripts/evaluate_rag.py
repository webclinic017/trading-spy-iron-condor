#!/usr/bin/env python3
"""RAG Evaluation Script.

Runs evaluation queries against the RAG system and generates a report.

Usage:
    python scripts/evaluate_rag.py              # Run with defaults (k=5)
    python scripts/evaluate_rag.py --k 10       # Top 10 results
    python scripts/evaluate_rag.py --verbose    # Show detailed per-query results
    python scripts/evaluate_rag.py --save       # Save report to JSON

Created: January 28, 2026
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.evaluation import (
    DEFAULT_TEST_QUERIES,
    EvaluationReport,
    get_evaluator,
)


def print_report(report: EvaluationReport, verbose: bool = False) -> None:
    """Print evaluation report to console."""
    print("\n" + "=" * 60)
    print("RAG EVALUATION REPORT")
    print("=" * 60)
    print(f"Timestamp: {report.timestamp}")
    print(f"Queries evaluated: {report.num_queries}")
    print(f"k (top results considered): {report.k}")

    print("\n--- AGGREGATE METRICS ---")
    print(f"Mean Precision@{report.k}: {report.mean_precision_at_k:.4f}")
    print(f"Mean Recall@{report.k}:    {report.mean_recall_at_k:.4f}")
    print(f"Mean Reciprocal Rank:      {report.mrr:.4f}")

    # Interpret metrics
    print("\n--- INTERPRETATION ---")
    if report.mean_precision_at_k >= 0.6:
        print(f"[PASS] Precision@{report.k} is good (>= 0.60)")
    elif report.mean_precision_at_k >= 0.4:
        print(f"[WARN] Precision@{report.k} is moderate (0.40-0.60)")
    else:
        print(f"[FAIL] Precision@{report.k} is low (< 0.40)")

    if report.mean_recall_at_k >= 0.6:
        print(f"[PASS] Recall@{report.k} is good (>= 0.60)")
    elif report.mean_recall_at_k >= 0.4:
        print(f"[WARN] Recall@{report.k} is moderate (0.40-0.60)")
    else:
        print(f"[FAIL] Recall@{report.k} is low (< 0.40)")

    if report.mrr >= 0.5:
        print("[PASS] MRR is good (>= 0.50) - relevant docs appear early")
    elif report.mrr >= 0.3:
        print("[WARN] MRR is moderate (0.30-0.50)")
    else:
        print("[FAIL] MRR is low (< 0.30) - relevant docs not appearing in top results")

    if verbose:
        print("\n--- PER-QUERY RESULTS ---")
        for qr in report.query_results:
            status = "[OK]" if qr.recall_at_k >= 0.5 else "[MISS]"
            print(f'\n{status} Query: "{qr.query}"')
            print(f"    Expected: {qr.expected_ids}")
            print(f"    Retrieved: {qr.retrieved_ids[:5]}")
            print(f"    Precision@{qr.k}: {qr.precision_at_k:.3f}")
            print(f"    Recall@{qr.k}: {qr.recall_at_k:.3f}")
            if qr.first_relevant_position:
                print(f"    First relevant at position: {qr.first_relevant_position}")
            else:
                print("    First relevant at position: NOT FOUND")

    if report.failed_queries:
        print("\n--- FAILED QUERIES ---")
        for fq in report.failed_queries:
            print(f"  - {fq}")

    # Summary
    print("\n--- SUMMARY ---")
    successful = len(report.query_results)
    found_count = sum(1 for qr in report.query_results if qr.recall_at_k > 0)
    print(f"Queries with at least one relevant result: {found_count}/{successful}")

    perfect_count = sum(1 for qr in report.query_results if qr.recall_at_k >= 1.0)
    print(f"Queries with all expected results found: {perfect_count}/{successful}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate RAG retrieval quality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/evaluate_rag.py                  # Basic evaluation
    python scripts/evaluate_rag.py --k 10           # Check top 10 results
    python scripts/evaluate_rag.py --verbose        # Show per-query details
    python scripts/evaluate_rag.py --save           # Save report to JSON
    python scripts/evaluate_rag.py --json           # Output only JSON (for CI)
        """,
    )
    parser.add_argument(
        "-k",
        type=int,
        default=5,
        help="Number of top results to consider (default: 5)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed per-query results",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save report to JSON file in data/evaluations/rag/",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output only JSON (no human-readable text)",
    )
    parser.add_argument(
        "--threshold-precision",
        type=float,
        default=0.4,
        help="Minimum acceptable precision (default: 0.4)",
    )
    parser.add_argument(
        "--threshold-recall",
        type=float,
        default=0.4,
        help="Minimum acceptable recall (default: 0.4)",
    )
    parser.add_argument(
        "--threshold-mrr",
        type=float,
        default=0.3,
        help="Minimum acceptable MRR (default: 0.3)",
    )

    args = parser.parse_args()

    # Configure logging
    if args.json:
        logging.basicConfig(level=logging.ERROR)  # Suppress logs for JSON output
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )

    # Run evaluation
    evaluator = get_evaluator()

    if not args.json:
        print(f"Evaluating RAG with {len(DEFAULT_TEST_QUERIES)} test queries...")
        print(f"Loaded {evaluator._get_search_engine().count()} lessons")

    report = evaluator.evaluate_all(k=args.k)

    # Output results
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print_report(report, verbose=args.verbose)

    # Save if requested
    if args.save:
        output_path = evaluator.save_report(report)
        if not args.json:
            print(f"\nReport saved to: {output_path}")

    # Check thresholds for CI
    exit_code = 0
    if report.mean_precision_at_k < args.threshold_precision:
        if not args.json:
            print(
                f"\n[FAIL] Precision@{args.k} ({report.mean_precision_at_k:.4f}) "
                f"below threshold ({args.threshold_precision})"
            )
        exit_code = 1

    if report.mean_recall_at_k < args.threshold_recall:
        if not args.json:
            print(
                f"\n[FAIL] Recall@{args.k} ({report.mean_recall_at_k:.4f}) "
                f"below threshold ({args.threshold_recall})"
            )
        exit_code = 1

    if report.mrr < args.threshold_mrr:
        if not args.json:
            print(f"\n[FAIL] MRR ({report.mrr:.4f}) below threshold ({args.threshold_mrr})")
        exit_code = 1

    if exit_code == 0 and not args.json:
        print("\n[SUCCESS] All metrics meet thresholds")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
