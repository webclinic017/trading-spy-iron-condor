# Autonomous Project Management — Feature Decomposition Pipeline

## When This Rule Activates

Detect these patterns in user requests and automatically engage structured planning:

1. **Feature requests**: "add X", "implement Y", "build Z", "create a new..."
2. **Multi-step work**: requests that clearly require 3+ files or multiple components
3. **ADO work items**: references to AB#, PBI, user story links
4. **Explicit planning**: "plan this", "break this down", "decompose this"

Do NOT activate for: bug fixes, single-file edits, questions, research, or tasks you can complete in <5 minutes.

## Autonomous Pipeline (No Manual Commands)

When activated, run this pipeline silently — no asking the user to invoke `/pm:*` commands.

### Phase 1: Rapid PRD (30 seconds)

Create `.claude/prds/<feature-name>.md` with frontmatter:

```markdown
---
name: <feature-name>
status: in-progress
created: <ISO datetime>
source: <ADO link if available>
---

# <Feature Name>

## Problem
<What problem does this solve? Extract from user's request.>

## Requirements
<Bullet list of functional requirements — inferred from request + codebase context>

## Scope
<What's in / what's out>

## Success Criteria
<How do we know it's done?>
```

Keep it concise — 1 page max. The PRD captures intent, not implementation.

### Phase 2: Technical Epic (1 minute)

Create `.claude/epics/<feature-name>/epic.md`:

```markdown
---
name: <feature-name>
status: in-progress
created: <ISO datetime>
prd: .claude/prds/<feature-name>.md
progress: 0%
---

# Epic: <Feature Name>

## Technical Approach
<Architecture decisions, patterns to follow, files affected>

## Task Breakdown
<Numbered list with parallel/sequential flags>

## Dependencies
<What must exist before we start>
```

### Phase 3: Task Decomposition (automatic)

For each task in the epic, create `.claude/epics/<feature-name>/NNN.md`:

```markdown
---
name: <Task Title>
status: open
parallel: true/false
depends_on: []
---

# <Task Title>

## What
<Clear description>

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Files
<List of files to create/modify>
```

### Phase 4: Execute with Parallel Agents

For tasks marked `parallel: true` with no unresolved dependencies:
- Dispatch via Task tool with appropriate `subagent_type` and `model`
- Use `model: "haiku"` for scaffolding, tests, simple implementations
- Use `model: "sonnet"` for complex logic, API integrations
- Use `model: "opus"` for architecture decisions, security-critical code
- Track progress by updating task frontmatter status

For sequential tasks: execute in dependency order, one at a time.

### Phase 5: Sync to GitHub (if repo has issues enabled)

After tasks are created, sync to GitHub Issues:
```bash
gh issue create --title "Epic: <name>" --body "<epic content>" --label "epic"
```
Create sub-issues for each task, linking back to the epic.

## Key Principles

- **Never ask the user to run a command** — execute everything autonomously
- **Keep PRDs short** — capture intent, not bureaucracy
- **Parallelize aggressively** — if tasks don't share files, run them concurrently
- **Update as you go** — mark tasks complete as agents finish
- **Skip phases that add no value** — if the request is clear enough, skip brainstorming and go straight to epic

## Integration Points

- Subagent dispatches are automatically traced by `PreToolUse`/`PostToolUse` hooks
- Context Guardian monitors window usage during parallel execution
- RLHF captures feedback on decomposition quality
- CCPM `/pm:*` commands remain available as manual overrides if needed
