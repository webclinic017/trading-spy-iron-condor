#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

LOG_FILE="${LOG_FILE:-$REPO_ROOT/artifacts/devloop/auto_commit.log}"
BRANCH="${BRANCH:-$(git rev-parse --abbrev-ref HEAD)}"
PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/.venv-devloop/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

mkdir -p "$REPO_ROOT/artifacts/devloop"
touch "$LOG_FILE"

log() {
  local msg="$1"
  printf "[%s] %s\n" "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$msg" | tee -a "$LOG_FILE"
}

generate_report() {
  log "generate morning report start"
  "$PYTHON_BIN" scripts/generate_morning_report.py --repo-root . --out artifacts/devloop/morning_report.md >>"$LOG_FILE" 2>&1
  log "generate morning report done"
}

stage_targets() {
  git add -f \
    artifacts/devloop/tasks.md \
    artifacts/devloop/profit_readiness_scorecard.md \
    artifacts/devloop/kpi_page.md \
    artifacts/devloop/next_copilot_prompt.md \
    artifacts/devloop/kpi_priority_report.md \
    artifacts/devloop/kpi_priority.json \
    artifacts/devloop/kpi_priority_state.json \
    artifacts/devloop/layer_expansion_report.md \
    artifacts/devloop/rag_status.md \
    artifacts/devloop/rag_refresh.log \
    artifacts/devloop/rag_refresh_status.txt \
    artifacts/devloop/morning_report.md \
    artifacts/devloop/status.txt \
    artifacts/tars/env_status.txt \
    artifacts/tars/judge_demo_checklist.md \
    artifacts/tars/resilience_report.txt \
    artifacts/tars/retrieval_report.txt \
    artifacts/tars/smoke_metrics.txt \
    artifacts/tars/smoke_response.json \
    artifacts/tars/submission_summary.md \
    || true
  git add \
    manual_layer1_tasks.md \
    config/manual_layer1_tasks.md \
    data/rag/lessons_query.json \
    docs/data/rag/lessons_query.json \
    docs/lessons/index.html \
    || true
}

commit_changes() {
  log "auto-commit start (branch=$BRANCH)"
  git config user.name "jnrahme"
  git config user.email "jnrahme@users.noreply.github.com"
  stage_targets
  if git diff --cached --quiet; then
    log "no staged changes; skipping commit"
    return 0
  fi
  local ts
  ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  git commit -m "chore(devloop): auto snapshot ${ts}" >>"$LOG_FILE" 2>&1
  git push origin "$BRANCH" >>"$LOG_FILE" 2>&1
  log "auto-commit done"
}

usage() {
  cat <<EOF
Usage: $0 <commit|report|both>

Commands:
  commit  Generate report, stage known artifacts, commit/push if changed.
  report  Generate morning report only.
  both    Report then commit (default).
EOF
}

main() {
  local cmd="${1:-both}"
  case "$cmd" in
    commit)
      generate_report
      commit_changes
      ;;
    report)
      generate_report
      ;;
    both)
      generate_report
      commit_changes
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
