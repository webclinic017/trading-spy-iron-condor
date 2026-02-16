# Layer Expansion Report

## Decision
- Layer 1 has open items; no promotions this cycle.
- Open Layer 1 count: 4
- Candidate pool size: 7
- Promoted this cycle: 0
- Focus metric: Equity delta (1d)

## KPI Signals
- Win Rate
- Equity delta (1d)
- Monthly run-rate estimate

## Top Candidates
- Improve KPI metric: Equity delta (1d) with measurable artifact proof.
- Improve win rate with stricter entry filters and add a validation report proving >=55% over the latest sample window.
- Improve 7-day equity delta by adding one measurable strategy change and a before/after artifact.
- Increase monthly run-rate with a promotion gate tied to run-rate threshold and backtest proof artifact.
- Resolve deferred cleanup item with test coverage: scripts/reindex_rag.py:126 # Extract lesson ID (LL-XXX or ll_XXX)
- Resolve deferred cleanup item with test coverage: scripts/update_github_pages.py:66 # Pattern: | **Portfolio** | $XXX,XXX.XX | +X.XX% |
- Resolve deferred cleanup item with test coverage: scripts/ai_disclosure.py:90 - Generic placeholder numbers ($X,XXX)

## Promoted Tasks
- [x] None

## Stop Conditions
- Stop adding layers when no WARN/UNKNOWN KPI remains and no new candidates are generated.
- Otherwise continue cycle-by-cycle with max promotions per run.

