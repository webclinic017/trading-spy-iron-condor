# Next Copilot Prompt

Copy/paste this into Copilot Chat (Agent mode):

```text
Read `.github/copilot-instructions.md` and `artifacts/devloop/tasks.md`.
Pick exactly one unchecked Layer 1 item and do a minimal fix.
Run `./scripts/layered_tdd_loop.sh analyze` after the change.
Update only necessary files and keep diffs surgical.
If Layer 1 is empty and checks are green, pick one open item from `manual_layer1_tasks.md`.
Target item: MANUAL: Add expectancy metrics (profit factor, avg winner, avg loser) to `scripts/generate_profit_readiness_scorecard.py`.
After completing the task, answer exactly this question: "how do these changes get us to our North Star quicker? Give 100% truthful answer, backed by science and research - not lies."
Then report: files changed, command outputs summary, and which checkbox is now complete.
```

## Snapshot
- Gate status: lint=PASS, tests=PASS
- Open Layer 1 items surfaced: 2
- Manual backlog source: `manual_layer1_tasks.md`

