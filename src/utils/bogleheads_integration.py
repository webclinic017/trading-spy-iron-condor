"""
Bogleheads forum integration utilities.

This module provides a lightweight, local-cache-based implementation for
the Bogleheads MCP server. It avoids external dependencies and network calls
by reading normalized RAG data stored under data/rag/normalized.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NORMALIZED_DIR = PROJECT_ROOT / "data" / "rag" / "normalized"


@dataclass(frozen=True)
class BogleheadsEntry:
    title: str
    content: str
    url: str
    published_date: str | None
    ticker: str | None
    sentiment: float | None
    rating: str | None
    rating_score: float | None
    source: str | None
    collected_at: str | None


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _iter_normalized_entries(max_files: int = 50) -> Iterable[dict[str, Any]]:
    if not NORMALIZED_DIR.exists():
        return []

    files = sorted(
        NORMALIZED_DIR.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:max_files]

    entries: list[dict[str, Any]] = []
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if isinstance(payload, list):
            entries.extend(item for item in payload if isinstance(item, dict))
        elif isinstance(payload, dict):
            items = payload.get("items")
            if isinstance(items, list):
                entries.extend(item for item in items if isinstance(item, dict))

    return entries


def _to_entry(raw: dict[str, Any]) -> BogleheadsEntry:
    return BogleheadsEntry(
        title=str(raw.get("title") or ""),
        content=str(raw.get("content") or ""),
        url=str(raw.get("url") or ""),
        published_date=raw.get("published_date"),
        ticker=raw.get("ticker"),
        sentiment=_safe_float(raw.get("sentiment")),
        rating=raw.get("rating"),
        rating_score=_safe_float(raw.get("rating_score")),
        source=raw.get("source"),
        collected_at=raw.get("collected_at"),
    )


def _filter_bogleheads(entries: Iterable[dict[str, Any]]) -> list[BogleheadsEntry]:
    filtered: list[BogleheadsEntry] = []
    for raw in entries:
        source = str(raw.get("source") or "").lower()
        if source != "bogleheads":
            continue
        filtered.append(_to_entry(raw))
    return filtered


class BogleheadsLearner:
    """
    Lightweight Bogleheads learner backed by local normalized RAG cache.
    """

    def monitor_bogleheads_forum(
        self,
        topics: list[str] | None = None,
        keywords: list[str] | None = None,
        max_posts: int = 50,
    ) -> dict[str, Any]:
        entries = _filter_bogleheads(_iter_normalized_entries())

        keyword_terms = [k.lower() for k in (keywords or [])]
        if keyword_terms:
            entries = [
                entry
                for entry in entries
                if any(
                    term in entry.title.lower() or term in entry.content.lower()
                    for term in keyword_terms
                )
            ]

        payload = [
            {
                "title": entry.title,
                "url": entry.url,
                "published_date": entry.published_date,
                "ticker": entry.ticker,
                "sentiment": entry.sentiment,
                "rating": entry.rating,
                "rating_score": entry.rating_score,
                "source": entry.source,
                "collected_at": entry.collected_at,
            }
            for entry in entries[:max_posts]
        ]

        return {
            "status": "ok",
            "source": "local_cache",
            "topics": topics or [],
            "keywords": keywords or [],
            "count": len(payload),
            "items": payload,
        }


def get_bogleheads_signal_for_symbol(
    symbol: str, market_context: dict[str, Any] | None = None
) -> dict[str, Any]:
    entries = _filter_bogleheads(_iter_normalized_entries())
    symbol_upper = symbol.upper()
    symbol_entries = [entry for entry in entries if (entry.ticker or "").upper() == symbol_upper]

    sentiments = [entry.sentiment for entry in symbol_entries if entry.sentiment is not None]
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0

    if avg_sentiment >= 0.2:
        signal = "bullish"
    elif avg_sentiment <= -0.2:
        signal = "bearish"
    else:
        signal = "neutral"

    return {
        "symbol": symbol_upper,
        "signal": signal,
        "avg_sentiment": avg_sentiment,
        "samples": len(sentiments),
        "source": "bogleheads_cache",
        "market_context": market_context or {},
    }


def get_bogleheads_regime() -> dict[str, Any]:
    entries = _filter_bogleheads(_iter_normalized_entries())
    sentiments = [entry.sentiment for entry in entries if entry.sentiment is not None]
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0

    if avg_sentiment >= 0.25:
        regime = "risk_on"
    elif avg_sentiment <= -0.25:
        regime = "risk_off"
    else:
        regime = "neutral"

    return {
        "regime": regime,
        "avg_sentiment": avg_sentiment,
        "samples": len(sentiments),
        "source": "bogleheads_cache",
    }
