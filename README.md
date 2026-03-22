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

**[Progress Dashboard](https://igorganapolsky.github.io/trading/rag-query/)**

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

## Risk Rules

- Max 5% risk per position ($5,000)
- Stop-loss at 100% of credit received
- Exit at 50% profit or 7 DTE
- Max 2 iron condors open (8 legs)
- Max 2 new IC opens per day

---

**Maintained by** [Igor Ganapolsky](https://github.com/IgorGanapolsky)
