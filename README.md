# AI Trading System

[![CI](https://github.com/IgorGanapolsky/trading/actions/workflows/ci.yml/badge.svg)](https://github.com/IgorGanapolsky/trading/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11.x-blue.svg)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Autonomous AI trading system: SPY iron condors with defined risk, continuous learning, and strict safety gates.

> **North Star**: $6K/month after-tax options income via SPY iron condors.
>
> **Strategy**: 15-20 delta, $10-wide wings, 30-45 DTE. Exit at 50% profit or 7 DTE. Stop at 100% of credit.
>
> **Accounts**: Paper ($100K) validates. Live mirrors qualified setups behind risk gates.

**[Live Dashboard](https://igorganapolsky.github.io/trading/rag-query/)**

---

## System Overview

![System Overview](docs/assets/system_overview.png)

---

## Architecture

![Trading Pipeline](docs/assets/trading_pipeline.png)

![Iron Condor Payoff](docs/assets/iron_condor_payoff.png)

![Theta Decay Curve](docs/assets/theta_decay_curve.png)

---

## Quick Start

```bash
git clone https://github.com/IgorGanapolsky/trading.git
cd trading
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Configure API keys
```

```bash
pytest tests/ -q                            # Run tests
ruff check src/                             # Lint
python3 scripts/run_grpo_training.py        # Train ML brain
python3 scripts/sync_alpaca_state.py        # Sync broker state
python3 scripts/system_health_check.py      # Health check
```

---

## How We Protect Capital

Every trade has a built-in safety net. The system follows [Phil Town's Rule #1](https://www.ruleoneinvesting.com/): **don't lose money.**

- **No single trade can risk more than 5% of the portfolio** ($5,000 on a $100K account). This means even a worst-case loss on one position won't materially damage the account.
- **Every iron condor has an automatic stop-loss at 100% of the credit received.** If a trade goes against us, the system closes it before losses exceed the premium collected.
- **Profits are taken at 50%, or positions close at 7 days to expiration** — whichever comes first. This locks in gains while theta decay is strongest and avoids gamma risk near expiry.
- **Maximum 2 iron condors open at any time** (8 option legs). This keeps exposure manageable and prevents over-concentration.
- **The system limits itself to 2 new iron condor opens per day**, preventing the rapid open-close cycling that was eating capital in spread costs.

---

**Maintained by** [Igor Ganapolsky](https://github.com/IgorGanapolsky)
