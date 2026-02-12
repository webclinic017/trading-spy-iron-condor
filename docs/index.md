---
layout: home
title: Ralph Mode - Building an AI Trading System in Public
---

# Building an AI Trading System in Public

This is the unfiltered story of building an autonomous AI trading system—every bug, every breakthrough, every lesson learned.

**The goal:** $6,000/month passive income through disciplined iron condor trading on SPY.

**The method:** Claude Opus 4.5 as CTO, running 24/7 autonomous operations using the [Ralph Wiggum iterative coding technique](https://github.com/Th0rgal/opencode-ralph-wiggum).

---

<!-- AUTO_STATUS_START -->
## Where We Are Today (Thursday, February 12, 2026)

Day 107 since project start (initial paper-phase target: 90 days).

| What | Status |
| --- | --- |
| Account Equity | $101,445.56 |
| Daily P/L | -$8.00 (-0.01%) |
| Strategy | Iron Condors on SPY |
| Open Positions | 1 iron condor (4 option legs) |
| Position P/L | +$6.00 |
| Win Rate | 37.5% (32 trades) |
| Last Sync | 2026-02-12 20:14 UTC |

Source of truth: [data/system_state.json](https://github.com/IgorGanapolsky/trading/blob/main/data/system_state.json)
<!-- AUTO_STATUS_END -->

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
- **[GitHub Actions](https://github.com/IgorGanapolsky/trading/actions)** - Watch Ralph work in real-time

Every trade gets recorded. Every bug gets documented. Every lesson goes into our [RAG knowledge base](/trading/rag-query/) (300+ lessons searchable).

---

_Built by Igor Ganapolsky (CEO) & Ralph (AI CTO) - Powered by Claude Opus 4.5_
