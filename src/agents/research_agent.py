"""
Perplexity Research Agent - Autonomous Weekend Backtesting & Strategy Optimization.

Based on: Perplexity Deep Research (Jan 2026)
- Natural language → automated backtesting
- CSV export for RAG integration
- Parameter optimization for iron condors

Runs autonomously on weekends via GitHub Actions to:
1. Test iron condor parameters (delta, DTE, width)
2. Analyze event-based performance (FOMC, earnings, VIX)
3. Feed results to RAG for continuous learning
4. Update optimal parameters in system_state.json
"""

import asyncio
import csv
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

# Project paths
PROJECT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_DIR / "data"
RESEARCH_DIR = DATA_DIR / "research"
BACKTEST_DIR = RESEARCH_DIR / "backtests"
RAG_DIR = PROJECT_DIR / "rag_knowledge" / "backtests"

# Ensure directories exist
RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
BACKTEST_DIR.mkdir(parents=True, exist_ok=True)
RAG_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class BacktestQuery:
    """A backtest research query for Perplexity."""

    query: str
    parameter_type: str  # 'delta', 'dte', 'width', 'event', 'vix'
    expected_metrics: list[str] = field(
        default_factory=lambda: [
            "win_rate",
            "avg_profit",
            "max_drawdown",
            "profit_factor",
        ]
    )
    priority: int = 1  # 1=high, 2=medium, 3=low


@dataclass
class BacktestResult:
    """Result from a Perplexity backtest research query."""

    query: str
    parameter_type: str
    findings: str
    metrics: dict[str, float]
    optimal_value: str | None
    confidence: float
    sources: list[str]
    timestamp: datetime
    raw_response: str = ""

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "parameter_type": self.parameter_type,
            "findings": self.findings,
            "metrics": self.metrics,
            "optimal_value": self.optimal_value,
            "confidence": self.confidence,
            "sources": self.sources,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_rag_lesson(self) -> str:
        """Convert to RAG-compatible lesson format."""
        return f"""# Backtest Research: {self.parameter_type.upper()}

**Query**: {self.query}

**Findings**: {self.findings}

**Optimal Value**: {self.optimal_value or "N/A"}

**Metrics**:
{chr(10).join(f"- {k}: {v}" for k, v in self.metrics.items())}

**Confidence**: {self.confidence:.0%}

**Sources**: {", ".join(self.sources[:3]) if self.sources else "Perplexity Deep Research"}

**Date**: {self.timestamp.strftime("%Y-%m-%d")}
"""


