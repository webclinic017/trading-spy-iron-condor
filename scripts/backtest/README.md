# Off-Market Backtesting System

## Overview

This system runs bull put spread simulations during evenings, weekends, and holidays when the market is closed. The goal is to **accelerate learning** and **find mistakes before they cost real money**.

## Quick Start

### Manual Run (via GitHub Actions)

1. Go to **Actions** → **Off-Market Backtesting**
2. Click **Run workflow**
3. Choose options:
   - `days`: Number of days to backtest (default: 30)
   - `parameter_sweep`: Enable to test multiple parameter combinations
   - `max_combinations`: How many parameter combos to test

### Automatic Schedule

| Time    | Day      | What Runs                         |
| ------- | -------- | --------------------------------- |
| 6 PM ET | Mon-Fri  | 30-day backtest                   |
| 8 AM ET | Saturday | 60-day backtest + parameter sweep |
| 8 AM ET | Sunday   | 60-day backtest                   |

## Files

```
scripts/backtest/
├── bull_put_spread_backtester.py  # Main backtest engine
├── parameter_sweep.py              # Parameter optimization
├── ingest_backtest_to_rag.py       # RAG database integration
├── check_market_hours.py           # Market hours checker
└── README.md                       # This file

data/backtests/
├── latest_summary.json             # Most recent backtest summary
├── backtest_summary_*.json         # Individual run summaries
├── backtest_results_*.json         # Detailed trade results
├── backtest_lessons_*.json         # Generated RAG lessons
└── parameter_sweeps/               # Parameter optimization results
```

## Configuration

### Default Parameters

| Parameter                    | Default | Description                |
| ---------------------------- | ------- | -------------------------- |
| `short_put_delta_min`        | -0.60   | Short put minimum delta    |
| `short_put_delta_max`        | -0.20   | Short put maximum delta    |
| `long_put_delta_min`         | -0.40   | Long put minimum delta     |
| `long_put_delta_max`         | -0.20   | Long put maximum delta     |
| `spread_width_min`           | $2.00   | Minimum spread width       |
| `spread_width_max`           | $4.00   | Maximum spread width       |
| `target_profit_pct`          | 50%     | Take profit at % of credit |
| `delta_stop_loss_multiplier` | 2.0x    | Stop when delta doubles    |

### Custom Config

Create a JSON file and pass it:

```bash
python scripts/backtest/bull_put_spread_backtester.py --config my_config.json
```

```json
{
  "short_put_delta_min": -0.5,
  "short_put_delta_max": -0.25,
  "target_profit_pct": 0.75
}
```

## RAG Integration

Every backtest generates lessons that are:

1. Saved to `data/backtests/backtest_lessons_*.json`
2. Formatted for RAG in `data/rag_staging/`
3. Ingested to Vertex AI RAG (when configured)

### Lesson Types

- **BACKTEST_SUMMARY**: Overall performance metrics
- **FAILURE_MODE**: Analysis of losing trades
- **PARAMETER_OPTIMIZATION**: Best parameter combinations found

## Metrics Tracked

### Performance

- Total P&L
- Win Rate
- Average Trade
- Sharpe Ratio
- Max Drawdown

### Strategy Health

- Parameter stability over time
- Regime detection (when strategy fails)
- Trade execution quality

## Troubleshooting

### "No data available for date range"

Alpaca may not have data for the requested dates. Try:

- Reducing the date range
- Using more recent dates

### "Market is OPEN - skipping backtest"

The workflow detected market hours. Wait until:

- After 4 PM ET on weekdays
- Weekend (any time)
- Market holiday

### Missing RAG lessons

Check that `GOOGLE_CLOUD_PROJECT` secret is set in GitHub repository settings.

## Phil Town Rule #1 Alignment

This system embodies Phil Town's principles:

1. **Never lose money** → Stop loss at 2x delta
2. **Never forget rule #1** → Daily backtesting finds mistakes early
3. **Buy wonderful companies** → SPY is the market itself
4. **Buy at attractive prices** → Bull put spreads collect premium

## Resources

- [Alpaca 0DTE Backtesting Guide](https://alpaca.markets/learn/backtesting-zero-dte-bull-put-spread-options-strategy-with-python)
- [Phil Town Rule #1 Investing](https://www.ruleoneinvesting.com/)
- [Bull Put Spread Strategy](https://alpaca.markets/learn/bull-put-spread)
