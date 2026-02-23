# 🤖 AI Trading System Wiki

Welcome to the **AI-Powered Automated Trading System** wiki!

---

## 📊 [Progress Dashboard](Progress-Dashboard)

**👉 [View Live Progress Dashboard →](https://igorganapolsky.github.io/trading/)**

The system tracks progress toward validated autonomous trading:
- North Star goal: **Validated iron condor system → consistent $500/month on $25K+ capital**
- Current strategy: **Iron Condors on SPY** (minimum $10K capital, code-enforced)
- Phil Town Rule #1: **Don't lose money**

---

## 🚀 Quick Links

### Documentation
- [CLAUDE.md](https://github.com/IgorGanapolsky/trading/blob/main/.claude/CLAUDE.md) - Strategy & directives
- [System State](https://github.com/IgorGanapolsky/trading/blob/main/data/system_state.json) - Live account data

### System Status
- [GitHub Actions](https://github.com/IgorGanapolsky/trading/actions) - Execution logs
- [RAG Chat](https://igorganapolsky.github.io/trading/rag-query/) - Query lessons learned
- [Judge Demo Evidence](https://igorganapolsky.github.io/trading/lessons/judge-demo.html) - TARS routing proof & readiness metrics

### Key Features
- **Iron Condor Guardian**: Automated Rule #1 enforcement (stop loss, 7 DTE exit, 50% profit take)
- **RLHF System**: Thompson Sampling + ShieldCortex memory
- **CI/CD**: 1300+ tests, self-healing workflows
- **Multi-Agent Swarm**: Analysis, execution, and monitoring agents

---

## 📈 Current Status (Feb 16, 2026)

| Metric | Value |
|--------|-------|
| **Account Equity** | $101,441.56 |
| **Starting Capital** | $100,000 (Jan 30, 2026) |
| **Net Gain** | $+1,441.56 (+1.44%) |
| **Open Positions** | 1 Iron Condor(s) |
| **Strategy** | SPY Iron Condors (15-20 delta) |

### Open Iron Condors
| Expiry | Put Spread | Call Spread |
|--------|------------|-------------|
| Mar 13, 2026 | 650/655 | 725/730 |

---

## 🎯 North Star Goal

**Vision**: Validated autonomous trading system generating **$6,000/month after-tax passive income**.

**Financial Roadmap** (Reverse-engineered from $6K Net):
- **Target**: $6,000/mo Net ≈ **$8,600/mo Gross** (assuming ~30% tax).
- **Yield**: Target 2.5% monthly return (conservative for Iron Condors + Credit Spreads).
- **Capital Required**: ~$350,000 deployed capital.

| Phase | Timeline | Target | Status |
|-------|----------|--------|--------|
| **Phase 1: Validate** | Now → Jun 2026 | 30 trades, >85% win rate on $100K paper | 🔄 In progress (1/30) |
| **Phase 2: Scale** | Jul → Dec 2026 | Reach $150K capital, generate $3,000/mo gross | ⏳ Pending |
| **Phase 3: Dominate** | 2027 | Scale to $350K+, achieve **$8,600/mo gross** | ⏳ Pending |
| **Phase 4: Productize** | 2028 | Packaged system for HNW accounts ($250K+) | ⏳ Pending |

**Strategy Parameters** (updated Feb 2026 — positive EV):
- Profit target: **50%** of max profit (high velocity)
- Stop loss: **200%** of credit (statistical management)
- Expected value per trade: **+$140** at 15-delta (85% probability)

---

## 🛡️ Phil Town Rule #1 Enforcement

The **Iron Condor Guardian** runs every 30 minutes during market hours to enforce:

1. **Stop Loss**: Exit if loss reaches 200% of credit received
2. **7 DTE Exit**: Close positions at 7 days to expiration (gamma risk)
3. **50% Profit Take**: Lock in profits at 50% of max profit

*Automation ensures rules are followed without human intervention.*

---

*Last updated: 2026-02-16 14:33 ET by GitHub Actions*
