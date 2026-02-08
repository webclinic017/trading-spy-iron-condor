#!/bin/bash
# Ralph Loop - Autonomous Overnight Coding
# Inspired by Geoff Huntley's Ralph methodology
#
# Usage:
#   ralph-loop.sh start "feature description" [work-item-id]
#   ralph-loop.sh status
#   ralph-loop.sh stop
#
# LOCAL ONLY - Do not commit to repository

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

GIT_ROOT=$(git rev-parse --show-toplevel)
RALPH_DIR="$GIT_ROOT/.claude/ralph"
PLAN_FILE="$RALPH_DIR/plan.md"
LOG_FILE="$RALPH_DIR/ralph.log"
PID_FILE="$RALPH_DIR/ralph.pid"
STATE_FILE="$RALPH_DIR/state.json"
TASKS_MAP_FILE="$RALPH_DIR/tasks-map.json"  # Maps plan task numbers to Claude Task IDs
TASKS_BRIDGE="$GIT_ROOT/.claude/scripts/claude-tasks-bridge.sh"

mkdir -p "$RALPH_DIR"

# Check if Tasks bridge is available
TASKS_ENABLED=false
if [ -x "$TASKS_BRIDGE" ]; then
    TASKS_ENABLED=true
fi

# Load .env for API keys
if [ -f "$GIT_ROOT/.env" ]; then
    export $(grep -v '^#' "$GIT_ROOT/.env" | grep -E '^[A-Z_]+=.' | xargs 2>/dev/null) || true
fi

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo -e "$msg" | tee -a "$LOG_FILE"
}

# Create Claude Code Tasks from plan file
create_tasks_from_plan() {
    if [ "$TASKS_ENABLED" != "true" ]; then
        log "${YELLOW}Tasks integration disabled (bridge not found)${NC}"
        return
    fi

    if [ ! -f "$PLAN_FILE" ]; then
        log "${YELLOW}Plan file not found, skipping Tasks creation${NC}"
        return
    fi

    log "${BLUE}Creating Claude Code Tasks from plan...${NC}"
    echo '{}' > "$TASKS_MAP_FILE"

    local task_num=0
    while IFS= read -r line; do
        task_num=$((task_num + 1))
        # Extract task description (remove "- [ ] N. " prefix)
        local task_desc=$(echo "$line" | sed 's/^- \[ \] [0-9]*\. //')

        if [ -n "$task_desc" ]; then
            log "  Creating Task $task_num: ${task_desc:0:50}..."

            # Create task via Claude (in background to not block)
            # The actual task creation happens when Claude processes the prompt
            local short_desc="${task_desc:0:60}"
            local active_form="Working on: ${task_desc:0:40}"

            # Store mapping: plan task number -> description (ID assigned later)
            jq --arg num "$task_num" --arg desc "$task_desc" \
                '.[$num] = {"description": $desc, "status": "pending"}' \
                "$TASKS_MAP_FILE" > "${TASKS_MAP_FILE}.tmp" && mv "${TASKS_MAP_FILE}.tmp" "$TASKS_MAP_FILE"
        fi
    done < <(grep "^\- \[ \]" "$PLAN_FILE" 2>/dev/null)

    log "${GREEN}Prepared $task_num tasks for tracking${NC}"
}

# Update task status in the map
update_task_status() {
    local task_num="$1"
    local status="$2"  # pending, in_progress, completed

    if [ "$TASKS_ENABLED" != "true" ] || [ ! -f "$TASKS_MAP_FILE" ]; then
        return
    fi

    jq --arg num "$task_num" --arg status "$status" \
        '.[$num].status = $status' \
        "$TASKS_MAP_FILE" > "${TASKS_MAP_FILE}.tmp" && mv "${TASKS_MAP_FILE}.tmp" "$TASKS_MAP_FILE"

    log "Task $task_num status: $status"
}

# Get current task number from plan (first uncompleted)
get_current_task_number() {
    if [ ! -f "$PLAN_FILE" ]; then
        echo "0"
        return
    fi

    local task_num=0
    while IFS= read -r line; do
        task_num=$((task_num + 1))
        if echo "$line" | grep -q "^\- \[ \]"; then
            echo "$task_num"
            return
        fi
    done < <(grep "^\- \[.\]" "$PLAN_FILE" 2>/dev/null)

    echo "0"
}

