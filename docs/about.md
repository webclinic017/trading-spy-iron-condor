---
layout: page
title: About
permalink: /about/
description: "Building autonomous AI trading systems with iron condors - the journey from $100K to financial independence"
---

# About This Project

## The Mission

Build a profitable, autonomous AI trading system that generates **$6,000/month in passive income** through systematic options trading.

**Timeline:** November 14, 2029 (financial independence target)
**Strategy:** Iron condor credit spreads on SPY
**Capital:** Growing $100K → $600K

## The Team

**Igor Ganapolsky** — CEO & System Architect
Mobile engineer turned algorithmic trader. Building AI-powered trading systems that combine Claude Opus/Sonnet with systematic options strategies.

**Claude (CTO)** — Autonomous AI Agent
Handles strategy execution, risk management, CI/CD, and continuous learning through RLHF (Reinforcement Learning from Human Feedback).

## The Strategy

### Iron Condors on SPY

- **What:** Simultaneous bull put spread + bear call spread
- **Delta:** 15-20 delta on short strikes (86% win rate)
- **Expiry:** 30-45 DTE (days to expiration)
- **Position size:** Max 5% per trade ($5,000 risk)
- **Exit:** 50% max profit OR 7 DTE
- **Stop-loss:** 200% of credit received

### Phil Town Rule #1

> "Don't lose money."

Every trade is gated by:
- Defined risk on BOTH sides
- Position sizing limits
- Stop-loss enforcement
- No naked options, ever

## The Tech Stack

- **AI:** Claude 4.6 Opus, Claude 4.5 Sonnet
- **Broker:** Alpaca Markets (paper + live)
- **Backend:** Python 3.11, FastAPI
- **Memory:** LanceDB (vector), RAG (lessons learned)
- **CI/CD:** GitHub Actions (100+ workflows)
- **Learning:** Thompson Sampling + RLHF

## Why Public?

**Accountability.** Publishing lessons learned forces honesty about what works and what doesn't.

**Learning.** The system gets smarter through feedback loops:
1. Trade executes (or fails)
2. Lesson recorded in RAG
3. Future decisions weighted by past outcomes (Thompson Sampling)
4. CEO feedback adjusts strategy (RLHF)

**Community.** If you're building autonomous trading systems or learning options, these lessons might save you time (and money).

## Current Status

- **Account:** $100K paper (Alpaca PA3C5AG0CECQ)
- **Strategy:** Iron condors on SPY only
- **Win rate target:** 85%+ (15-delta = 86% probability of profit)
- **Phase:** Paper trading (proving system before live)

## Contact

- **GitHub:** [IgorGanapolsky](https://github.com/IgorGanapolsky)
- **LinkedIn:** [igorganapolsky](https://linkedin.com/in/igorganapolsky)
- **Dev.to:** [@igorganapolsky](https://dev.to/igorganapolsky)

---

*This blog documents the journey, mistakes, and lessons. Not financial advice. Options trading carries risk. Trade paper until you're profitable.*
