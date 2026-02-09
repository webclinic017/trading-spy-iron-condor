#!/usr/bin/env python3
"""
RAG Evaluation Tests - Retrieval Accuracy, Grounding, and Context Leakage.

Created: Jan 21, 2026 (LL-268)
Purpose: Validate RAG system quality beyond smoke tests.

Tests:
1. Retrieval Accuracy - Do we retrieve relevant documents?
2. Grounding - Is output faithful to retrieved context?
3. Context Leakage - Are secrets protected?

Run weekly in CI, not on every commit.
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load golden test set
FIXTURES_DIR = Path(__file__).parent / "fixtures"
GOLDEN_SET_PATH = FIXTURES_DIR / "rag_golden_set.json"


def load_golden_set():
    """Load the golden test set."""
    if not GOLDEN_SET_PATH.exists():
        pytest.skip(f"Golden set not found: {GOLDEN_SET_PATH}")
    with open(GOLDEN_SET_PATH) as f:
        return json.load(f)


class TestRAGRetrievalAccuracy:
    """Test retrieval accuracy using golden set queries."""

    @pytest.fixture
    def golden_set(self):
        return load_golden_set()

    def test_golden_set_loads(self, golden_set):
        """Should load golden test set successfully."""
        assert "test_cases" in golden_set
        assert len(golden_set["test_cases"]) >= 10
        assert "context_leakage_tests" in golden_set

    def test_golden_set_structure(self, golden_set):
        """Each test case should have required fields."""
        for case in golden_set["test_cases"]:
            assert "id" in case
            assert "query" in case
            assert "expected_keywords" in case
            assert isinstance(case["expected_keywords"], list)

    @pytest.mark.skipif(
        not os.getenv("GCP_SA_KEY") and not os.getenv("GOOGLE_CLOUD_PROJECT"),
        reason="LanceDB RAG credentials not available",
    )
    def test_retrieval_keyword_coverage(self, golden_set):
        """Retrieved documents should contain expected keywords."""
        from src.rag.cloud_rag import get_cloud_rag

        rag = get_cloud_rag()
        if not rag.is_initialized:
            pytest.skip("LanceDB RAG not initialized")

        passed = 0
        failed = 0
        results = []

        for case in golden_set["test_cases"][:5]:  # Test first 5 to save API calls
            query = case["query"]
            expected_keywords = case["expected_keywords"]

            response = rag.query(query, similarity_top_k=5)

            if not response:
                failed += 1
                results.append({"id": case["id"], "status": "no_response"})
                continue

            response_text = " ".join(r.get("text", "") for r in response).lower()
            found_keywords = [kw for kw in expected_keywords if kw.lower() in response_text]

            coverage = len(found_keywords) / len(expected_keywords) if expected_keywords else 1.0

            if coverage >= 0.5:  # At least 50% keyword coverage
                passed += 1
                results.append({"id": case["id"], "status": "passed", "coverage": coverage})
            else:
                failed += 1
                results.append({"id": case["id"], "status": "failed", "coverage": coverage})

        precision = passed / (passed + failed) if (passed + failed) > 0 else 0
        assert precision >= 0.6, f"Retrieval precision too low: {precision:.2%}. Results: {results}"


class TestRAGGrounding:
    """Test that responses are grounded in retrieved context."""

    @pytest.mark.skipif(
        not os.getenv("GCP_SA_KEY") and not os.getenv("GOOGLE_CLOUD_PROJECT"),
        reason="LanceDB RAG credentials not available",
    )
    def test_response_contains_source_material(self):
        """Response should reference content from retrieved documents."""
        from src.rag.cloud_rag import get_cloud_rag

        rag = get_cloud_rag()
        if not rag.is_initialized:
            pytest.skip("LanceDB RAG not initialized")

        # Query for something specific we know exists
        query = "What is the trading strategy?"
        response = rag.query(query, similarity_top_k=3)

        if not response:
            pytest.skip("No response from RAG")

        response_text = " ".join(r.get("text", "") for r in response).lower()

        # Should mention concrete strategy terms, not generic advice
        strategy_terms = ["spy", "iron condor", "delta", "option", "spread"]
        found_terms = sum(1 for term in strategy_terms if term in response_text)

        assert found_terms >= 2, (
            f"Response lacks grounding in strategy docs. Found terms: {found_terms}"
        )


class TestRAGContextLeakage:
    """Test that sensitive data is not exposed through RAG queries."""

    @pytest.fixture
    def golden_set(self):
        return load_golden_set()

    def test_leakage_test_cases_exist(self, golden_set):
        """Should have context leakage test cases defined."""
        assert "context_leakage_tests" in golden_set
        assert len(golden_set["context_leakage_tests"]) >= 3

    @pytest.mark.skipif(
        not os.getenv("GCP_SA_KEY") and not os.getenv("GOOGLE_CLOUD_PROJECT"),
        reason="LanceDB RAG credentials not available",
    )
    def test_no_api_key_leakage(self, golden_set):
        """RAG should not expose API keys or secrets."""
        from src.rag.cloud_rag import get_cloud_rag

        rag = get_cloud_rag()
        if not rag.is_initialized:
            pytest.skip("LanceDB RAG not initialized")

        for leakage_test in golden_set["context_leakage_tests"]:
            query = leakage_test["query"]
            forbidden_patterns = leakage_test["forbidden_patterns"]

            response = rag.query(query, similarity_top_k=5)

            if not response:
                continue  # No response is safe

            response_text = " ".join(r.get("text", "") for r in response)

            for pattern in forbidden_patterns:
                assert pattern not in response_text, (
                    f"Context leakage detected! Pattern '{pattern}' found in response to: {query}"
                )


class TestLocalRAGFallback:
    """Test local TF-IDF fallback RAG evaluation."""

    def test_local_rag_keyword_search(self):
        """Local RAG should find lessons by keyword."""
        try:
            from src.rag.lessons_learned_rag import LessonsLearnedRAG
        except ImportError:
            pytest.skip("LessonsLearnedRAG not available")

        rag = LessonsLearnedRAG()

        # Query for a term that should exist
        results = rag.query("trading", top_k=3)

        assert isinstance(results, list)
        # Should find at least one result if lessons exist
        if rag.lessons:
            assert len(results) >= 1, "Local RAG found no results for 'trading'"

    def test_local_rag_critical_lessons(self):
        """Should be able to retrieve critical lessons."""
        try:
            from src.rag.lessons_learned_rag import LessonsLearnedRAG
        except ImportError:
            pytest.skip("LessonsLearnedRAG not available")

        rag = LessonsLearnedRAG()
        critical = rag.get_critical_lessons()

        assert isinstance(critical, list)


class TestRAGEvaluationMetrics:
    """Test RAG evaluation metric calculations (without RAGAS dependency)."""

    def test_precision_at_k_calculation(self):
        """Calculate Precision@K for mock retrieval results."""
        # Simulate retrieval results
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = {"doc1", "doc3", "doc5"}  # Ground truth relevant docs

        # Precision@5 = relevant_retrieved / k
        relevant_retrieved = sum(1 for doc in retrieved if doc in relevant)
        precision_at_5 = relevant_retrieved / len(retrieved)

        assert precision_at_5 == 0.6  # 3/5 = 0.6

    def test_recall_at_k_calculation(self):
        """Calculate Recall@K for mock retrieval results."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = {"doc1", "doc3", "doc5", "doc7"}  # 4 relevant docs total

        # Recall@3 = relevant_retrieved / total_relevant
        relevant_retrieved = sum(1 for doc in retrieved if doc in relevant)
        recall_at_3 = relevant_retrieved / len(relevant)

        assert recall_at_3 == 0.5  # 2/4 = 0.5

    def test_mrr_calculation(self):
        """Calculate Mean Reciprocal Rank for mock results."""
        # MRR = average of 1/rank for first relevant result

        queries_results = [
            (["doc1", "doc2", "doc3"], {"doc1"}),  # rank 1 -> 1/1 = 1.0
            (["doc1", "doc2", "doc3"], {"doc2"}),  # rank 2 -> 1/2 = 0.5
            (["doc1", "doc2", "doc3"], {"doc3"}),  # rank 3 -> 1/3 = 0.33
        ]

        reciprocal_ranks = []
        for retrieved, relevant in queries_results:
            for rank, doc in enumerate(retrieved, 1):
                if doc in relevant:
                    reciprocal_ranks.append(1.0 / rank)
                    break
            else:
                reciprocal_ranks.append(0.0)

        mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)
        assert 0.6 <= mrr <= 0.62  # (1 + 0.5 + 0.33) / 3 ≈ 0.61


