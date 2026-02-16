#!/usr/bin/env python3
"""
Generate Wiki Home Page with Current Account Data

Pulls live data from Alpaca and generates an accurate wiki home page.
Called by .github/workflows/update-wiki.yml
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from alpaca.trading.client import TradingClient

# Config
API_KEY = os.environ.get("ALPACA_API_KEY")
SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY")
STARTING_CAPITAL = 100000.0  # $100K account started Jan 30, 2026
NORTH_STAR_TARGET = 600000.0  # $600K = Financial Independence
MONTHLY_INCOME_TARGET = 6000.0  # $6K/month after-tax
MIN_TRADES_FOR_PROJECTION = 30  # No projections until 30+ completed trades
SYSTEM_STATE_PATH = Path("data/system_state.json")
TRADES_PATH = Path("data/trades.json")


def get_account_data() -> dict:
    """Fetch current account data from Alpaca."""
    if not API_KEY or not SECRET_KEY:
        # Fallback: read from system_state.json instead of hardcoded values
        if SYSTEM_STATE_PATH.exists():
            try:
                state = json.loads(SYSTEM_STATE_PATH.read_text())
                portfolio = state.get("portfolio", {})
                positions = state.get("positions", [])
                # Parse IC positions from system state
                iron_condors = []
                expiries: dict[str, dict] = {}
                for pos in positions:
                    sym = pos.get("symbol", "")
                    if len(sym) > 10:
                        expiry = sym[3:9]
                        if expiry not in expiries:
                            expiries[expiry] = {"puts": [], "calls": []}
                        strike = int(sym[10:18]) / 1000
                        opt_type = "puts" if "P" in sym[9:10] else "calls"
                        expiries[expiry][opt_type].append(
                            {"strike": strike, "qty": int(float(pos.get("qty", 0)))}
                        )
                for expiry, legs in expiries.items():
                    if legs["puts"] and legs["calls"]:
                        put_strikes = sorted([p["strike"] for p in legs["puts"]])
                        call_strikes = sorted([c["strike"] for c in legs["calls"]])
                        exp_date = datetime.strptime(f"20{expiry}", "%Y%m%d")
                        iron_condors.append(
                            {
                                "expiry": exp_date.strftime("%b %d, %Y"),
                                "put_spread": f"{put_strikes[0]:.0f}/{put_strikes[-1]:.0f}"
                                if len(put_strikes) >= 2
                                else str(put_strikes[0]),
                                "call_spread": f"{call_strikes[0]:.0f}/{call_strikes[-1]:.0f}"
                                if len(call_strikes) >= 2
                                else str(call_strikes[0]),
                            }
                        )
                return {
                    "equity": portfolio.get("equity", STARTING_CAPITAL),
                    "cash": portfolio.get("cash", STARTING_CAPITAL),
                    "buying_power": portfolio.get("cash", STARTING_CAPITAL) * 2,
                    "positions": positions,
                    "iron_condors": iron_condors,
                }
            except (json.JSONDecodeError, KeyError):
                pass
        return {
            "equity": STARTING_CAPITAL,
            "cash": STARTING_CAPITAL,
            "buying_power": STARTING_CAPITAL * 2,
            "positions": [],
        }

    client = TradingClient(API_KEY, SECRET_KEY, paper=True)
    account = client.get_account()
    positions = client.get_all_positions()

    # Parse iron condors
    iron_condors = []
    options = [p for p in positions if len(p.symbol) > 10]

    # Group by expiry
    expiries = {}
    for pos in options:
        symbol = pos.symbol
        expiry = symbol[3:9]  # YYMMDD
        if expiry not in expiries:
            expiries[expiry] = {"puts": [], "calls": []}

        strike = int(symbol[10:18]) / 1000
        opt_type = "puts" if "P" in symbol[9:10] else "calls"
        qty = int(float(pos.qty))
        expiries[expiry][opt_type].append({"strike": strike, "qty": qty})

    # Format iron condors
    for expiry, legs in expiries.items():
        if legs["puts"] and legs["calls"]:
            put_strikes = sorted([p["strike"] for p in legs["puts"]])
            call_strikes = sorted([c["strike"] for c in legs["calls"]])
            exp_date = datetime.strptime(f"20{expiry}", "%Y%m%d")
            iron_condors.append(
                {
                    "expiry": exp_date.strftime("%b %d, %Y"),
                    "put_spread": (
                        f"{put_strikes[0]:.0f}/{put_strikes[-1]:.0f}"
                        if len(put_strikes) >= 2
                        else str(put_strikes[0])
                    ),
                    "call_spread": (
                        f"{call_strikes[0]:.0f}/{call_strikes[-1]:.0f}"
                        if len(call_strikes) >= 2
                        else str(call_strikes[0])
                    ),
                }
            )

    return {
        "equity": float(account.equity),
        "cash": float(account.cash),
        "buying_power": float(account.buying_power),
        "iron_condors": iron_condors,
    }


def get_north_star_metrics() -> dict:
    """Load North Star metrics from system_state.json."""
    defaults = {
        "probability_score": 0,
        "probability_label": "unknown",
        "required_cagr": 0,
        "estimated_cagr": 0,
        "closed_trades": 0,
        "realized_pl": 0,
        "months_remaining": 44,
    }
    if not SYSTEM_STATE_PATH.exists():
        return defaults
    try:
        state = json.loads(SYSTEM_STATE_PATH.read_text())
        ns = state.get("north_star", {})
        contribs = state.get("north_star_contributions", {})

        # Closed trade stats from trades.json (canonical source)
        samples = 0
        total_pnl = 0.0
        if TRADES_PATH.exists():
            try:
                trades_data = json.loads(TRADES_PATH.read_text())
                stats = trades_data.get("stats", {})
                samples = stats.get("closed_trades", 0)
                total_pnl = stats.get("total_realized_pnl", 0.0)
            except (json.JSONDecodeError, KeyError):
                pass
        return {
            "probability_score": ns.get("probability_score", 0),
            "probability_label": ns.get("probability_label", "unknown"),
            "required_cagr": ns.get("required_cagr", 0),
            "estimated_cagr": ns.get("estimated_cagr_from_expectancy", 0),
            "closed_trades": samples,
            "realized_pl": total_pnl,
            "months_remaining": contribs.get("months_remaining", 44),
        }
    except (json.JSONDecodeError, KeyError):
        return defaults


def generate_wiki_home(data: dict) -> str:
    """Generate wiki home page markdown."""
    et = ZoneInfo("America/New_York")
    now = datetime.now(et)
    date_str = now.strftime("%b %d, %Y")

    equity = data["equity"]
    net_gain = equity - STARTING_CAPITAL
    net_gain_pct = (net_gain / STARTING_CAPITAL) * 100
    iron_condors = data.get("iron_condors", [])

    # Progress calculations
    progress_to_goal = (equity / NORTH_STAR_TARGET) * 100

    # North Star data-driven metrics
    ns = get_north_star_metrics()

    # Generate iron condor table
    ic_table = ""
    if iron_condors:
        ic_table = "| Expiry | Put Spread | Call Spread |\n|--------|------------|-------------|\n"
        for ic in iron_condors:
            ic_table += f"| {ic['expiry']} | {ic['put_spread']} | {ic['call_spread']} |\n"
    else:
        ic_table = "*No open iron condor positions*\n"

    wiki = f"""# 🤖 AI Trading System Wiki

