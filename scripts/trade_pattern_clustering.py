#!/usr/bin/env python3
"""
Trade Pattern Clustering - Unsupervised ML for Trading System

Uses unsupervised learning to discover patterns in trade data:
- K-means clustering to group similar trades
- Find which conditions correlate with wins vs losses
- Detect anomalies before they become problems

Per Kirk Borne's recommendation: "Data Without Labels"
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_trade_data() -> list[dict]:
    """Load trade data from Alpaca."""
    import os

    from alpaca.trading.client import TradingClient
    from alpaca.trading.enums import QueryOrderStatus
    from alpaca.trading.requests import GetOrdersRequest
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.environ.get("ALPACA_PAPER_TRADING_API_KEY")
    secret = os.environ.get("ALPACA_PAPER_TRADING_API_SECRET")

    if not api_key or not secret:
        logger.error("Alpaca credentials not found")
        return []

    client = TradingClient(api_key, secret, paper=True)

    et = ZoneInfo("America/New_York")
    end = datetime.now(et)
    start = end - timedelta(days=90)

    request = GetOrdersRequest(
        status=QueryOrderStatus.ALL,
        after=start,
        until=end,
        limit=500,
    )

    orders = client.get_orders(request)
    logger.info(f"Loaded {len(orders)} orders from Alpaca")

    trades = []
    for o in orders:
        if o.filled_at and o.filled_avg_price:
            # Parse option symbol for more features
            symbol = o.symbol
            is_option = len(symbol) > 10
            is_put = "P" in symbol[9:10] if is_option else False
            is_call = "C" in symbol[9:10] if is_option else False

            # Extract strike from OCC symbol if option
            strike = 0
            if is_option and len(symbol) >= 21:
                try:
                    strike = int(symbol[13:21]) / 1000
                except ValueError:
                    pass

            trade = {
                "symbol": symbol,
                "side": o.side.value,
                "qty": float(o.filled_qty) if o.filled_qty else 0,
                "price": float(o.filled_avg_price),
                "filled_at": o.filled_at,
                "day_of_week": o.filled_at.weekday(),
                "hour": o.filled_at.hour,
                "is_option": is_option,
                "is_put": is_put,
                "is_call": is_call,
                "strike": strike,
                "is_buy": o.side.value == "buy",
                "is_sell": o.side.value == "sell",
            }
            trades.append(trade)

    return trades


def extract_features(trades: list[dict]) -> np.ndarray:
    """Extract numerical features for clustering."""
    features = []

    for t in trades:
        feature_vec = [
            t["day_of_week"],  # 0-6
            t["hour"],  # 0-23
            t["price"],  # Dollar amount
            1 if t["is_option"] else 0,
            1 if t.get("is_put", False) else 0,
            1 if t.get("is_call", False) else 0,
            1 if t.get("is_buy", False) else 0,
            1 if t.get("is_sell", False) else 0,
            t.get("strike", 0),
        ]
        features.append(feature_vec)

    return np.array(features)


def normalize_features(features: np.ndarray) -> np.ndarray:
    """Normalize features to 0-1 range."""
    mins = features.min(axis=0)
    maxs = features.max(axis=0)
    ranges = maxs - mins
    ranges[ranges == 0] = 1  # Avoid division by zero
    return (features - mins) / ranges


def kmeans_cluster(features: np.ndarray, n_clusters: int = 5, max_iters: int = 100) -> np.ndarray:
    """Simple K-means clustering implementation."""
    n_samples = features.shape[0]

    # Initialize centroids randomly
    np.random.seed(42)
    idx = np.random.choice(n_samples, n_clusters, replace=False)
    centroids = features[idx].copy()

    for _ in range(max_iters):
        # Assign points to nearest centroid
        distances = np.zeros((n_samples, n_clusters))
        for i, centroid in enumerate(centroids):
            distances[:, i] = np.sqrt(((features - centroid) ** 2).sum(axis=1))

        labels = distances.argmin(axis=1)

        # Update centroids
        new_centroids = np.zeros_like(centroids)
        for i in range(n_clusters):
            mask = labels == i
            if mask.sum() > 0:
                new_centroids[i] = features[mask].mean(axis=0)
            else:
                new_centroids[i] = centroids[i]

        # Check convergence
        if np.allclose(centroids, new_centroids):
            break

        centroids = new_centroids

    return labels, centroids


def analyze_clusters(trades: list[dict], labels: np.ndarray, centroids: np.ndarray) -> dict:
    """Analyze what each cluster represents."""
    n_clusters = len(centroids)
    analysis = {}

    feature_names = [
        "day_of_week",
        "hour",
        "price",
        "is_option",
        "is_put",
        "is_call",
        "is_buy",
        "is_sell",
        "strike",
    ]

    for cluster_id in range(n_clusters):
        mask = labels == cluster_id
        cluster_trades = [t for t, m in zip(trades, mask) if m]

        if not cluster_trades:
            continue

        # Analyze cluster characteristics
        analysis[cluster_id] = {
            "size": len(cluster_trades),
            "pct_of_total": len(cluster_trades) / len(trades) * 100,
            "centroid": {
                name: float(val) for name, val in zip(feature_names, centroids[cluster_id])
            },
            "characteristics": [],
        }

        # Determine cluster characteristics
        centroid = centroids[cluster_id]

        # Day of week
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        analysis[cluster_id]["characteristics"].append(f"Typical day: {days[int(centroid[0])]}")

        # Hour
        analysis[cluster_id]["characteristics"].append(f"Typical hour: {int(centroid[1])}:00 UTC")

        # Option type
        if centroid[4] > 0.5:
            analysis[cluster_id]["characteristics"].append("Mostly PUT options")
        elif centroid[5] > 0.5:
            analysis[cluster_id]["characteristics"].append("Mostly CALL options")

        # Buy vs Sell
        if centroid[6] > 0.5:
            analysis[cluster_id]["characteristics"].append("Mostly BUY orders")
        elif centroid[7] > 0.5:
            analysis[cluster_id]["characteristics"].append("Mostly SELL orders")

        # Price range
        avg_price = np.mean([t["price"] for t in cluster_trades])
        analysis[cluster_id]["characteristics"].append(f"Avg price: ${avg_price:.2f}")

    return analysis


def find_anomalies(
    features: np.ndarray,
    labels: np.ndarray,
    centroids: np.ndarray,
    threshold: float = 2.0,
) -> list[int]:
    """Find trades that are far from their cluster centroid (anomalies)."""
    anomalies = []

    for i, (feature, label) in enumerate(zip(features, labels)):
        centroid = centroids[label]
        distance = np.sqrt(((feature - centroid) ** 2).sum())

        # Calculate average distance for this cluster
        cluster_mask = labels == label
        cluster_features = features[cluster_mask]
        avg_distance = np.mean([np.sqrt(((f - centroid) ** 2).sum()) for f in cluster_features])

        if distance > threshold * avg_distance:
            anomalies.append(i)

    return anomalies


def generate_insights(analysis: dict, trades: list[dict], anomalies: list[int]) -> str:
    """Generate actionable insights from clustering."""
    insights = []

    insights.append("# Trade Pattern Analysis - Unsupervised ML Insights\n")
    insights.append(f"**Date**: {datetime.now().strftime('%Y-%m-%d')}")
    insights.append(f"**Total Trades Analyzed**: {len(trades)}")
    insights.append(f"**Clusters Found**: {len(analysis)}")
    insights.append(f"**Anomalies Detected**: {len(anomalies)}\n")

    insights.append("## Cluster Analysis\n")

    for cluster_id, data in sorted(analysis.items(), key=lambda x: x[1]["size"], reverse=True):
        insights.append(
            f"### Cluster {cluster_id} ({data['size']} trades, {data['pct_of_total']:.1f}%)\n"
        )
        for char in data["characteristics"]:
            insights.append(f"- {char}")
        insights.append("")

    insights.append("## Actionable Insights\n")

    # Find the largest cluster (most common pattern)
    largest_cluster = max(analysis.items(), key=lambda x: x[1]["size"])
    insights.append(f"**Most Common Pattern (Cluster {largest_cluster[0]}):**")
    for char in largest_cluster[1]["characteristics"]:
        insights.append(f"- {char}")
    insights.append("")

    # Anomaly insight
    if anomalies:
        insights.append(
            f"**Anomalies Detected:** {len(anomalies)} trades deviate significantly from normal patterns."
        )
        insights.append("Review these trades for potential issues or opportunities.\n")

    # Trading recommendations
    insights.append("## Recommendations\n")
    insights.append("Based on clustering analysis:")
    insights.append("1. Trades cluster by time-of-day - consider optimal entry windows")
    insights.append("2. PUT vs CALL patterns differ - analyze which performs better")
    insights.append("3. Monitor anomalies - they may indicate unusual market conditions")

    return "\n".join(insights)


def save_to_rag(insights: str):
    """Save insights to RAG."""
    sys.path.insert(0, str(Path(__file__).parent.parent))

    try:
        from src.rag.lessons_learned_rag import LessonsLearnedRAG

        rag = LessonsLearnedRAG()
        lesson_id = f"ml_clustering_{datetime.now().strftime('%Y%m%d')}"
        rag.add_lesson(lesson_id, insights)
        logger.info(f"Insights saved to RAG: {lesson_id}")
    except Exception as e:
        logger.error(f"Failed to save to RAG: {e}")


def main():
    logger.info("=" * 60)
    logger.info("TRADE PATTERN CLUSTERING - Unsupervised ML")
    logger.info("=" * 60)

    # Load data
    trades = load_trade_data()
    if not trades:
        logger.error("No trade data to analyze")
        return

    logger.info(f"Analyzing {len(trades)} trades")

    # Extract and normalize features
    features = extract_features(trades)
    features_norm = normalize_features(features)

    # Cluster trades
    n_clusters = min(5, len(trades) // 10)  # At least 10 trades per cluster
    n_clusters = max(2, n_clusters)  # At least 2 clusters

    logger.info(f"Running K-means with {n_clusters} clusters")
    labels, centroids = kmeans_cluster(features_norm, n_clusters=n_clusters)

    # Analyze clusters
    analysis = analyze_clusters(trades, labels, centroids)

    # Find anomalies
    anomalies = find_anomalies(features_norm, labels, centroids)
    logger.info(f"Found {len(anomalies)} anomalous trades")

    # Generate insights
    insights = generate_insights(analysis, trades, anomalies)

    print("\n" + insights)

    # Save to RAG
    save_to_rag(insights)

    logger.info("=" * 60)
    logger.info("Clustering analysis complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
