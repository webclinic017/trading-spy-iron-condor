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

**[Progress Dashboard](https://github.com/IgorGanapolsky/trading/wiki/Progress-Dashboard)** | **[RAG Query](https://igorganapolsky.github.io/trading/rag-query/)**

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

## Risk Management

| Rule | Value |
|---|---|
| Max risk per position | 5% ($5,000) |
| Stop-loss | 100% of credit, no exceptions |
| Exit | 50% profit OR 7 DTE |
| Max open legs | 8 (~2 iron condors) |
| Daily IC open limit | 2 (anti-churn) |

---

## Disclaimer

**Educational purposes only.** Trading involves significant risk. Past performance does not guarantee future results. Not financial advice.

---

**Maintained by** [Igor Ganapolsky](https://github.com/IgorGanapolsky)
