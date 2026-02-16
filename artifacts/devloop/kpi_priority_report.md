# KPI Priority Report

## Focus
- Focus metric: Monthly run-rate estimate
- Deficit score: 100.50
- Same-focus cycles: 93
- Stall pivot active: yes

## Ranked Gaps
- Monthly run-rate estimate: $-30.00/month [WARN] deficit=100.50
- Equity delta (2d): $-2.00 (-0.00%) [WARN] deficit=100.00
- Win Rate: 37.50% [WARN] deficit=31.82
- Max Drawdown (sync history): 0.03% [PASS] deficit=0.00
- Execution Quality (valid trade records): 97.89% [PASS] deficit=0.00
- Gateway Latency: 1626 ms [PASS] deficit=0.00
- Gateway Cost (smoke call): $0.000045 [PASS] deficit=0.00

## Recommended Tasks
- Add a run-rate promotion gate artifact that fails when monthly estimate is below $6,000 target.
- Implement one measurable strategy improvement and produce before/after run-rate artifact using same sampling window.

## Stall Pivot Tasks
- STALL PIVOT: For focus metric `Monthly run-rate estimate`, run a simulation/backtest matrix and generate artifact proving best configuration before further feature work.
- STALL PIVOT: Add an implementation-level gate test that must fail if KPI regresses versus baseline artifact.

