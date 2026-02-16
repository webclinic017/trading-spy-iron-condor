# Morning Devloop Report

- Generated (UTC): 2026-02-16T03:32:19Z

## KPI Focus
- Focus metric: Equity delta (1d)
- Deficit: 100.00
- Stall pivot active: no

## Profit Readiness Snapshot
- Win Rate: 37.50% [WARN] (sample_size=32)
- Monthly run-rate estimate: $0.00/month [WARN]
- Max Drawdown: 0.03% [PASS] (equity_points=24)

## RAG Snapshot
- PASS (reindex_exit=0, query_index_exit=0).

## Layer 1 Open Tasks
- [ ] MANUAL: Add a promotion gate artifact that blocks strategy promotion when win rate/run-rate thresholds are below target.
- [ ] MANUAL: Add automated weekly delta section (7d and 30d) with warning flags for flat/negative run-rate.
- [ ] MANUAL: Add demo evidence index page linking all `artifacts/tars/*` and `artifacts/devloop/*` outputs for judges.
- [ ] MANUAL: Add expectancy metrics (profit factor, avg winner, avg loser) to `scripts/generate_profit_readiness_scorecard.py`.

## Last Log Lines
- `[2026-02-16T03:28:47Z] bootstrap start`
- `bootstrap complete: /Users/joeyrahme/GitHubWorkspace/trading/.venv-devloop`
- `profile: profit`
- `ruff cmd: /Users/joeyrahme/GitHubWorkspace/trading/.venv-devloop/bin/ruff check src/orchestrator src/risk src/trading src/execution src/llm scripts --select=E9,F63,F7,F82`
- `pytest cmd: /Users/joeyrahme/GitHubWorkspace/trading/.venv-devloop/bin/pytest tests/test_orchestrator_main.py tests/test_trade_gateway.py tests/test_risk_manager.py tests/test_pre_trade_checklist.py tests/test_options_executor_smoke.py tests/test_trade_opinion.py -q --maxfail=25 --tb=short`
- `[2026-02-16T03:28:49Z] bootstrap done`
- `[2026-02-16T03:28:49Z] cycle=1 profile=profit analyze start`
- `[2026-02-16T03:28:50Z] iteration=1`
- `iteration 1: green`
- `[2026-02-16T03:29:11Z] cycle=1 profile=profit analyze done`
- `ok: scorecard generated -> artifacts/devloop/profit_readiness_scorecard.md`
- `ok: kpi priority report -> artifacts/devloop/kpi_priority_report.md`
- `ok: kpi priority json -> artifacts/devloop/kpi_priority.json`
- `focus_metric=Equity delta (1d)`
- `stall_pivot=0`
- `ok: layer expansion report -> artifacts/devloop/layer_expansion_report.md`
- `promoted_count=0`
- `ok: kpi page generated -> /Users/joeyrahme/GitHubWorkspace/trading/artifacts/devloop/kpi_page.md`
- `ok: generated -> /Users/joeyrahme/GitHubWorkspace/trading/artifacts/devloop/next_copilot_prompt.md`
- `[2026-02-16T03:29:11Z] sleeping 300s`

