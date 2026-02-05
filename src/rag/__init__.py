"""
RAG (Retrieval-Augmented Generation) module for the trading system.

This module provides:
- Vertex AI RAG integration for lessons learned
- Local JSON backup for trade recording
- Semantic search across trading knowledge
- RAG evaluation metrics (Precision@k, Recall@k, MRR)
- Semantic caching for cost optimization (up to 68% reduction)

Note: ChromaDB was deprecated Jan 7, 2026 in favor of Vertex AI RAG.
Note: Semantic caching added Jan 28, 2026 for Vertex AI cost optimization.
"""

from src.rag.evaluation import (
    EvaluationQuery,
    EvaluationReport,
    RAGEvaluator,
    get_evaluator,
)
from src.rag.lessons_learned_rag import LessonsLearnedRAG
from src.rag.semantic_cache import SemanticCache, get_cache_stats, get_semantic_cache

__all__ = [
    "LessonsLearnedRAG",
    "RAGEvaluator",
    "EvaluationQuery",
    "EvaluationReport",
    "get_evaluator",
    "SemanticCache",
    "get_semantic_cache",
    "get_cache_stats",
]
