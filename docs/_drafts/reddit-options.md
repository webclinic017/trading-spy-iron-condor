---
target: r/options
status: draft
---

**Title:** Data from 71K iron condor trades: why I close at 50% profit instead of holding to expiration

I see a lot of posts about whether to close iron condors early or let them expire. I found a study that settles it with data — 71,417 SPY iron condors from 2007-2017.

**The short version:** closing at 50% profit gives you ~85% win rate and frees up capital 3x faster than holding to expiration (~68% win rate).

**The full breakdown:**

Two setups tested:
- 16-delta short / 5-delta long (40,868 trades)
- 30-delta short / 16-delta long (30,549 trades)

For the 16-delta setup (similar to what most of us trade):

| Close at | Win Rate | Avg Days Held |
|----------|----------|---------------|
| 25% | ~92% | ~8 days |
| 50% | ~85% | ~14 days |
| 75% | ~75% | ~25 days |
| Expiration | ~68% | ~45 days |

The math on capital efficiency is what really sold me. With 50% targets you can turn capital 24-36x per year vs 12x holding to expiration. More at-bats = more compounding.

**VIX matters too.** 30-delta condors during VIX > 20 significantly outperformed all other regimes. Below VIX 15, premiums are too thin to bother.

I built an automated system around these rules:
- 15-20 delta, $10-wide wings on SPY
- Close at 50% profit or 7 DTE (whichever first)
- Stop at 100% of credit
- Max 2 concurrent condors

Running it on $100K paper for the last month. Down 0.4% — the drawdown hit 6.5% during the March selloff but recovered. Safety rails working as designed.

Source: [projectfinance.com iron condor management study](https://www.projectfinance.com/iron-condor-management/)

If you trade ICs — what's your profit target? And do you adjust for VIX level?