class PerplexityResearchAgent:
    """
    Autonomous research agent using Perplexity Deep Research.

    Capabilities:
    - Natural language backtesting queries
    - Parameter optimization research
    - Event-based performance analysis
    - CSV export for data analysis
    - RAG integration for continuous learning
    """

    # Standard backtest queries for iron condors
    IRON_CONDOR_QUERIES: list[BacktestQuery] = [
        # Delta optimization
        BacktestQuery(
            query="Historical backtest of SPY iron condors: compare 10-delta vs 15-delta vs 20-delta short strikes. What win rate and profit factor does each achieve over the past 5 years?",
            parameter_type="delta",
            priority=1,
        ),
        # DTE optimization
        BacktestQuery(
            query="SPY iron condor backtest: compare 30 DTE vs 45 DTE vs 60 DTE expiration. Which DTE has the best risk-adjusted returns and win rate?",
            parameter_type="dte",
            priority=1,
        ),
        # Width optimization
        BacktestQuery(
            query="SPY iron condor wing width analysis: $5 wide vs $10 wide spreads. How does wing width affect win rate and maximum drawdown?",
            parameter_type="width",
            priority=2,
        ),
        # FOMC event analysis
        BacktestQuery(
            query="Iron condor performance around FOMC meetings: should you avoid trading 3 days before Fed announcements? Historical win rate comparison.",
            parameter_type="event",
            priority=1,
        ),
        # Earnings event analysis
        BacktestQuery(
            query="SPY iron condor performance during earnings season vs non-earnings periods. Is there a statistically significant difference in win rates?",
            parameter_type="event",
            priority=2,
        ),
        # VIX regime analysis
        BacktestQuery(
            query="Iron condor performance by VIX level: VIX under 15 vs 15-20 vs 20-25 vs above 25. Which VIX regime has the best iron condor win rate?",
            parameter_type="vix",
            priority=1,
        ),
        # Exit timing
        BacktestQuery(
            query="Iron condor exit strategy backtest: close at 50% profit vs 75% profit vs hold to expiration. Which exit strategy maximizes risk-adjusted returns?",
            parameter_type="exit",
            priority=1,
        ),
        # Management rules
        BacktestQuery(
            query="Iron condor adjustment strategies: when one side is tested, does rolling the untested side closer improve overall profitability?",
            parameter_type="management",
            priority=2,
        ),
    ]

    def __init__(self):
        self.api_key = os.environ.get("PERPLEXITY_API_KEY", "")
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.model = "sonar-pro"  # Deep research model
        self.results: list[BacktestResult] = []

    async def research(self, query: str, extract_metrics: bool = True) -> dict[str, Any]:
        """
        Execute a deep research query via Perplexity.

        Returns structured research results with metrics extraction.
        """
        if not self.api_key:
            return {"error": "PERPLEXITY_API_KEY not configured", "results": None}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # System prompt for structured backtest analysis
        system_prompt = """You are a quantitative options research analyst specializing in iron condor strategies on SPY.

When analyzing backtests, ALWAYS provide:
1. Win rate (as percentage)
2. Average profit per trade (as dollar amount or percentage)
3. Maximum drawdown (as percentage)
4. Profit factor (ratio of gross profits to gross losses)
5. Sample size (number of trades analyzed)

Format numbers clearly. Cite specific studies, papers, or data sources when available.
If exact numbers aren't available, provide reasonable estimates with confidence levels."""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            "search_recency_filter": "year",  # Recent data preferred
            "return_citations": True,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=60.0,  # Deep research takes longer
                )
                response.raise_for_status()
                data = response.json()

                answer = data["choices"][0]["message"]["content"]
                citations = data.get("citations", [])

                result = {
                    "answer": answer,
                    "citations": citations,
                    "model": data.get("model", self.model),
                }

                # Extract metrics if requested
                if extract_metrics:
                    result["metrics"] = self._extract_metrics(answer)

                return result

        except httpx.HTTPError as e:
            return {"error": str(e), "results": None}

    def _extract_metrics(self, text: str) -> dict[str, float | None]:
        """Extract quantitative metrics from research response."""
        import re

        metrics = {
            "win_rate": None,
            "avg_profit": None,
            "max_drawdown": None,
            "profit_factor": None,
            "sample_size": None,
        }

        # Win rate patterns (e.g., "85% win rate", "win rate of 80%")
        win_patterns = [
            r"(\d{1,2}(?:\.\d+)?)\s*%\s*win\s*rate",
            r"win\s*rate\s*(?:of\s*)?(\d{1,2}(?:\.\d+)?)\s*%",
            r"(\d{1,2}(?:\.\d+)?)\s*%\s*(?:probability|success)",
        ]
        for pattern in win_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metrics["win_rate"] = float(match.group(1))
                break

        # Profit factor patterns (e.g., "profit factor of 1.5", "1.8 profit factor")
        pf_patterns = [
            r"profit\s*factor\s*(?:of\s*)?(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s*profit\s*factor",
        ]
        for pattern in pf_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metrics["profit_factor"] = float(match.group(1))
                break

        # Max drawdown patterns
        dd_patterns = [
            r"(?:max(?:imum)?\s*)?drawdown\s*(?:of\s*)?(\d{1,2}(?:\.\d+)?)\s*%",
            r"(\d{1,2}(?:\.\d+)?)\s*%\s*(?:max(?:imum)?\s*)?drawdown",
        ]
        for pattern in dd_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metrics["max_drawdown"] = float(match.group(1))
                break

        # Sample size patterns
        sample_patterns = [
            r"(\d{2,5})\s*trades",
            r"sample\s*(?:size\s*)?(?:of\s*)?(\d{2,5})",
            r"(\d{2,5})\s*(?:iron\s*)?condors",
        ]
        for pattern in sample_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metrics["sample_size"] = int(match.group(1))
                break

        return metrics

    async def run_backtest_suite(
        self,
        queries: list[BacktestQuery] | None = None,
        priority_filter: int | None = None,
    ) -> list[BacktestResult]:
        """
        Run a suite of backtest queries.

        Args:
            queries: Custom queries or use default IRON_CONDOR_QUERIES
            priority_filter: Only run queries with priority <= this value

        Returns:
            List of BacktestResult objects
        """
        if queries is None:
            queries = self.IRON_CONDOR_QUERIES

        if priority_filter is not None:
            queries = [q for q in queries if q.priority <= priority_filter]

        results = []
        for query in queries:
            print(f"Researching: {query.parameter_type}...")

            response = await self.research(query.query)

            if response.get("error"):
                print(f"  Error: {response['error']}")
                continue

            # Parse response into BacktestResult
            result = BacktestResult(
                query=query.query,
                parameter_type=query.parameter_type,
                findings=response.get("answer", "")[:500],  # Truncate for summary
                metrics=response.get("metrics", {}),
                optimal_value=self._extract_optimal_value(
                    response.get("answer", ""), query.parameter_type
                ),
                confidence=self._calculate_confidence(response),
                sources=response.get("citations", [])[:5],
                timestamp=datetime.now(timezone.utc),
                raw_response=response.get("answer", ""),
            )

            results.append(result)
            self.results.append(result)

            # Rate limit - don't hammer API
            await asyncio.sleep(2)

        return results

    def _extract_optimal_value(self, text: str, param_type: str) -> str | None:
        """Extract the recommended optimal value from research."""
        import re

        text_lower = text.lower()

        if param_type == "delta":
            # Look for delta recommendations
            patterns = [
                r"(\d{1,2})\s*(?:-)?delta\s*(?:is\s*)?(?:optimal|best|recommended)",
                r"(?:optimal|best|recommended)\s*(?:is\s*)?(\d{1,2})\s*(?:-)?delta",
            ]
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    return f"{match.group(1)}-delta"

        elif param_type == "dte":
            patterns = [
                r"(\d{2,3})\s*(?:dte|days?\s*to\s*expir)",
                r"(?:optimal|best)\s*(?:is\s*)?(\d{2,3})\s*(?:dte|days)",
            ]
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    return f"{match.group(1)} DTE"

        elif param_type == "width":
            patterns = [
                r"\$(\d{1,2})\s*(?:wide|width)",
                r"(\d{1,2})\s*(?:point|dollar)\s*(?:wide|width)",
            ]
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    return f"${match.group(1)} wide"

        elif param_type == "vix":
            if "under 15" in text_lower or "below 15" in text_lower:
                return "VIX < 15"
            elif "15-20" in text_lower or "15 to 20" in text_lower:
                return "VIX 15-20"
            elif "20-25" in text_lower:
                return "VIX 20-25"

        elif param_type == "exit":
            if "50%" in text_lower and ("profit" in text_lower or "max" in text_lower):
                return "50% of max profit"
            elif "75%" in text_lower:
                return "75% of max profit"

        return None

    def _calculate_confidence(self, response: dict) -> float:
        """Calculate confidence score based on response quality."""
        confidence = 0.5  # Base confidence

        # More citations = higher confidence
        citations = response.get("citations", [])
        if len(citations) >= 3:
            confidence += 0.2
        elif len(citations) >= 1:
            confidence += 0.1

        # Metrics extracted = higher confidence
        metrics = response.get("metrics", {})
        non_null_metrics = sum(1 for v in metrics.values() if v is not None)
        confidence += non_null_metrics * 0.05

        # Cap at 0.95
        return min(confidence, 0.95)

    def export_to_csv(self, results: list[BacktestResult] | None = None) -> Path:
        """Export results to CSV for analysis."""
        if results is None:
            results = self.results

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = BACKTEST_DIR / f"backtest_results_{timestamp}.csv"

        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "timestamp",
                    "parameter_type",
                    "query",
                    "optimal_value",
                    "win_rate",
                    "profit_factor",
                    "max_drawdown",
                    "sample_size",
                    "confidence",
                    "findings",
                ],
            )
            writer.writeheader()

            for result in results:
                writer.writerow(
                    {
                        "timestamp": result.timestamp.isoformat(),
                        "parameter_type": result.parameter_type,
                        "query": result.query[:100],
                        "optimal_value": result.optimal_value or "",
                        "win_rate": result.metrics.get("win_rate", ""),
                        "profit_factor": result.metrics.get("profit_factor", ""),
                        "max_drawdown": result.metrics.get("max_drawdown", ""),
                        "sample_size": result.metrics.get("sample_size", ""),
                        "confidence": result.confidence,
                        "findings": result.findings[:200],
                    }
                )

        print(f"Exported {len(results)} results to {csv_path}")
        return csv_path

    def export_to_rag(self, results: list[BacktestResult] | None = None) -> list[Path]:
        """Export results as RAG lessons for continuous learning."""
        if results is None:
            results = self.results

        paths = []
        timestamp = datetime.now().strftime("%Y%m%d")

        for result in results:
            if result.confidence < 0.5:
                continue  # Skip low-confidence results

            filename = f"backtest_{result.parameter_type}_{timestamp}.md"
            rag_path = RAG_DIR / filename

            rag_path.write_text(result.to_rag_lesson())
            paths.append(rag_path)
            print(f"Created RAG lesson: {rag_path.name}")

        return paths

    def update_system_state(self, results: list[BacktestResult] | None = None) -> None:
        """Update system_state.json with optimal parameters."""
        if results is None:
            results = self.results

        state_file = DATA_DIR / "system_state.json"
        if not state_file.exists():
            print("system_state.json not found")
            return

        state = json.loads(state_file.read_text())

        # Initialize research section
        if "research_insights" not in state:
            state["research_insights"] = {}

        insights = state["research_insights"]
        insights["last_updated"] = datetime.now(timezone.utc).isoformat()
        insights["parameters"] = insights.get("parameters", {})

        # Update parameters from high-confidence results
        for result in results:
            if result.confidence >= 0.6 and result.optimal_value:
                insights["parameters"][result.parameter_type] = {
                    "optimal_value": result.optimal_value,
                    "confidence": result.confidence,
                    "win_rate": result.metrics.get("win_rate"),
                    "profit_factor": result.metrics.get("profit_factor"),
                    "updated_at": result.timestamp.isoformat(),
                }

        state_file.write_text(json.dumps(state, indent=2))
        print(f"Updated system_state.json with {len(results)} research insights")


