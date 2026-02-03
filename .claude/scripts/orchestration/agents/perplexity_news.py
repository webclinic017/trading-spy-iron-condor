#!/usr/bin/env python3
"""
Perplexity-Powered News Agent for Trading System

Uses Perplexity Pro/Max API for real-time market intelligence:
- Breaking news affecting SPY/options
- Fed speaker schedules and economic events
- Earnings announcements
- Analyst upgrades/downgrades
- Unusual options activity

Premium Data Sources (Perplexity Max - 50 queries/month per source):
- Statista: Market data, trend analysis, VIX forecasts
- PitchBook: Investment analysis, fund flows
- CB Insights: Market trends, company activity
- Wiley: Academic research (long-term)

Integrates with swarm orchestration for pre-trade validation.
"""

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

# Track premium query usage
PROJECT_DIR = Path(__file__).parent.parent.parent.parent.parent
DATA_DIR = PROJECT_DIR / "data"
USAGE_FILE = DATA_DIR / "perplexity_premium_usage.json"


@dataclass
class MarketEvent:
    """A market-moving event detected by Perplexity."""

    event_type: str  # 'earnings', 'fed', 'economic', 'news', 'options_flow'
    headline: str
    impact_level: str  # 'high', 'medium', 'low'
    ticker: str | None
    timestamp: datetime
    source: str
    details: str


