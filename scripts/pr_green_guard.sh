#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BRANCH="${BRANCH:-$(git rev-parse --abbrev-ref HEAD)}"
PR_NUMBER="${PR_NUMBER:-}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-300}"
MAX_CYCLES="${MAX_CYCLES:-0}" # 0=infinite
LOG_FILE="${LOG_FILE:-$REPO_ROOT/artifacts/devloop/pr_green_guard.log}"

mkdir -p "$REPO_ROOT/artifacts/devloop"
touch "$LOG_FILE"

log() {
  printf "[%s] %s\n" "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$1" | tee -a "$LOG_FILE"
}

resolve_pr() {
  if [[ -n "$PR_NUMBER" ]]; then
    echo "$PR_NUMBER"
    return 0
  fi
  gh pr view --head "$BRANCH" --json number -q '.number' 2>/dev/null || true
}

checks_text() {
  local pr="$1"
  gh pr checks "$pr" 2>/dev/null || true
}

all_green() {
  local text="$1"
  if [[ -z "$text" ]]; then
    return 1
  fi
  if printf "%s\n" "$text" | grep -Eiq $'\tfail\t|\tpending\t|\tcancel\t|\terror\t'; then
    return 1
  fi
  return 0
}

try_known_fix() {
  # Known recurring issue: generated explainer file missing required blog front matter.
  python3 scripts/generate_system_explainer.py --repo-root . --out docs/_reports/hackathon-system-explainer.md >>"$LOG_FILE" 2>&1 || true
  if git diff --quiet -- docs/_reports/hackathon-system-explainer.md scripts/generate_system_explainer.py; then
    log "no known-fix changes to commit"
    return 0
  fi
  git config user.name "jnrahme"
  git config user.email "jnrahme@users.noreply.github.com"
  git add docs/_reports/hackathon-system-explainer.md scripts/generate_system_explainer.py
  git commit -m "fix(ci): refresh explainer artifact for lint compliance" >>"$LOG_FILE" 2>&1 || true
  git push origin "$BRANCH" >>"$LOG_FILE" 2>&1 || true
  log "applied known lint fix and pushed"
}

main() {
  if ! command -v gh >/dev/null 2>&1; then
    log "gh not found; exiting"
    exit 1
  fi

  local cycle=1
  while true; do
    local pr
    pr="$(resolve_pr)"
    if [[ -z "$pr" ]]; then
      log "no PR found for branch=$BRANCH"
    else
      local txt
      txt="$(checks_text "$pr")"
      if all_green "$txt"; then
        log "PR #$pr checks are green"
      else
        log "PR #$pr not green; checking for known auto-fixes"
        if printf "%s\n" "$txt" | grep -Eq '^Lint & Format[[:space:]]+fail[[:space:]]+'; then
          try_known_fix
        fi
      fi
    fi

    if (( MAX_CYCLES > 0 && cycle >= MAX_CYCLES )); then
      log "max cycles reached=$MAX_CYCLES"
      break
    fi
    cycle=$((cycle + 1))
    sleep "$INTERVAL_SECONDS"
  done
}

main "$@"