async def run_weekend_research() -> dict[str, Any]:
    """
    Autonomous weekend research job.

    Called by GitHub Actions on Saturday mornings.
    """
    agent = PerplexityResearchAgent()

    if not agent.api_key:
        return {
            "status": "skipped",
            "reason": "PERPLEXITY_API_KEY not configured",
        }

    print("=== Starting Weekend Backtest Research ===")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")

    # Run high-priority queries first
    results = await agent.run_backtest_suite(priority_filter=1)

    # Export results
    csv_path = agent.export_to_csv(results)
    rag_paths = agent.export_to_rag(results)

    # Update system state
    agent.update_system_state(results)

    # Summary
    summary = {
        "status": "completed",
        "queries_run": len(results),
        "high_confidence_results": sum(1 for r in results if r.confidence >= 0.7),
        "csv_export": str(csv_path),
        "rag_lessons_created": len(rag_paths),
        "key_findings": [
            {
                "parameter": r.parameter_type,
                "optimal": r.optimal_value,
                "confidence": r.confidence,
            }
            for r in results
            if r.optimal_value and r.confidence >= 0.6
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Save summary
    summary_file = RESEARCH_DIR / "latest_research_summary.json"
    summary_file.write_text(json.dumps(summary, indent=2))

    print("\n=== Research Complete ===")
    print(f"Results: {len(results)} queries processed")
    print(f"High confidence: {summary['high_confidence_results']}")
    print(f"RAG lessons: {len(rag_paths)}")

    return summary


async def get_research_signal() -> dict[str, Any]:
    """
    Get trading signal based on latest research insights.

    For swarm integration.
    """
    state_file = DATA_DIR / "system_state.json"

    if not state_file.exists():
        return {
            "signal": 0.5,
            "confidence": 0.3,
            "data": {"error": "No research data available"},
        }

    state = json.loads(state_file.read_text())
    insights = state.get("research_insights", {})
    params = insights.get("parameters", {})

    if not params:
        return {
            "signal": 0.5,
            "confidence": 0.3,
            "data": {"error": "No parameter insights available"},
        }

    # Calculate signal based on research confidence
    avg_confidence = sum(p.get("confidence", 0.5) for p in params.values()) / max(len(params), 1)

    # Higher confidence in research = more favorable signal
    signal = 0.5 + (avg_confidence - 0.5) * 0.4

    return {
        "signal": round(signal, 3),
        "confidence": round(avg_confidence, 3),
        "data": {
            "source": "perplexity_deep_research",
            "parameters_optimized": list(params.keys()),
            "last_updated": insights.get("last_updated", "unknown"),
            "recommendation": "FAVORABLE" if avg_confidence >= 0.7 else "NEUTRAL",
        },
    }


if __name__ == "__main__":

    async def demo():
        agent = PerplexityResearchAgent()

        if not agent.api_key:
            print("PERPLEXITY_API_KEY not set - demo mode")
            print("\nTo enable research, set PERPLEXITY_API_KEY environment variable")
            return

        # Run a single test query
        result = await agent.research(
            "What is the historical win rate for SPY iron condors with 15-delta short strikes?"
        )

        print("=== Research Result ===")
        print(f"Answer: {result.get('answer', 'N/A')[:300]}...")
        print(f"Metrics: {result.get('metrics', {})}")
        print(f"Citations: {len(result.get('citations', []))}")

    asyncio.run(demo())
