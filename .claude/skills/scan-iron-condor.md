# Scan Iron Condor Skill

Manually trigger the iron condor scanner to find entry opportunities.

## Trigger

`/scan-iron-condor`

## What It Does

1. Checks current positions (max 2 ICs allowed)
2. Gets current SPY price
3. Checks VIX conditions
4. Calculates optimal strikes (15-20 delta, 30-45 DTE)
5. Creates GitHub issue for approval with auto-execute

## Usage

```
/scan-iron-condor          # Scan and create alert
/scan-iron-condor --dry-run  # Scan without alert
```

## Output

- Opportunity details (expiry, strikes, credit, risk)
- GitHub issue link for approval
- Auto-execute timer (30 min)

## Entry Criteria

- SPY only
- 30-45 DTE
- 15-20 delta short strikes
- $5-wide wings
- VIX favorable (15-25)
- Max 2 positions

## Instructions

When user invokes this skill:

1. Run `python scripts/iron_condor_scanner.py`
2. Report the opportunity found (or why none found)
3. Provide the GitHub issue link if created
