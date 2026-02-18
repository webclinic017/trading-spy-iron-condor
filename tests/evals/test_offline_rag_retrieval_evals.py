"""
Offline RAG Retrieval Evals - deterministic, dependency-free regression tests.

Goal: catch retrieval regressions without requiring LanceDB, embeddings, or network access.

We evaluate the LessonsLearnedRAG keyword fallback path against a tiny synthetic corpus.
This is intentionally "boring but stable" so CI can gate merges on behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass(frozen=True)
class RetrievalEvalCase:
    name: str
    query: str
    expected_top_id: str
    severity_filter: str | None = None


def _write_lesson(
    dir_path: Path, lesson_id: str, *, severity: str, body: str, tags: list[str]
) -> None:
    # Keep filenames free of date-like patterns so recency boosts don't affect ranking.
    assert "jan" not in lesson_id.lower()
    assert "2026" not in lesson_id.lower()

    tag_block = ""
    if tags:
        tag_block = "\n\n## Tags\n" + ", ".join(f"`{t}`" for t in tags) + "\n"

    content = f"""# {lesson_id}

**Severity**: {severity}

{body.strip()}
{tag_block}
"""
    (dir_path / f"{lesson_id}.md").write_text(content, encoding="utf-8")


@pytest.fixture()
def mini_lessons_dir(tmp_path: Path) -> Path:
    """A tiny, deterministic lessons corpus for offline evals."""
    _write_lesson(
        tmp_path,
        "ll_position_stacking_blocker",
        severity="CRITICAL",
        body="""
Position stacking caused multiple BUYs to accumulate the same symbol.

## Prevention
Block opening BUY orders when the symbol is already held. Always check positions first.
""",
        tags=["risk", "position-sizing", "iron-condor"],
    )
    _write_lesson(
        tmp_path,
        "ll_blind_trading_guard",
        severity="CRITICAL",
        body="""
Blind trading happened when equity was zero or missing.

## Prevention
Require equity > 0 before any risk-on trade is allowed.
""",
        tags=["risk", "equity", "guardrails"],
    )
    _write_lesson(
        tmp_path,
        "ll_stop_loss_required",
        severity="HIGH",
        body="""
Trades were entered without a stop loss definition.

## Prevention
Define stop loss relative to credit received and enforce it on entry.
""",
        tags=["risk", "stop-loss", "execution"],
    )
    _write_lesson(
        tmp_path,
        "ll_alpaca_api_symbol_parsing",
        severity="MEDIUM",
        body="""
Option OCC symbol parsing failed which broke risk checks.

## Prevention
Extract underlying from OCC symbols and validate allowed tickers.
""",
        tags=["alpaca", "api", "occ"],
    )
    _write_lesson(
        tmp_path,
        "ll_rag_retrieval_precision",
        severity="LOW",
        body="""
Keyword retrieval needs to match tags as well as body content.

## Prevention
Boost matches found in tags to improve precision.
""",
        tags=["rag", "retrieval", "keywords"],
    )
    return tmp_path


@pytest.mark.parametrize(
    "case",
    [
        RetrievalEvalCase(
            name="position stacking query hits stacking lesson",
            query="position stacking buy already held symbol",
            expected_top_id="ll_position_stacking_blocker",
        ),
        RetrievalEvalCase(
            name="blind trading query hits equity guard lesson",
            query="equity is zero blind trading should be blocked",
            expected_top_id="ll_blind_trading_guard",
        ),
        RetrievalEvalCase(
            name="stop loss query hits stop loss lesson",
            query="stop loss credit received must be defined",
            expected_top_id="ll_stop_loss_required",
        ),
        RetrievalEvalCase(
            name="severity filter returns critical lesson",
            query="guardrails risk equity",
            expected_top_id="ll_blind_trading_guard",
            severity_filter="CRITICAL",
        ),
        RetrievalEvalCase(
            name="tag match is boosted",
            query="occ symbol underlying extraction",
            expected_top_id="ll_alpaca_api_symbol_parsing",
        ),
    ],
    ids=lambda c: c.name,
)
def test_offline_rag_retrieval_eval(case: RetrievalEvalCase, mini_lessons_dir: Path) -> None:
    """
    Deterministic eval for LessonsLearnedRAG retrieval behavior.

    This uses a custom knowledge_dir, which forces:
    - no LanceDB
    - no LessonsSearch singleton
    - direct file keyword retrieval with tag boosting
    """
    from src.rag.lessons_learned_rag import LessonsLearnedRAG

    rag = LessonsLearnedRAG(knowledge_dir=str(mini_lessons_dir))
    results = rag.query(case.query, top_k=3, severity_filter=case.severity_filter)
    assert results, "Expected at least one result"
    assert results[0]["id"] == case.expected_top_id
