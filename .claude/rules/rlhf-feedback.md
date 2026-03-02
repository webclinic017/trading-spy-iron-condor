# RLHF Feedback Pipeline

## Signal Detection

- Thumbs up/down → Intensity 4
- Positive/negative words → Intensity 3
- Strong frustration (!!!) → Intensity 5 (CRITICAL)

## Success Metrics

Computed by `scripts/rlhf_metrics.py`.

Targets:
- Satisfaction rate >= 70%
- Last 7d satisfaction rate >= 60%
- MemAlign sync rate >= 0.90
- Pending ShieldCortex sync entries == 0

## On Negative Feedback

1. STOP current work
2. Record lesson with severity + context
3. Extract correction pattern ("I said X", "should be X")
4. Inject into session mistakes file
5. Apologize and course-correct