@dataclass
class PremiumQueryBudget:
    """Monthly budget for premium data sources (50/month per source)."""

    statista_used: int = 0
    pitchbook_used: int = 0
    cb_insights_used: int = 0
    wiley_used: int = 0
    month: str = ""  # YYYY-MM format

    @property
    def statista_remaining(self) -> int:
        return max(0, 50 - self.statista_used)

    @property
    def pitchbook_remaining(self) -> int:
        return max(0, 50 - self.pitchbook_used)

    def can_query(self, source: str) -> bool:
        """Check if we have budget for a premium query."""
        if source == "statista":
            return self.statista_remaining > 0
        elif source == "pitchbook":
            return self.pitchbook_remaining > 0
        elif source == "cb_insights":
            return 50 - self.cb_insights_used > 0
        return False

    def record_query(self, source: str) -> None:
        """Record a premium query usage."""
        if source == "statista":
            self.statista_used += 1
        elif source == "pitchbook":
            self.pitchbook_used += 1
        elif source == "cb_insights":
            self.cb_insights_used += 1
        elif source == "wiley":
            self.wiley_used += 1

    def to_dict(self) -> dict:
        return {
            "statista_used": self.statista_used,
            "pitchbook_used": self.pitchbook_used,
            "cb_insights_used": self.cb_insights_used,
            "wiley_used": self.wiley_used,
            "month": self.month,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PremiumQueryBudget":
        return cls(
            statista_used=data.get("statista_used", 0),
            pitchbook_used=data.get("pitchbook_used", 0),
            cb_insights_used=data.get("cb_insights_used", 0),
            wiley_used=data.get("wiley_used", 0),
            month=data.get("month", ""),
        )


class PerplexityNewsAgent:
    """
    Real-time market news agent powered by Perplexity Pro/Max.

    Provides autonomous market scanning for iron condor trading:
    - Pre-trade: Check for events that could blow through strikes
    - Intraday: Monitor for breaking news requiring position adjustment
    - EOD: Summarize day's events for learning

    Premium Data Sources (Max subscription):
    - Statista: VIX forecasts, market trends (HIGH value)
    - PitchBook: Fund flows, institutional analysis (MEDIUM value)
    """

    # Premium source prefixes for Perplexity queries
    PREMIUM_SOURCES = {
        "statista": "Using Statista data:",
        "pitchbook": "Using PitchBook data:",
        "cb_insights": "Using CB Insights:",
    }

    # Daily budget allocation (from 50/month per source)
    DAILY_BUDGET = {
        "statista": 2,  # ~2 per trading day
        "pitchbook": 1,  # ~1 per trading day
    }

    def __init__(self):
        self.api_key = os.environ.get("PERPLEXITY_API_KEY", "")
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.model = "sonar-pro"  # Perplexity Pro model for better results
        self.budget = self._load_budget()

    def _load_budget(self) -> PremiumQueryBudget:
        """Load premium query budget from file."""
        current_month = datetime.now().strftime("%Y-%m")

        if USAGE_FILE.exists():
            try:
                data = json.loads(USAGE_FILE.read_text())
                budget = PremiumQueryBudget.from_dict(data)
                # Reset if new month
                if budget.month != current_month:
                    budget = PremiumQueryBudget(month=current_month)
                return budget
            except (json.JSONDecodeError, KeyError):
                pass

        return PremiumQueryBudget(month=current_month)

    def _save_budget(self) -> None:
        """Save premium query budget to file."""
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        USAGE_FILE.write_text(json.dumps(self.budget.to_dict(), indent=2))

    async def search(self, query: str, recency: str = "day") -> dict[str, Any]:
        """
        Execute a Perplexity search with recency filtering.

        Args:
            query: Natural language search query
            recency: Time filter - 'day', 'week', 'month', 'year'

        Returns:
            Search results with sources
        """
        if not self.api_key:
            return {"error": "PERPLEXITY_API_KEY not configured", "results": []}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a financial market analyst. Provide concise, factual answers about market events. Focus on events that could affect SPY options prices.",
                },
                {"role": "user", "content": query},
            ],
            "search_recency_filter": recency,
            "return_citations": True,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "answer": data["choices"][0]["message"]["content"],
                    "citations": data.get("citations", []),
                    "model": data.get("model", self.model),
                }
        except httpx.HTTPError as e:
            return {"error": str(e), "results": []}

    async def search_premium(self, query: str, source: str) -> dict[str, Any]:
        """
        Execute a premium data source query (Statista, PitchBook, etc.).

        Uses budget tracking to stay within 50 queries/month per source.
        """
        if not self.budget.can_query(source):
            return {
                "error": f"Monthly budget exhausted for {source}",
                "remaining": 0,
            }

        # Prefix query with source instruction
        prefix = self.PREMIUM_SOURCES.get(source, "")
        full_query = f"{prefix} {query}"

        result = await self.search(full_query, recency="week")

        # Record usage
        self.budget.record_query(source)
        self._save_budget()

        result["source"] = source
        result["budget_remaining"] = getattr(self.budget, f"{source}_remaining", 0)

        return result

    async def get_vix_forecast(self) -> dict[str, Any]:
        """Get VIX forecast from Statista (premium source)."""
        return await self.search_premium(
            "What is the VIX volatility index forecast for the next week? Include historical context.",
            "statista"
        )

    async def get_market_trend_analysis(self) -> dict[str, Any]:
        """Get market trend analysis from Statista (premium source)."""
        return await self.search_premium(
            "Current US equity market trend analysis. Is the market trending bullish, bearish, or range-bound?",
            "statista"
        )

    async def get_fund_flow_analysis(self) -> dict[str, Any]:
        """Get SPY fund flow analysis from PitchBook (premium source)."""
        return await self.search_premium(
            "SPY ETF institutional fund flows analysis. Are institutions buying or selling?",
            "pitchbook"
        )

    async def get_pre_trade_intel(self) -> dict[str, Any]:
        """
        Get market intelligence BEFORE opening an iron condor.

        Checks (Standard - unlimited):
        1. Fed speakers today
        2. Economic data releases
        3. Major earnings that could move SPY
        4. Unusual options activity

        Premium checks (budgeted):
        5. VIX forecast from Statista
        6. Market trend from Statista
        """
        # Standard queries (unlimited)
        standard_queries = [
            ("fed_speakers", "Are there any Federal Reserve speakers or FOMC events today?"),
            ("economic_data", "What economic data releases are scheduled today? GDP, jobs, CPI, etc."),
            ("spy_earnings", "Are there any S&P 500 companies reporting earnings today that could move SPY?"),
            ("options_flow", "Is there any unusual options activity on SPY today?"),
        ]

        results = {}
        risk_score = 0.0

        # Execute standard queries
        for key, query in standard_queries:
            result = await self.search(query, recency="day")
            results[key] = result

            # Assess risk from answer
            if result.get("answer"):
                answer_lower = result["answer"].lower()
                if any(word in answer_lower for word in ["fed", "fomc", "powell", "rate"]):
                    risk_score += 0.3
                if any(word in answer_lower for word in ["cpi", "jobs", "gdp", "inflation"]):
                    risk_score += 0.2
                if any(word in answer_lower for word in ["earnings", "guidance", "beat", "miss"]):
                    risk_score += 0.15

        # Premium queries (if budget available)
        premium_data = {}
        if self.budget.can_query("statista"):
            vix_forecast = await self.get_vix_forecast()
            premium_data["vix_forecast"] = vix_forecast

            # Adjust risk based on VIX forecast
            if vix_forecast.get("answer"):
                answer = vix_forecast["answer"].lower()
                if any(word in answer for word in ["spike", "surge", "elevated", "high"]):
                    risk_score += 0.25
                elif any(word in answer for word in ["low", "stable", "calm", "range"]):
                    risk_score -= 0.1  # Favorable for iron condors

        results["premium"] = premium_data

        # Determine trade recommendation
        if risk_score >= 0.5:
            recommendation = "AVOID"
            reason = "High-impact events today could cause volatility beyond iron condor strikes"
        elif risk_score >= 0.3:
            recommendation = "CAUTION"
            reason = "Moderate event risk - consider wider strikes or smaller position"
        else:
            recommendation = "CLEAR"
            reason = "No major market-moving events detected"

        return {
            "risk_score": round(min(max(risk_score, 0), 1.0), 2),
            "recommendation": recommendation,
            "reason": reason,
            "intel": results,
            "premium_budget": self.budget.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_breaking_news(self, ticker: str = "SPY") -> dict[str, Any]:
        """Get breaking news that could affect a position."""
        query = f"Breaking news affecting {ticker} stock price in the last hour"
        result = await self.search(query, recency="day")

        events = []
        if result.get("answer"):
            # Parse for high-impact keywords
            answer = result["answer"]
            impact = "low"

            if any(word in answer.lower() for word in ["crash", "surge", "halt", "breaking"]):
                impact = "high"
            elif any(word in answer.lower() for word in ["rise", "fall", "move", "change"]):
                impact = "medium"

            events.append(
                MarketEvent(
                    event_type="news",
                    headline=answer[:200],
                    impact_level=impact,
                    ticker=ticker,
                    timestamp=datetime.now(),
                    source="perplexity",
                    details=answer,
                )
            )

        return {
            "ticker": ticker,
            "events": [e.__dict__ for e in events],
            "has_breaking_news": len(events) > 0 and events[0].impact_level != "low",
        }

    async def get_phil_town_research(self, topic: str) -> dict[str, Any]:
        """
        Research Phil Town investing concepts for weekend learning.

        Topics: 'rule_1', 'big_5', 'moat', 'management', 'margin_of_safety'
        """
        topic_queries = {
            "rule_1": "Phil Town Rule #1 investing - what are the key principles for never losing money?",
            "big_5": "Phil Town Big 5 numbers for stock analysis - ROIC, sales growth, EPS growth, equity growth, cash flow growth",
            "moat": "What makes a company have a strong economic moat according to Phil Town?",
            "management": "How to evaluate company management quality using Phil Town's methods",
            "margin_of_safety": "Phil Town margin of safety calculation for stock valuation",
        }

        query = topic_queries.get(topic, f"Phil Town investing advice on {topic}")
        result = await self.search(query, recency="year")

        return {
            "topic": topic,
            "research": result.get("answer", ""),
            "sources": result.get("citations", []),
        }


# Integration with swarm orchestration
async def perplexity_news_signal() -> dict[str, Any]:
    """
    Generate trading signal from Perplexity news analysis.

    Returns signal in swarm-compatible format for aggregation.
    """
    agent = PerplexityNewsAgent()

    # Get pre-trade intelligence
    intel = await agent.get_pre_trade_intel()

    # Convert to swarm signal format
    # Higher signal = safer to trade, Lower = more risky
    signal = 1.0 - intel["risk_score"]

    return {
        "signal": round(signal, 2),
        "confidence": 0.85,  # Perplexity is generally reliable
        "data": {
            "risk_score": intel["risk_score"],
            "recommendation": intel["recommendation"],
            "reason": intel["reason"],
            "intel_summary": {
                k: v.get("answer", "")[:100] for k, v in intel.get("intel", {}).items()
            },
        },
    }


async def main():
    """Demo the Perplexity news agent."""
    agent = PerplexityNewsAgent()

    if not agent.api_key:
        print("⚠️  PERPLEXITY_API_KEY not set - using mock mode")
        print("\nTo enable real searches, add to .env:")
        print("  PERPLEXITY_API_KEY=pplx-xxxx...")
        return

    print("=== Pre-Trade Intelligence ===")
    intel = await agent.get_pre_trade_intel()
    print(f"Risk Score: {intel['risk_score']}")
    print(f"Recommendation: {intel['recommendation']}")
    print(f"Reason: {intel['reason']}")

    print("\n=== Breaking News Check ===")
    news = await agent.get_breaking_news("SPY")
    print(f"Has breaking news: {news['has_breaking_news']}")

    print("\n=== Swarm Signal ===")
    signal = await perplexity_news_signal()
    print(f"Signal: {signal['signal']} (higher = safer)")
    print(f"Confidence: {signal['confidence']}")


if __name__ == "__main__":
    asyncio.run(main())
