---
target: r/algotrading
status: draft
---

**Title:** What 71,417 iron condor trades on SPY taught me about automated exit rules

I've been building an open-source system that trades SPY iron condors with automated entries and exits. Before going live, I dug into projectfinance.com's study of 71,417 SPY iron condors from 2007-2017.

The data surprised me:

**Win rate by profit target:**

| Close at | Win Rate | Avg Days Held |
|----------|----------|---------------|
| 25% profit | ~92% | ~8 days |
| 50% profit | ~85% | ~14 days |
| 75% profit | ~75% | ~25 days |
| Expiration | ~68% | ~45 days |

Closing at 50% profit captures most of the premium in ~40% of the time. Holding to expiration drops the win rate to 68% and ties up capital 3x longer.

**What I implemented based on this:**
- Auto-close at 50% profit (no discretion)
- Mandatory exit at 7 DTE (gamma risk)
- Stop-loss at 100% of credit received
- 15-20 delta short strikes, $10-wide wings, 30-45 DTE
- Max 2 concurrent condors

The system uses GRPO (Group Relative Policy Optimization) to learn from closed trades and adjust delta/DTE parameters over time. Still early — only 11 closed trades so far, need 30+ before the ML kicks in.

Current result: -0.4% on $100K paper account over 30 days. Not impressive, but the safety rails held — max drawdown was 6.5% before recovering.

Code is open source: https://github.com/IgorGanapolsky/trading

Curious if anyone else has implemented automated IC management. What exit rules do you use?
