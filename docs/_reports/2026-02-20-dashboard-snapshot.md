---
layout: "post"
title: "Daily Dashboard Snapshot - 2026-02-20"
description: "Daily snapshot for 2026-02-20: paper equity $101,272.00, paper daily P/L $-93.40, cadence gate FAIL."
date: "2026-02-20"
last_modified_at: "2026-02-20"
tags:
  - "dashboard"
  - "north-star"
  - "ai-discoverability"
  - "ops"
image: "/assets/og-image.png"
canonical_url: "https://igorganapolsky.github.io/trading/reports/2026-02-20-dashboard-snapshot/"
faq: true
questions:
  - question: "What is the current state of the trading system today?"
    answer: "Daily snapshot for 2026-02-20: paper equity $101,272.00, paper daily P/L $-93.40, cadence gate FAIL."
  - question: "Are cadence and risk gates passing this week?"
    answer: "Cadence gate is FAIL. Risk mode is validation with recommended max position size 0.0%."
  - question: "What is the North Star probability right now?"
    answer: "North Star probability is 44.10% (low), monthly target $6,000.00 with progress 1.02%."
---
# Daily Dashboard Snapshot | 2026-02-20

This report is auto-generated from system state for search and AI discoverability.

## Answer Block

**Q: Did we make money today?**<br>
A: Paper daily P/L is $-93.40. Live account total P/L is $188.69.

**Q: Are we on track toward the North Star?**<br>
A: North Star probability is 44.10% (low), monthly target $6,000.00 with progress 1.02%.

**Q: Is execution cadence healthy?**<br>
A: Weekly cadence KPI is **FAIL** with risk mode **validation**.

## No-Trade Diagnostic (Why We Did Not Trade)

- Decision records observed (lookback window): `0`

### Top Rejection Reasons

- none

## KPI Snapshot

| Metric | Value |
|---|---|
| Live Equity | $208.69 |
| Live Total P/L | $188.69 (943.45%) |
| Paper Equity | $101,272.00 |
| Paper Total P/L | $1,272.00 (1.27%) |
| Paper Daily Change | $-93.40 |
| Paper Win Rate | 100.00% (sample: 1) |
| Open Positions (Paper) | 4 |
| Weekly Cadence KPI | FAIL |
| Weekly Risk Mode | validation |
| Recommended Max Position Size | 0.01% |
| North Star Probability | 44.10% (low) |

## Evidence

- [System state source](https://github.com/IgorGanapolsky/trading/blob/main/data/system_state.json)
- [Dashboard source markdown](https://github.com/IgorGanapolsky/trading/blob/main/wiki/Progress-Dashboard.md)
- [Cadence gate checker](https://github.com/IgorGanapolsky/trading/blob/main/scripts/check_weekly_cadence_gate.py)
- [North Star operating plan updater](https://github.com/IgorGanapolsky/trading/blob/main/scripts/update_north_star_operating_plan.py)
- [Live site dashboard](https://igorganapolsky.github.io/trading/)

## Data Freshness

- Snapshot date: `2026-02-20`
- Live account sync timestamp: `2026-02-20T17:11:57.494303`
