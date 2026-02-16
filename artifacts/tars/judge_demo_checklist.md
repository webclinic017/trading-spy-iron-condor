# Judge Demo Checklist

## Must-Have Evidence
- [x] Gateway environment captured
- [x] Smoke response recorded
- [x] Smoke response includes completion choices
- [x] Resilience report recorded
- [x] Resilience report observed error-path signal
- [x] Retrieval report recorded
- [x] Submission summary generated
- [x] Latency/cost metrics captured

## Claim -> Evidence Mapping
- Routed model call works -> `artifacts/tars/smoke_response.json`
- Failure path is handled -> `artifacts/tars/resilience_report.txt`
- Retrieval/memory readiness -> `artifacts/tars/retrieval_report.txt`
- Config + run summary -> `artifacts/tars/env_status.txt`, `artifacts/tars/submission_summary.md`

## Live Demo Sequence
1. Open `submission_summary.md` and state the claims.
2. Show `smoke_response.json` and point to completion choices.
3. Show `resilience_report.txt` and explain fallback/error-path behavior.
4. Show `retrieval_report.txt` and describe memory/retrieval readiness.
5. Show `smoke_metrics.txt` for latency/token/cost context.

