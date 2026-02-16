# Next Copilot Prompt

Copy/paste this into Copilot Chat (Agent mode):

```text
Read `.github/copilot-instructions.md` and `artifacts/devloop/tasks.md`.
Pick exactly one unchecked Layer 1 item and do a minimal fix.
Run `./scripts/layered_tdd_loop.sh analyze` after the change.
Update only necessary files and keep diffs surgical.
If Layer 1 is empty and checks are green, pick one open item from `manual_layer1_tasks.md`.
Target item: MANUAL: Add a promotion gate artifact that blocks strategy promotion when win rate/run-rate thresholds are below target.
Then report: files changed, command outputs summary, and which checkbox is now complete.
```

## Snapshot
- Gate status: lint=PASS, tests=PASS
- Open Layer 1 items surfaced: 4
- Manual backlog source: `manual_layer1_tasks.md`

