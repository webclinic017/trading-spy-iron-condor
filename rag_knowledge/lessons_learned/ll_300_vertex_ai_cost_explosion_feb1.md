# LL-300: Vertex AI Cost Explosion - $98/mo vs $20/mo Budget

**Date**: February 1, 2026
**Severity**: CRITICAL
**Category**: Cost Management

## Problem

Google Cloud bill hit $98.70/month when budget was $20/month - 5x over budget.

## Root Cause

Multiple workflows calling Vertex AI RAG APIs:

1. `enforce-phil-town-completeness.yml` - Every push + 2x daily schedule
2. `phil-town-ingestion.yml` - Daily weekdays (ingesting YouTube + blogs)
3. `daily-trading.yml` - Multiple RAG calls per trading day:
   - `pretrade-rag-query` job
   - `pre_session_rag_check.py`
   - `record_account_to_rag.py`
   - `sync_trades_to_rag.py`
4. Dialogflow webhook (Cloud Run) - Every voice query uses Vertex RAG

## Vertex AI Cost Breakdown (Estimated)

| Component              | Frequency           | Est. Monthly Cost |
| ---------------------- | ------------------- | ----------------- |
| RAG Query API          | ~100 calls/day      | $30-40            |
| Text Embeddings        | ~500/day            | $10-15            |
| Datastore storage      | Ongoing             | $10-20            |
| Cloud Run (webhook)    | ~50 requests/day    | $5-10             |
| YouTube/Blog ingestion | Daily vectorization | $15-20            |

## Resolution

Disabled all automated Vertex AI RAG calls in GitHub Actions:

1. `enforce-phil-town-completeness.yml` - Disabled auto-triggers (manual only)
2. `phil-town-ingestion.yml` - Disabled schedule (manual only)
3. `daily-trading.yml`:
   - Disabled `pretrade-rag-query` job
   - Disabled `pre_session_rag_check.py`
   - Disabled `record_account_to_rag.py`
   - Disabled `sync_trades_to_rag.py`

## Alternative Approach

Use **local file-based storage** instead of Vertex AI:

- Trade history: `data/system_state.json` (already works)
- Lessons learned: `rag_knowledge/lessons_learned/*.md` (local search)
- Account balances: Can add to `system_state.json`

## Budget Protection

Going forward:

- Set GCP budget alert at $15/month
- Manual Vertex AI syncs only when truly needed
- Monitor GCP billing weekly

## CEO Action Required

Go to Google Cloud Console and set a budget alert:

1. Navigation > Billing > Budgets & alerts
2. Create budget: $20/month
3. Set alert thresholds: 50%, 90%, 100%
4. Email notification to your account

## Prevention

- ALWAYS calculate API costs BEFORE enabling automated workflows
- Prefer local storage over cloud APIs for high-frequency operations
- Review GCP billing weekly

## References

- GCP Bill: $98.70 (Feb 1, 2026)
- Budget: $20/month
