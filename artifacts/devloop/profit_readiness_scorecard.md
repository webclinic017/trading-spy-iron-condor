# Profit Readiness Scorecard

## Gate Health
- lint_exit: 0
- test_exit: 0

## Metrics
- Win Rate: 37.50% [WARN] (sample_size=32)
- Max Drawdown (sync history): 0.03% [PASS] (equity_points=24)
- Execution Quality (valid trade records): 97.89% [PASS] (valid=93/95)
- Gateway Latency: 897 ms [PASS] (from artifacts/tars/smoke_metrics.txt)
- Gateway Cost (smoke call): $0.000045 [PASS] (set TARS_INPUT_COST_PER_1M and TARS_OUTPUT_COST_PER_1M for estimate)

## 7-Day Delta
- Equity delta (1d): $0.00 (0.00%) [WARN]
- Monthly run-rate estimate: $0.00/month [WARN]
- Data source: sync_health.history
- North Star target: $6,000/month after tax

## Interpretation
- PASS means metric is within current readiness threshold.
- WARN means metric needs improvement before scaling risk.
- UNKNOWN means data is not yet captured for this metric.