Welcome to the **AI-Powered Automated Trading System** wiki!

---

## 📊 [Progress Dashboard](Progress-Dashboard)

**👉 [View Live Progress Dashboard →](https://igorganapolsky.github.io/trading/)**

The system tracks progress toward Financial Independence:
- North Star goal: **$6,000/month after-tax**
- Current strategy: **Iron Condors on SPY**
- Phil Town Rule #1: **Don't lose money**

---

## 🚀 Quick Links

### Documentation
- [CLAUDE.md](https://github.com/IgorGanapolsky/trading/blob/main/.claude/CLAUDE.md) - Strategy & directives
- [System State](https://github.com/IgorGanapolsky/trading/blob/main/data/system_state.json) - Live account data

### System Status
- [GitHub Actions](https://github.com/IgorGanapolsky/trading/actions) - Execution logs
- [RAG Chat](https://igorganapolsky.github.io/trading/rag-query/) - Query lessons learned

### Key Features
- **Iron Condor Guardian**: Automated Rule #1 enforcement (stop loss, 7 DTE exit, 50% profit take)
- **RLHF System**: Thompson Sampling + ShieldCortex memory
- **CI/CD**: 1300+ tests, self-healing workflows
- **Multi-Agent Swarm**: Analysis, execution, and monitoring agents

---

## 📈 Current Status ({date_str})

| Metric | Value |
|--------|-------|
| **Account Equity** | ${equity:,.2f} |
| **Starting Capital** | ${STARTING_CAPITAL:,.0f} (Jan 30, 2026) |
| **Net Gain** | ${net_gain:+,.2f} ({net_gain_pct:+.2f}%) |
| **Open Positions** | {len(iron_condors)} Iron Condor(s) |
| **Strategy** | SPY Iron Condors (15-20 delta) |

### Open Iron Condors
{ic_table}
---

## 🎯 North Star Goal

**Target**: Financial Independence = **$6,000/month after-tax**

| Metric | Value |
|--------|-------|
| **Current Equity** | ${equity:,.0f} |
| **Target Capital** | $600,000 |
| **Progress** | {progress_to_goal:.1f}% |
| **Completed IC Trades** | {ns["closed_trades"]} of {MIN_TRADES_FOR_PROJECTION} required |
| **Realized IC P/L** | ${ns["realized_pl"]:,.0f} |
| **Months Remaining** | {ns["months_remaining"]} |
| **Required CAGR** | {ns["required_cagr"] * 100:.1f}% |
| **Estimated CAGR** | {ns["estimated_cagr"] * 100:.2f}% |
| **Probability** | {ns["probability_score"]:.1f}% ({ns["probability_label"]}) |

**Deadline**: Nov 14, 2029

{"⚠️ **INSUFFICIENT DATA** — " + str(MIN_TRADES_FOR_PROJECTION - ns["closed_trades"]) + " more completed trades needed before projections are valid" if ns["closed_trades"] < MIN_TRADES_FOR_PROJECTION else "📊 **DATA-DRIVEN** — Projections based on " + str(ns["closed_trades"]) + " completed trades"}

---

## 🛡️ Phil Town Rule #1 Enforcement

The **Iron Condor Guardian** runs every 30 minutes during market hours to enforce:

1. **Stop Loss**: Exit if loss reaches 200% of credit received
2. **7 DTE Exit**: Close positions at 7 days to expiration (gamma risk)
3. **50% Profit Take**: Lock in profits at 50% of max profit

*Automation ensures rules are followed without human intervention.*

---

*Last updated: {now.strftime("%Y-%m-%d %H:%M ET")} by GitHub Actions*
"""
    return wiki


def main():
    """Main entry point."""
    print("Fetching account data from Alpaca...")
    data = get_account_data()
    print(f"Equity: ${data['equity']:,.2f}")
    print(f"Iron Condors: {len(data.get('iron_condors', []))}")

    print("Generating wiki home page...")
    wiki_content = generate_wiki_home(data)

    # Write to file for workflow to pick up
    output_path = Path("wiki_home.md")
    output_path.write_text(wiki_content)
    print(f"Wiki home page written to {output_path}")


if __name__ == "__main__":
    main()