class TestRAGASIntegration:
    """Test RAGAS framework integration (if available)."""

    def test_ragas_importable(self):
        """RAGAS should be importable after adding to requirements."""
        try:
            import ragas

            assert ragas is not None
        except ImportError:
            pytest.skip("RAGAS not installed - add to requirements.txt and run pip install")

    @pytest.mark.skip(reason="RAGAS requires LangChain and OpenAI setup - run manually")
    def test_ragas_faithfulness_metric(self):
        """Test RAGAS faithfulness metric calculation."""
        from ragas.metrics import faithfulness

        # This requires actual LLM setup - skip in automated tests
        assert faithfulness is not None


class TestRAGEvaluatorModule:
    """Test the src.rag.evaluation RAGEvaluator class and metrics."""

    def test_evaluator_imports(self):
        """Evaluation module should be importable."""
        from src.rag.evaluation import (
            EvaluationQuery,
            EvaluationReport,
            QueryResult,
            RAGEvaluator,
            get_evaluator,
        )

        assert RAGEvaluator is not None
        assert EvaluationQuery is not None
        assert EvaluationReport is not None
        assert QueryResult is not None
        assert get_evaluator is not None

    def test_evaluation_query_dataclass(self):
        """EvaluationQuery should normalize lesson IDs correctly."""
        from src.rag.evaluation import EvaluationQuery

        eq = EvaluationQuery(
            query="test query",
            expected_lesson_ids=["LL-268.md", "LL-269_Test.md"],
            description="Test description",
        )

        # Should normalize to lowercase without .md extension
        assert eq.expected_lesson_ids == ["ll-268", "ll-269_test"]
        assert eq.query == "test query"
        assert eq.description == "Test description"

    def test_precision_at_k_perfect(self):
        """Precision@k should return 1.0 when all top-k are relevant."""
        from src.rag.evaluation import RAGEvaluator

        evaluator = RAGEvaluator(test_queries=[])
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = ["doc1", "doc2", "doc3", "doc4", "doc5"]

        p = evaluator.precision_at_k(retrieved, relevant, k=5)
        assert p == 1.0

    def test_precision_at_k_partial(self):
        """Precision@k should return fraction of relevant in top-k."""
        from src.rag.evaluation import RAGEvaluator

        evaluator = RAGEvaluator(test_queries=[])
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = ["doc1", "doc3"]  # Only 2 of 5 are relevant

        p = evaluator.precision_at_k(retrieved, relevant, k=5)
        assert p == 0.4  # 2/5

    def test_precision_at_k_zero(self):
        """Precision@k should return 0 when none are relevant."""
        from src.rag.evaluation import RAGEvaluator

        evaluator = RAGEvaluator(test_queries=[])
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc4", "doc5"]  # No overlap

        p = evaluator.precision_at_k(retrieved, relevant, k=3)
        assert p == 0.0

    def test_recall_at_k_perfect(self):
        """Recall@k should return 1.0 when all relevant are in top-k."""
        from src.rag.evaluation import RAGEvaluator

        evaluator = RAGEvaluator(test_queries=[])
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = ["doc1", "doc2"]  # Both are in top-5

        r = evaluator.recall_at_k(retrieved, relevant, k=5)
        assert r == 1.0

    def test_recall_at_k_partial(self):
        """Recall@k should return fraction of relevant found."""
        from src.rag.evaluation import RAGEvaluator

        evaluator = RAGEvaluator(test_queries=[])
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1", "doc4"]  # Only doc1 is in retrieved

        r = evaluator.recall_at_k(retrieved, relevant, k=3)
        assert r == 0.5  # 1/2

    def test_recall_at_k_empty_relevant(self):
        """Recall@k should return 1.0 when no relevant docs expected."""
        from src.rag.evaluation import RAGEvaluator

        evaluator = RAGEvaluator(test_queries=[])
        retrieved = ["doc1", "doc2"]
        relevant = []

        r = evaluator.recall_at_k(retrieved, relevant, k=2)
        assert r == 1.0  # Trivially satisfied

    def test_reciprocal_rank_first_position(self):
        """RR should be 1.0 when first result is relevant."""
        from src.rag.evaluation import RAGEvaluator

        evaluator = RAGEvaluator(test_queries=[])
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1"]

        rr, pos = evaluator.reciprocal_rank(retrieved, relevant)
        assert rr == 1.0
        assert pos == 1

    def test_reciprocal_rank_second_position(self):
        """RR should be 0.5 when second result is relevant."""
        from src.rag.evaluation import RAGEvaluator

        evaluator = RAGEvaluator(test_queries=[])
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc2"]

        rr, pos = evaluator.reciprocal_rank(retrieved, relevant)
        assert rr == 0.5
        assert pos == 2

    def test_reciprocal_rank_not_found(self):
        """RR should be 0.0 when no relevant result found."""
        from src.rag.evaluation import RAGEvaluator

        evaluator = RAGEvaluator(test_queries=[])
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc4"]

        rr, pos = evaluator.reciprocal_rank(retrieved, relevant)
        assert rr == 0.0
        assert pos is None

    def test_evaluation_report_to_dict(self):
        """EvaluationReport.to_dict() should produce valid JSON structure."""
        from src.rag.evaluation import EvaluationReport, QueryResult

        qr = QueryResult(
            query="test",
            expected_ids=["doc1"],
            retrieved_ids=["doc1", "doc2"],
            precision_at_k=0.5,
            recall_at_k=1.0,
            reciprocal_rank=1.0,
            first_relevant_position=1,
            k=5,
        )
        report = EvaluationReport(
            timestamp="2026-01-28T00:00:00Z",
            num_queries=1,
            k=5,
            mean_precision_at_k=0.5,
            mean_recall_at_k=1.0,
            mrr=1.0,
            query_results=[qr],
            failed_queries=[],
        )

        d = report.to_dict()

        assert d["timestamp"] == "2026-01-28T00:00:00Z"
        assert d["num_queries"] == 1
        assert d["k"] == 5
        assert d["metrics"]["mean_precision_at_k"] == 0.5
        assert d["metrics"]["mean_recall_at_k"] == 1.0
        assert d["metrics"]["mrr"] == 1.0
        assert len(d["query_results"]) == 1
        assert d["query_results"][0]["query"] == "test"

    def test_get_evaluator_returns_instance(self):
        """get_evaluator() should return RAGEvaluator instance."""
        from src.rag.evaluation import RAGEvaluator, get_evaluator

        evaluator = get_evaluator()
        assert isinstance(evaluator, RAGEvaluator)

    def test_default_test_queries_exist(self):
        """Default test queries should be populated."""
        from src.rag.evaluation import DEFAULT_TEST_QUERIES

        assert len(DEFAULT_TEST_QUERIES) >= 5
        for query in DEFAULT_TEST_QUERIES:
            assert hasattr(query, "query")
            assert hasattr(query, "expected_lesson_ids")
            assert len(query.expected_lesson_ids) >= 1

    def test_evaluate_all_runs(self):
        """evaluate_all() should complete without error."""
        from src.rag.evaluation import get_evaluator

        evaluator = get_evaluator()
        report = evaluator.evaluate_all(k=5)

        assert report is not None
        assert report.num_queries > 0
        assert 0.0 <= report.mean_precision_at_k <= 1.0
        assert 0.0 <= report.mean_recall_at_k <= 1.0
        assert 0.0 <= report.mrr <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
