---
layout: home
title: Building an AI Trading System in Public
---

This is the unfiltered story of building an autonomous AI trading system—every bug, every breakthrough, every lesson learned.

**The goal:** $6,000/month passive income through disciplined iron condor trading on SPY.

**The method:** A full autonomous stack where each layer has a strict role:

- **Signal + market data layer**: Alpaca + macro/news inputs feed the orchestrator.
- **Decision layer**: Claude Opus handles trade-critical reasoning; TARS/OpenRouter route non-critical tasks for cost control.
- **Memory layer**: LanceDB RAG retrieves prior failures and lessons before trade and code decisions.
- **Execution layer**: Orchestrator + trade gateway enforce SPY-only, sizing, entry/exit, and stop-loss policies before orders hit Alpaca.
- **Risk layer**: Hard gates (position limits, drawdown controls, pre-trade smoke tests, mandatory checklists) block unsafe actions.
- **Reliability layer**: Ralph Mode and CI workflows continuously test, repair, and document the system.

Full architecture: **[Tech Stack](/trading/tech-stack/)**.

## How This Reaches North Star (By Nov 14, 2029)

North Star in `.claude/CLAUDE.md`: grow from **$100K to $600K**, then operate at **$6,000/month after-tax** by **November 14, 2029**.

### Phase 1: Validation (Now -> 2026-05-31)
- Complete 90-day paper validation with the current SPY iron condor rules.
- Required gate to move forward: stable risk behavior + passing North Star gate logic.

### Phase 2: Controlled Live Pilot (2026-06-01 -> 2026-12-31)
- Transition to live only after Phase 1 gates pass.
- Keep strict risk caps (5% max position risk, defined exits/stops, no ticker drift).
- Objective: prove process discipline under live execution constraints.

### Phase 3: Controlled Scaling (2027-01-01 -> 2028-12-31)
- Scale only when rolling performance/risk gates remain green.
- Continue closed learning loop: trade outcome -> RAG lesson -> policy update -> retest -> redeploy.
- Objective: increase capital efficiency without increasing rule violations.

### Phase 4: Income Conversion (2029-01-01 -> 2029-11-14)
- Operate at target capital and convert risk-adjusted option premium into monthly cashflow.
- Maintain CI/risk reliability as a hard precondition to protect compounding.
- Target outcome date: **November 14, 2029**.

---

## Where We Are Today

<!-- AUTO_STATUS_START -->
_Last Sync: 2026-02-16 14:40 UTC (source: `data/system_state.json`)_

| What | Status |
| ---- | ------ |
| Account Equity | $101,441.56 |
| Daily P/L | +$0.00 |
| Win Rate | 100.0% (1 trades; target 80.0%) |
| Paper Phase | Day 14/90 |
| North Star Gate | ACTIVE (VALIDATING) |
| Open Positions | 1 structure(s), 4 option leg(s) |
| Unrealized P/L | +$2.00 |

**Execution Focus:** Do not scale risk until validation passes.
<!-- AUTO_STATUS_END -->

This section is auto-updated from `data/system_state.json` by `scripts/update_docs_index.py` via GitHub Actions.

---

## The Story So Far

### The Silent 74 Days (Nov 1 - Jan 12)

For 74 days, our system showed green dashboards while executing zero trades. [Read the full post-mortem](/trading/2026/01/07/the-silent-74-days.html)—it's one of those engineering failures you learn from.

### First Trades (Jan 13)

We finally executed trades. Bought SOFI. Learned why individual stocks are riskier than index ETFs.

### Strategy Pivot (Jan 15-19)

After getting burned on SOFI, we pivoted to SPY-only iron condors. The math:

- Individual stocks: Unpredictable, earnings risk, wide spreads
- SPY iron condors: 86% win rate, defined risk, best liquidity

### Ralph Mode Activated (Jan 22)

The system now heals itself. CI workflows detect issues, apply fixes, and document discoveries automatically. [See today's discoveries](/trading/2026/01/24/ralph-discovery.html).

### Fresh Start (Jan 22)

Reset to $30K. Clean slate. No PDT restrictions.

### Scaled to $100K (Jan 30)

Upgraded to $100K paper account for more realistic position sizing. Target: prove 80%+ win rate before live trading.

---

## Featured Posts

### Must-Read

- **[The Silent 74 Days](/trading/2026/01/07/the-silent-74-days.html)** - How we built a system that did nothing
- **[Complete Iron Condor Guide](/trading/2026/01/21/iron-condors-ai-trading-complete-guide.html)** - Our full strategy and tech stack
- **[The Position Stacking Disaster](/trading/2026/01/22/position-stacking-disaster-fix.html)** - A bug that cost $1,472 in paper trading

### Recent Updates

{% for post in site.posts limit:5 %}

- [{{ post.title }}]({{ post.url | relative_url }}) <small>({{ post.date | date: "%b %d" }})</small>
  {% endfor %}

[View all posts →](/trading/posts/)

---

## Follow the Journey

- **[GitHub Repository](https://github.com/IgorGanapolsky/trading)** - Full source code, issues, and PRs
- **[GitHub Actions](https://github.com/IgorGanapolsky/trading/actions)** - Watch autonomous workflows run in real-time
- **[Judge Demo Evidence]({{ "/lessons/judge-demo.html" | relative_url }})** - Clean, visual summary of proof artifacts and system status

Every trade gets recorded. Every bug gets documented. Every lesson goes into our [RAG knowledge base](/trading/rag-query/) (300+ lessons searchable).

---

_Built by Igor Ganapolsky (CEO) with Claude-powered autonomous agents, including Ralph Mode._
