"""
Tests for Document-Aware RAG System

This validates the LongRAG-style document retrieval:
1. Section-level chunking preserves lesson sections
2. Metadata enrichment extracts categories and strategies
3. Hybrid retrieval filters by metadata before semantic search
4. Complex queries about position stacking return relevant results
"""

from pathlib import Path

import pytest


class TestDocumentAwareRAG:
    """Test suite for document-aware RAG system."""

    def test_import_module(self):
        """Verify module can be imported."""
        from src.memory.document_aware_rag import (
            DocumentAwareRAG,
            get_document_aware_rag,
        )

        assert DocumentAwareRAG is not None
        assert get_document_aware_rag is not None

    def test_singleton_instance(self):
        """Verify singleton pattern works."""
        from src.memory.document_aware_rag import get_document_aware_rag

        rag1 = get_document_aware_rag()
        rag2 = get_document_aware_rag()
        assert rag1 is rag2

    def test_search_result_dataclass(self):
        """Verify SearchResult dataclass structure."""
        from src.memory.document_aware_rag import SearchResult

        result = SearchResult(
            document_id="test_doc",
            title="Test Title",
            content="Test content",
            section_title="Test Section",
            score=0.95,
            metadata={"severity": "critical"},
        )

        assert result.document_id == "test_doc"
        assert result.score == 0.95
        assert result.metadata["severity"] == "critical"

    def test_document_section_dataclass(self):
        """Verify DocumentSection dataclass structure."""
        from src.memory.document_aware_rag import DocumentSection

        section = DocumentSection(
            id="test_section",
            title="Test Section",
            content="Test content here",
            section_type="root_cause",
            parent_doc_id="test_doc",
            parent_doc_title="Test Document",
            chunk_index=0,
        )

        assert section.section_type == "root_cause"
        assert section.chunk_index == 0

    def test_classify_section_type(self):
        """Verify section type classification."""
        from src.memory.document_aware_rag import DocumentAwareRAG

        rag = DocumentAwareRAG()

        assert rag._classify_section_type("What Happened") == "what_happened"
        assert rag._classify_section_type("Root Cause Analysis") == "root_cause"
        assert rag._classify_section_type("Solution") == "solution"
        assert rag._classify_section_type("Prevention") == "prevention"
        assert rag._classify_section_type("Summary") == "summary"
        assert rag._classify_section_type("Random Title") == "content"

    def test_extract_sections(self):
        """Verify section extraction from markdown."""
        from src.memory.document_aware_rag import DocumentAwareRAG

        rag = DocumentAwareRAG()

        content = """# Test Document

This is the summary.

## What Happened

This is what happened in the incident.
The description continues here with more details.

## Root Cause

The root cause was identified as a bug.
Multiple factors contributed to this issue.

## Solution

We fixed it by adding validation.
The fix was verified in testing.
"""

        sections = rag._extract_sections(content, "test_doc", "Test Document")

        # Should have 3 sections (summary + what_happened + root_cause + solution)
        assert len(sections) >= 3

        # Check section types
        section_types = [s.section_type for s in sections]
        assert "what_happened" in section_types
        assert "root_cause" in section_types
        assert "solution" in section_types

    def test_metadata_extraction(self):
        """Verify metadata extraction from content."""
        from src.memory.document_aware_rag import DocumentAwareRAG

        rag = DocumentAwareRAG()

        content = """# LL-275: Position Stacking Bug

**Severity**: CRITICAL

This lesson documents a position stacking issue with iron condor trades
in the $100K paper account during high VIX environments.

## Prevention

Always validate position limits before executing trades.
"""

        filepath = Path("/tmp/ll_275_position_stacking_bug_jan22.md")
        metadata = rag._extract_metadata(content, filepath)

        assert metadata["severity"] == "critical"
        assert metadata["lesson_id"] == "LL-275"
        assert "risk_management" in metadata["categories"]
        assert "iron condor" in metadata["strategies"]
        assert metadata["account"] == "100k"
        assert metadata["market_condition"] == "high_volatility"

    @pytest.mark.skipif(
        not Path(
            "/Users/ganapolsky_i/workspace/git/igor/trading/.claude/memory/lancedb"
        ).exists(),
        reason="LanceDB not available",
    )
    def test_search_integration(self):
        """Integration test for search functionality."""
        from src.memory.document_aware_rag import get_document_aware_rag

        rag = get_document_aware_rag()

        result = rag.query_with_context("position stacking", limit=2)

        assert "query" in result
        assert "result_count" in result
        assert "results" in result
        assert result["result_count"] >= 0

    @pytest.mark.skipif(
        not Path(
            "/Users/ganapolsky_i/workspace/git/igor/trading/.claude/memory/lancedb"
        ).exists(),
        reason="LanceDB not available",
    )
    def test_complex_query(self):
        """Test complex query about position stacking in high VIX."""
        from src.memory.document_aware_rag import get_document_aware_rag

        rag = get_document_aware_rag()

        result = rag.query_with_context(
            "What went wrong with position stacking in high VIX environments?", limit=3
        )

        # Should find relevant results
        assert result["result_count"] > 0

        # Results should be high severity
        for r in result["results"]:
            # Position stacking lessons should be marked as important
            assert r.score > 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