# Generate the planning prompt
generate_plan_prompt() {
    local description="$1"
    local work_item="$2"
    local agents_content=""
    local specs_content=""

    # Load AGENTS.md (project root for cross-tool compatibility, fallback to .claude/ralph/)
    if [ -f "$GIT_ROOT/AGENTS.md" ]; then
        agents_content=$(cat "$GIT_ROOT/AGENTS.md")
    elif [ -f "$RALPH_DIR/AGENTS.md" ]; then
        agents_content=$(cat "$RALPH_DIR/AGENTS.md")
    fi

    # Load specs/ files if directory exists for gap analysis
    if [ -d "$GIT_ROOT/specs" ]; then
        specs_content="## Specifications (Gap Analysis Required)\n\n"
        specs_content+="Compare these specs against the current codebase. Tasks should close the gap.\n\n"
        for spec_file in "$GIT_ROOT/specs"/*.md; do
            if [ -f "$spec_file" ]; then
                specs_content+="### $(basename "$spec_file")\n\n"
                specs_content+="$(cat "$spec_file")\n\n"
            fi
        done
    fi

    cat << EOF
# Ralph Planning Session

You are starting a Ralph autonomous coding session. Your job is to create a detailed implementation plan.

## Operational Reference (AGENTS.md)

$agents_content

$specs_content

## Feature Request
$description

## Work Item
${work_item:-"None specified - create tasks without AB# references"}

## Design-First Methodology (MANDATORY)

Before writing ANY code tasks, you MUST complete a design phase:

### Step 1: Define Domain Concepts (2-5 minutes)
Write down in plain language:
- What are the **entities** (objects, classes, components)?
- What are their **responsibilities** (what does each do)?
- How do they **relate** to each other?
- What are the **boundaries** between concerns?

### Step 2: Define Design Constraints
Explicitly state rules like:
- "No circular dependencies between X and Y"
- "Component Z should ONLY know about IDs, not full objects"
- "State management lives in hooks, not components"
- "Colors MUST come from theme.colors, never hardcoded"
- "Business logic in hooks/utils, presentation in components"

### Step 3: Translate to Style Rules
- Use TypeScript strict mode, no \`any\`
- Prefer composition over inheritance
- Single responsibility per file
- Extract reusable patterns into shared/

## Instructions

1. **Study** the codebase to understand the current architecture (don't assume not implemented)
2. If specs/ exist, perform **gap analysis** - compare specs against existing code
3. **DESIGN FIRST** - Complete the domain/constraints/style phases above
4. Break down the feature into **small, atomic tasks** (each task = 1 commit)
5. Each task should be completable in 10-30 minutes
6. Tasks must be ORDERED by dependency (can't use X before creating X)
7. Include validation steps (tests, lint, build)
8. Create the plan in the exact format below

## Output Format

Create a file at: $PLAN_FILE

With this EXACT structure:

\`\`\`markdown
# Ralph Plan: [Feature Name]

## Status: IN_PROGRESS

## Feature Description
[Brief description]

## Work Item
AB#${work_item:-"NONE"}

## Design (REQUIRED - Complete Before Tasks)

### Domain Concepts
| Entity | Responsibility | Depends On |
|--------|---------------|------------|
| [Name] | [What it does] | [Dependencies] |

### Design Constraints
1. [Constraint 1: e.g., "No direct color imports, use theme.colors"]
2. [Constraint 2: e.g., "Business logic in hooks, not components"]
3. [Constraint 3: e.g., "Single responsibility per file"]

### Style Rules
- TypeScript strict, no \`any\`
- Composition over inheritance
- Extract reusable patterns to shared/

## Tasks

### Pending
- [ ] 1. [First task - be specific]
- [ ] 2. [Second task]
- [ ] 3. [Third task]
... (continue for all tasks)

### In Progress
(empty initially)

### Completed
(empty initially)

## Validation Commands
\\\`\\\`\\\`bash
npm test
npm run lint
npm run typecheck
\\\`\\\`\\\`

## Completion Marker
(Add "ALL_TASKS_COMPLETE" when finished)
\`\`\`

## Important Rules

1. Tasks must be ATOMIC - one logical change per task
2. Tasks must be ORDERED - dependencies respected
3. Each task must be TESTABLE - validation must pass after
4. Keep tasks SMALL - 10-30 min each
5. Be SPECIFIC - "Update Header.tsx to support dark prop" not "Update header"

Now analyze the codebase and create the plan.
EOF
}

# Generate the execution prompt
generate_execution_prompt() {
    local agents_content=""
    local specs_content=""
    local current_task_num=$(get_current_task_number)

    # Load AGENTS.md (project root for cross-tool compatibility, fallback to .claude/ralph/)
    if [ -f "$GIT_ROOT/AGENTS.md" ]; then
        agents_content=$(cat "$GIT_ROOT/AGENTS.md")
    elif [ -f "$RALPH_DIR/AGENTS.md" ]; then
        agents_content=$(cat "$RALPH_DIR/AGENTS.md")
    fi

    # Load specs/ files if directory exists
    if [ -d "$GIT_ROOT/specs" ]; then
        specs_content="## Specifications\n\n"
        for spec_file in "$GIT_ROOT/specs"/*.md; do
            if [ -f "$spec_file" ]; then
                specs_content+="### $(basename "$spec_file")\n\n"
                specs_content+="$(cat "$spec_file")\n\n"
            fi
        done
    fi

    cat << EOF
# Ralph Execution Session

You are continuing a Ralph autonomous coding session.

## Claude Code Tasks Integration (MANDATORY)

**Current Plan Task Number:** $current_task_num

**BEFORE starting work on a task:**
1. Use TaskCreate to create a task for the current work item (if not already created)
2. Use TaskUpdate to mark the task as "in_progress"

**AFTER completing a task:**
1. Use TaskUpdate to mark the task as "completed"
2. The visual task list in the terminal will update automatically

This provides real-time progress tracking visible to the user.

## Operational Reference (AGENTS.md)

$agents_content

$specs_content

## Your Mission

1. Read the plan file: $PLAN_FILE
2. Find the FIRST task that is NOT completed (no [x])
3. Implement ONLY that one task
4. **VALIDATE your work (MANDATORY - must pass before commit)**
5. Commit your changes ONLY if validation passes
6. Update the plan file to mark the task complete
7. Exit cleanly

## Validation Commands (MUST ALL PASS)

\`\`\`bash
npm run typecheck   # TypeScript - REQUIRED
npm run lint        # Linting - REQUIRED
npm test -- --passWithNoTests  # Tests - REQUIRED
\`\`\`

**CRITICAL: If ANY validation fails, DO NOT COMMIT. Fix the issue first.**

## Visual QA with Maestro (For Frontend/UI Tasks)

If your task involves UI changes (components, screens, styling):

1. **Ensure app is running** on iOS Simulator or Android Emulator
2. **Run Maestro smoke test** to verify app doesn't crash:
   \`\`\`bash
   maestro test .maestro/smoke/launch.yaml
   \`\`\`
3. **Run feature-specific Maestro tests** if they exist:
   \`\`\`bash
   maestro test .maestro/menu/store-menu.yaml  # Example
   \`\`\`
4. **For new UI features**, create a Maestro flow:
   \`\`\`yaml
   # .maestro/{feature}/{test-name}.yaml
   appId: com.subway.na.lower
   ---
   - launchApp
   - assertVisible: "Expected Text"
   - takeScreenshot: feature-result.png
   \`\`\`

**Maestro Commands:**
- \`maestro test <flow.yaml>\` - Run single test
- \`maestro test .maestro/\` - Run all tests
- \`maestro studio\` - Interactive test builder

**Visual QA is RECOMMENDED for UI tasks, REQUIRED for Figma-based implementations.**

## Rules

1. ONE TASK ONLY - Do not work on multiple tasks
2. **VALIDATE BEFORE COMMIT - ALL checks must pass (backpressure)**
3. **NO COMMIT ON FAILURE - Fix issues, don't skip validation**
4. UPDATE THE PLAN - Mark [x] and move to Completed section
5. EXIT WHEN DONE - Say "RALPH_TASK_COMPLETE" when finished
6. If ALL tasks are done, say "RALPH_ALL_COMPLETE"

## If You Get Stuck

If a task is impossible or blocked:
1. Add a note to the plan file explaining why
2. Say "RALPH_TASK_BLOCKED: [reason]"
3. Exit (the loop will retry or a human will help)

## If Validation Fails

1. Read the error output carefully
2. Fix the issue (type error, lint error, test failure)
3. Re-run validation
4. Only commit when ALL validations pass
5. Say "RALPH_VALIDATION_FIXED" after fixing validation errors

## Commit Message Format

git commit -m "ralph: [task description]

Task N of M in Ralph session
$([ -n "$WORK_ITEM" ] && echo "AB#$WORK_ITEM")"

Now read the plan and execute the next task.
EOF
}

# Start a new Ralph session
start_ralph() {
    local description="$1"
    local work_item="$2"

    if [ -z "$description" ]; then
        echo -e "${RED}Error: Feature description required${NC}"
        echo "Usage: ralph-loop.sh start \"implement dark mode\" [work-item-id]"
        exit 1
    fi

    # Check if already running
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo -e "${YELLOW}Ralph is already running (PID: $(cat $PID_FILE))${NC}"
        echo "Use 'ralph-loop.sh status' to check progress"
        echo "Use 'ralph-loop.sh stop' to stop it"
        exit 1
    fi

    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║              RALPH - AUTONOMOUS CODING LOOP                ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Feature:${NC} $description"
    [ -n "$work_item" ] && echo -e "${BLUE}Work Item:${NC} AB#$work_item"
    echo ""

    # Create new branch for Ralph work
    local branch_name="ralph/$(echo "$description" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | sed 's/[^a-z0-9-]//g' | cut -c1-30)"
    [ -n "$work_item" ] && branch_name="ralph/${work_item}-$(echo "$description" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | sed 's/[^a-z0-9-]//g' | cut -c1-20)"

    echo -e "${BLUE}Creating branch:${NC} $branch_name"
    git checkout -b "$branch_name" 2>/dev/null || git checkout "$branch_name"

    # Initialize state
    cat > "$STATE_FILE" << EOF
{
    "description": "$description",
    "work_item": "$work_item",
    "branch": "$branch_name",
    "started": "$(date -Iseconds)",
    "status": "planning",
    "sessions": 0,
    "tasks_completed": 0
}
EOF

    # Clear previous logs
    > "$LOG_FILE"
    log "${CYAN}Starting Ralph session${NC}"
    log "Feature: $description"
    log "Branch: $branch_name"

    # Phase 1: Planning
    echo ""
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}  PHASE 1: PLANNING                                         ${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo ""

    log "Phase 1: Creating implementation plan..."

    # Generate plan with Claude
    local plan_prompt=$(generate_plan_prompt "$description" "$work_item")
    echo "$plan_prompt" | claude --print > /dev/null 2>&1

    # Wait for plan file
    local attempts=0
    while [ ! -f "$PLAN_FILE" ] && [ $attempts -lt 60 ]; do
        sleep 2
        attempts=$((attempts + 1))
    done

    if [ ! -f "$PLAN_FILE" ]; then
        log "${RED}Failed to create plan file${NC}"
        exit 1
    fi

    # Count tasks
    local total_tasks=$(grep -c "^\- \[ \]" "$PLAN_FILE" 2>/dev/null || echo "0")
    log "Plan created with $total_tasks tasks"

    echo -e "${GREEN}✓ Plan created with $total_tasks tasks${NC}"

    # Create Claude Code Tasks for visual progress tracking
    if [ "$TASKS_ENABLED" = "true" ]; then
        echo -e "${BLUE}Creating Claude Code Tasks for progress tracking...${NC}"
        create_tasks_from_plan
        echo -e "${GREEN}✓ Tasks created for visual progress tracking${NC}"
    fi
    echo ""

    # Phase 2: Execution Loop
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}  PHASE 2: AUTONOMOUS EXECUTION                             ${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo ""

    # Update state
    jq '.status = "executing"' "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"

    # Start the loop in background
    echo $$ > "$PID_FILE"

    local session=0
    local max_sessions=100  # Safety limit
    local consecutive_failures=0
    local max_failures=3

    while [ $session -lt $max_sessions ]; do
        session=$((session + 1))

        # Check if all tasks complete
        if grep -q "ALL_TASKS_COMPLETE" "$PLAN_FILE" 2>/dev/null; then
            log "${GREEN}🎉 ALL TASKS COMPLETE!${NC}"
            echo -e "${GREEN}🎉 Ralph completed all tasks!${NC}"
            break
        fi

        # Check remaining tasks
        local remaining=$(grep -c "^\- \[ \]" "$PLAN_FILE" 2>/dev/null || echo "0")
        local completed=$(grep -c "^\- \[x\]" "$PLAN_FILE" 2>/dev/null || echo "0")

        if [ "$remaining" -eq 0 ]; then
            # All tasks marked complete, add completion marker
            echo -e "\nALL_TASKS_COMPLETE" >> "$PLAN_FILE"
            log "${GREEN}🎉 ALL TASKS COMPLETE!${NC}"
            break
        fi

        log ""
        log "${CYAN}═══ Session $session ═══${NC}"
        log "Progress: $completed done, $remaining remaining"

        echo -e "${BLUE}Session $session:${NC} $completed done, $remaining remaining"

        # Get current task number for tracking
        local current_task_num=$(get_current_task_number)
        [ "$TASKS_ENABLED" = "true" ] && update_task_status "$current_task_num" "in_progress"

        # Update state
        jq ".sessions = $session | .tasks_completed = $completed | .current_task = $current_task_num" "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"

        # Run Claude for one task
        local exec_prompt=$(generate_execution_prompt)
        local output=$(echo "$exec_prompt" | claude --print 2>&1)

        # Check result
        if echo "$output" | grep -q "RALPH_ALL_COMPLETE"; then
            echo -e "\nALL_TASKS_COMPLETE" >> "$PLAN_FILE"
            [ "$TASKS_ENABLED" = "true" ] && update_task_status "$current_task_num" "completed"
            log "${GREEN}🎉 ALL TASKS COMPLETE!${NC}"
            break
        elif echo "$output" | grep -q "RALPH_TASK_COMPLETE"; then
            [ "$TASKS_ENABLED" = "true" ] && update_task_status "$current_task_num" "completed"
            log "${GREEN}✓ Task $current_task_num completed${NC}"
            consecutive_failures=0
        elif echo "$output" | grep -q "RALPH_TASK_BLOCKED"; then
            local reason=$(echo "$output" | grep "RALPH_TASK_BLOCKED" | sed 's/RALPH_TASK_BLOCKED://')
            [ "$TASKS_ENABLED" = "true" ] && update_task_status "$current_task_num" "pending"  # Reset to pending
            log "${YELLOW}⚠ Task $current_task_num blocked: $reason${NC}"
            consecutive_failures=$((consecutive_failures + 1))
        else
            log "${YELLOW}⚠ Session ended without clear status${NC}"
            consecutive_failures=$((consecutive_failures + 1))
        fi

        # Check for too many failures
        if [ $consecutive_failures -ge $max_failures ]; then
            log "${RED}Too many consecutive failures. Pausing Ralph.${NC}"
            jq '.status = "paused"' "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
            echo -e "${RED}Ralph paused after $max_failures consecutive failures.${NC}"
            echo "Check $LOG_FILE for details"
            echo "Resume with: ralph-loop.sh resume"
            break
        fi

        # Brief pause between sessions
        sleep 5
    done

    # Final status
    local final_completed=$(grep -c "^\- \[x\]" "$PLAN_FILE" 2>/dev/null || echo "0")

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Ralph session finished${NC}"
    echo -e "Sessions: $session"
    echo -e "Tasks completed: $final_completed"
    echo -e "Log: $LOG_FILE"
    echo -e "Plan: $PLAN_FILE"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"

    # Update final state
    jq '.status = "complete" | .finished = "'"$(date -Iseconds)"'"' "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"

    # Cleanup PID
    rm -f "$PID_FILE"

    # Create PR if we have commits
    local commit_count=$(git rev-list --count HEAD ^develop 2>/dev/null || echo "0")
    if [ "$commit_count" -gt 0 ]; then
        echo ""
        echo -e "${BLUE}Creating draft PR...${NC}"
        git push -u origin "$branch_name" 2>/dev/null || true
        gh pr create --draft --title "ralph: $description" --body "$(cat << EOF
## Ralph Autonomous Session

**Feature:** $description
**Sessions:** $session
**Tasks Completed:** $final_completed

### Plan
\`\`\`
$(cat "$PLAN_FILE")
\`\`\`

### Log
See \`.claude/ralph/ralph.log\` for detailed execution log.

---
🤖 Generated autonomously by Ralph
EOF
)" 2>/dev/null || echo "PR creation skipped (may already exist)"
    fi
}

# Check Ralph status
status_ralph() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║              RALPH STATUS                                   ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [ ! -f "$STATE_FILE" ]; then
        echo -e "${YELLOW}No Ralph session found.${NC}"
        echo "Start one with: ralph-loop.sh start \"feature description\""
        return
    fi

    local status=$(jq -r '.status' "$STATE_FILE")
    local description=$(jq -r '.description' "$STATE_FILE")
    local branch=$(jq -r '.branch' "$STATE_FILE")
    local sessions=$(jq -r '.sessions' "$STATE_FILE")
    local completed=$(jq -r '.tasks_completed' "$STATE_FILE")
    local started=$(jq -r '.started' "$STATE_FILE")

    echo -e "${BLUE}Feature:${NC} $description"
    echo -e "${BLUE}Branch:${NC} $branch"
    echo -e "${BLUE}Started:${NC} $started"
    echo -e "${BLUE}Sessions:${NC} $sessions"
    echo -e "${BLUE}Tasks Completed:${NC} $completed"
    echo -e "${BLUE}Tasks Integration:${NC} $([ "$TASKS_ENABLED" = "true" ] && echo "${GREEN}Enabled${NC}" || echo "${YELLOW}Disabled${NC}")"

    case "$status" in
        "planning")
            echo -e "${BLUE}Status:${NC} ${YELLOW}Planning...${NC}"
            ;;
        "executing")
            if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
                echo -e "${BLUE}Status:${NC} ${GREEN}Running (PID: $(cat $PID_FILE))${NC}"
            else
                echo -e "${BLUE}Status:${NC} ${YELLOW}Stopped (was executing)${NC}"
            fi
            ;;
        "paused")
            echo -e "${BLUE}Status:${NC} ${YELLOW}Paused (check log for errors)${NC}"
            ;;
        "complete")
            echo -e "${BLUE}Status:${NC} ${GREEN}Complete!${NC}"
            ;;
        *)
            echo -e "${BLUE}Status:${NC} $status"
            ;;
    esac

    echo ""

    if [ -f "$PLAN_FILE" ]; then
        local total_raw=$(grep -c "^\- \[.\]" "$PLAN_FILE" 2>/dev/null || true)
        local done_raw=$(grep -c "^\- \[x\]" "$PLAN_FILE" 2>/dev/null || true)
        local total=${total_raw:-0}
        local done=${done_raw:-0}
        # Ensure numeric values
        total=$(echo "$total" | tr -d '[:space:]')
        done=$(echo "$done" | tr -d '[:space:]')
        [ -z "$total" ] && total=0
        [ -z "$done" ] && done=0
        local remaining=$((total - done))

        echo -e "${BLUE}Progress:${NC} $done / $total tasks"

        # Progress bar
        if [ "$total" -gt 0 ]; then
            local pct=$((done * 100 / total))
            local filled=$((pct / 5))
            local empty=$((20 - filled))
            printf "${GREEN}"
            printf '█%.0s' $(seq 1 $filled 2>/dev/null) 2>/dev/null || true
            printf "${NC}"
            printf '░%.0s' $(seq 1 $empty 2>/dev/null) 2>/dev/null || true
            echo " $pct%"
        fi

        echo ""
        echo -e "${BLUE}Remaining Tasks:${NC}"
        grep "^\- \[ \]" "$PLAN_FILE" 2>/dev/null | head -5 | sed 's/^/  /'
        [ "$remaining" -gt 5 ] && echo "  ... and $((remaining - 5)) more"
    fi

    echo ""
    echo -e "${BLUE}Recent Log:${NC}"
    tail -10 "$LOG_FILE" 2>/dev/null | sed 's/^/  /' || echo "  No log entries"
}

# Stop Ralph
stop_ralph() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}Stopping Ralph (PID: $pid)...${NC}"
            kill "$pid" 2>/dev/null || true
            rm -f "$PID_FILE"
            jq '.status = "stopped"' "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
            echo -e "${GREEN}Ralph stopped.${NC}"
        else
            echo -e "${YELLOW}Ralph process not running.${NC}"
            rm -f "$PID_FILE"
        fi
    else
        echo -e "${YELLOW}No Ralph session running.${NC}"
    fi
}

# Resume paused Ralph
resume_ralph() {
    if [ ! -f "$STATE_FILE" ]; then
        echo -e "${RED}No Ralph session to resume.${NC}"
        exit 1
    fi

    local status=$(jq -r '.status' "$STATE_FILE")
    if [ "$status" = "complete" ]; then
        echo -e "${GREEN}Ralph already completed this session.${NC}"
        exit 0
    fi

    echo -e "${BLUE}Resuming Ralph session...${NC}"
    jq '.status = "executing"' "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"

    # Re-enter execution loop (simplified resume)
    local description=$(jq -r '.description' "$STATE_FILE")
    local work_item=$(jq -r '.work_item' "$STATE_FILE")

    # Continue from where we left off
    start_ralph "$description" "$work_item"
}

# Show help
show_help() {
    cat << EOF
${CYAN}Ralph - Autonomous Overnight Coding Loop${NC}

${BLUE}Usage:${NC}
  ralph-loop.sh start <description> [work-item-id]
  ralph-loop.sh status
  ralph-loop.sh stop
  ralph-loop.sh resume
  ralph-loop.sh help

${BLUE}Commands:${NC}
  start <desc> [id]   Start new Ralph session
  status              Check current session status
  stop                Stop running session
  resume              Resume paused session
  help                Show this help

${BLUE}Examples:${NC}
  ralph-loop.sh start "implement dark mode" 1648178
  ralph-loop.sh start "refactor authentication system"
  ralph-loop.sh status
  ralph-loop.sh stop

${BLUE}How It Works:${NC}
  1. Creates detailed implementation plan
  2. Creates Claude Code Tasks for visual progress tracking
  3. Loops through tasks, one per Claude session
  4. Each session: implement → test → commit → update plan → update Tasks
  5. Visual task list updates in real-time in terminal
  6. Continues until all tasks complete
  7. Creates draft PR when done

${BLUE}Tasks Integration:${NC}
  Ralph now integrates with Claude Code's native Tasks system for:
  - Real-time visual progress in terminal UI
  - Task dependencies and blocking
  - Status tracking (pending → in_progress → completed)

  The Tasks bridge script is at: .claude/scripts/claude-tasks-bridge.sh

${BLUE}Files:${NC}
  Plan:  .claude/ralph/plan.md
  Log:   .claude/ralph/ralph.log
  State: .claude/ralph/state.json

${BLUE}Safety:${NC}
  - Max 100 sessions (prevents runaway)
  - Pauses after 3 consecutive failures
  - All work on separate branch
  - Draft PR (not auto-merged)

EOF
}

# Main
case "${1:-help}" in
    start)
        start_ralph "$2" "$3"
        ;;
    status)
        status_ralph
        ;;
    stop)
        stop_ralph
        ;;
    resume)
        resume_ralph
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac
