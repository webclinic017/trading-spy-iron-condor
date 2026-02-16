# KPI Page

## Snapshot
- Demo checklist completion: 8/8
- Readiness metrics: PASS=4, WARN=1, UNKNOWN=0

## Reliability
- Dev loop status: `artifacts/devloop/tasks.md`
- Scorecard: `artifacts/devloop/profit_readiness_scorecard.md`

## Business Readiness
- Win Rate: 37.50% [WARN]
- Max Drawdown (sync history): 0.03% [PASS]
- Execution Quality (valid trade records): 97.89% [PASS]
- Gateway Latency: 897 ms [PASS]
- Gateway Cost (smoke call): $0.000045 [PASS]

## 7-Day Trend
- Equity delta (1d): $0.00 (0.00%) [WARN]
- Monthly run-rate estimate: $0.00/month [WARN]
- Data source: sync_health.history
- North Star target: $6,000/month after tax

## Demo Readiness
- Judge checklist: `artifacts/tars/judge_demo_checklist.md`
- Submission summary: `artifacts/tars/submission_summary.md`
- Smoke metrics: `artifacts/tars/smoke_metrics.txt`

## Next Actions
1. Clear WARN metrics in scorecard, starting with win rate/run-rate.
2. Keep checklist at 100% before demo/submission.
3. Re-run `./scripts/layered_tdd_loop.sh run` after every meaningful change.

