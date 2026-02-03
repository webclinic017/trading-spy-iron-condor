"""
Research module for trading system.

Contains:
- docling_parser: IBM Docling integration for parsing financial documents
- research_agent: Perplexity-powered weekend research agent
"""

from src.research.docling_parser import (
    DoclingDocument,
    DoclingFinancialParser,
    FinancialMetrics,
    ParsedSection,
    ParsedTable,
    get_docling_parser,
)

__all__ = [
    "DoclingDocument",
    "DoclingFinancialParser",
    "FinancialMetrics",
    "ParsedSection",
    "ParsedTable",
    "get_docling_parser",
]
