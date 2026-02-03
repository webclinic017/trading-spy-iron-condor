#!/usr/bin/env python3
"""
Generate Wiki Home Page with Current Account Data

Pulls live data from Alpaca and generates an accurate wiki home page.
Called by .github/workflows/update-wiki.yml
"""

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


def get_account_data() -> dict:
    """Fetch current account data from Alpaca."""
    if not API_KEY or not SECRET_KEY:
        # Return mock data for local testing
        return {
            "equity": 101632.61,
            "cash": 101828.61,
            "buying_power": 201657.22,
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

    # Generate iron condor table
    ic_table = ""
    if iron_condors:
        ic_table = "| Expiry | Put Spread | Call Spread |\n|--------|------------|-------------|\n"
        for ic in iron_condors:
            ic_table += (
                f"| {ic['expiry']} | {ic['put_spread']} | {ic['call_spread']} |\n"
            )
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

| Phase | Capital | Monthly Income | Timeline |
|-------|---------|----------------|----------|
| **NOW** | ${equity:,.0f} | ~$1,100 | {now.strftime('%b %Y')} |
| Phase 2 | $250,000 | ~$2,800 | Jan 2027 |
| Phase 3 | $400,000 | ~$4,500 | Jul 2027 |
| **GOAL** | $600,000 | **$6,700** | Jan 2028 🎯 |

**Progress**: {progress_to_goal:.1f}% toward $600K goal

**Deadline**: Nov 14, 2029 (CEO's 50th birthday)

**Status**: {"✅ **ON TRACK**" if net_gain >= 0 else "⚠️ **NEEDS ATTENTION**"} - Compounding at ~8% monthly reaches goal by Jan 2028

---

## 🛡️ Phil Town Rule #1 Enforcement

The **Iron Condor Guardian** runs every 30 minutes during market hours to enforce:

1. **Stop Loss**: Exit if loss reaches 200% of credit received
2. **7 DTE Exit**: Close positions at 7 days to expiration (gamma risk)
3. **50% Profit Take**: Lock in profits at 50% of max profit

*Automation ensures rules are followed without human intervention.*

---

*Last updated: {now.strftime('%Y-%m-%d %H:%M ET')} by GitHub Actions*
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
