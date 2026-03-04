---
layout: post
title: "North Star Operating Strategy: Fast, Gated, Coherent"
date: 2026-02-17 13:20:00 -0500
last_modified_at: "2026-02-17"
categories: [strategy, north-star, operations]
tags: [north-star, spy, iron-condor, rag, risk-management, alpaca]
description: "Canonical operating strategy: reach $6K/month after-tax using SPY iron condors, paper-first validation, and opportunistic execution."
excerpt: "Our operating strategy is now explicit and consistent across repo, dashboard, and judge demo: fastest safe path to $6K/month with strict RAG + risk gates."
hero_image: /trading/assets/og/default-hero.png
---

## Canonical Strategy (Single Source of Truth)

- North Star: **$6K/month after-tax financial independence**
- Timing policy: **not calendar-constrained in execution**; reach the goal **as fast as safely possible**
- Core setup: **SPY iron condors**, **15-20 delta** short strikes, **$10-wide wings**, **up to 8 open option legs** (typically ~2 concurrent condors)

## Capital Allocation Policy

- **Paper account ($100K Alpaca)** is the primary validation engine.
- **Brokerage account** is traded opportunistically only when the same setup and gates pass:
  - strategy eligibility
  - risk policy checks
  - lessons-informed constraints from RAG

## Why This Matters

Coherence beats velocity theater. If the strategy text differs across repo, dashboard, and social channels, execution quality degrades. This update makes every primary surface align with one operating policy.

This operating strategy also defines what "good execution" means in day-to-day decisions. The team does not optimize for activity; it optimizes for validated outcomes. A valid setup must pass risk constraints, satisfy strategy shape, and avoid known failure modes already captured in lessons learned. If any one of those checks fails, no trade is the correct result. That discipline is the mechanism that keeps capital intact while compounding only when the edge is present.

The policy is intentionally redundant across the surfaces operators use most: internal docs, dashboards, and externally visible explainer pages. That redundancy is deliberate because drift is expensive. When definitions diverge, teams make inconsistent calls under pressure. By keeping a single canonical strategy statement and linking to auditable implementation artifacts, this page is intended to reduce interpretation risk and shorten incident triage when behavior differs from expectation.

## Answer Block

- **What is the North Star?** Reach **$6K/month after-tax** as fast as safely possible.
- **What instruments and structure are in scope?** **SPY iron condors** with 15-20 delta shorts and $10-wide wings.
- **What are hard execution constraints?** Paper-first validation, strict risk gates, and lessons-informed constraints from RAG.
- **How many legs can be open concurrently?** Up to **8 option legs** (typically about two concurrent condors).
- **How do we prevent policy drift?** Keep repo docs, dashboards, and public explainers aligned to one canonical statement and verify in CI.

## Evidence Endpoints

- Judge demo: [/trading/lessons/judge-demo.html](/trading/lessons/judge-demo.html)
- RAG query: [/trading/rag-query/](/trading/rag-query/)
- Live status: [/trading/lessons/ops-status.html](/trading/lessons/ops-status.html)
- Repo reference: https://github.com/IgorGanapolsky/trading/tree/main/docs
- Workflow reference: https://github.com/IgorGanapolsky/trading/blob/main/.github/workflows/ci.yml
