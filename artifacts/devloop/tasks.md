# Layered Task Backlog

## Gate Status
- Lint: PASS
- Tests: PASS

## Layer 1: Red Build/Test Failures
- [ ] MANUAL: Add a promotion gate artifact that blocks strategy promotion when win rate/run-rate thresholds are below target.
- [ ] MANUAL: Add automated weekly delta section (7d and 30d) with warning flags for flat/negative run-rate.
- [ ] MANUAL: Add demo evidence index page linking all `artifacts/tars/*` and `artifacts/devloop/*` outputs for judges.
- [ ] MANUAL: Add expectancy metrics (profit factor, avg winner, avg loser) to `scripts/generate_profit_readiness_scorecard.py`.

## Completed Since Last Iteration
- [x] None

## Layer 2: High-Impact Files
- None

## Layer 3: Deferred Cleanup
- scripts/reindex_rag.py:126 # Extract lesson ID (LL-XXX or ll_XXX)
- scripts/update_github_pages.py:66 # Pattern: | **Portfolio** | $XXX,XXX.XX | +X.XX% |
- scripts/ai_disclosure.py:90 - Generic placeholder numbers ($X,XXX)
- scripts/validate_ticker_whitelist.py:66 _approved = get_approved_tickers_from_claude_md()  # TODO: Use for whitelist validation
- scripts/generate_layered_tasks.py:108 or "TODO:" in stripped
- scripts/generate_layered_tasks.py:109 or "FIXME:" in stripped
- scripts/execute_options_trade.py:587 # TODO: Implement call option finding similar to put finding
- scripts/phil_town_ml_trader.py:83 # TODO: Add ML model that learns optimal entry timing
- scripts/phil_town_ml_trader.py:105 # TODO: Call actual iron condor scanner and executor
- scripts/phil_town_ml_trader.py:106 print("\n⏳ TODO: Integrate with iron_condor_scanner.py")
- src/memory/document_aware_rag.py:498 # Extract lesson ID (LL-XXX or ll_XXX)
- src/execution/alpaca_executor.py:116 # TODO: Enhance with actual market features from RLFilter
- .github/workflows/ci.yml:116 # TODO: Increase to 40% then 70% as more tests are added

## Next Loop Protocol
1. Pick one unchecked Layer 1 item and implement a minimal fix.
2. Re-run lint/tests.
3. Regenerate this file; resolved Layer 1 items auto-move to checked.
4. Repeat until Layer 1 is fully checked.

