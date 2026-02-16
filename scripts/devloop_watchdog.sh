#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.joeyrahme.trading.devloop"
LOG_FILE="$REPO_ROOT/artifacts/devloop/watchdog.log"
STOP_FILE="$REPO_ROOT/artifacts/devloop/STOP"
MAX_STALE_SECONDS="${MAX_STALE_SECONDS:-900}"
CHECK_EVERY_SECONDS="${CHECK_EVERY_SECONDS:-60}"

mkdir -p "$REPO_ROOT/artifacts/devloop"
touch "$LOG_FILE"

log() {
  local msg="$1"
  printf "[%s] %s\n" "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$msg" | tee -a "$LOG_FILE"
}

is_agent_running() {
  launchctl print "gui/$(id -u)/$LABEL" 2>/dev/null | rg -q "state = running"
}

is_loop_stale() {
  local out_log="$REPO_ROOT/artifacts/devloop/launchd.out.log"
  if [[ ! -f "$out_log" ]]; then
    return 0
  fi
  local now epoch mtime age
  now="$(date +%s)"
  mtime="$(stat -f %m "$out_log" 2>/dev/null || echo 0)"
  epoch="$mtime"
  age=$((now - epoch))
  (( age > MAX_STALE_SECONDS ))
}

restart_agent() {
  log "restart requested"
  "$REPO_ROOT/scripts/devloop_launchagent.sh" restart >>"$LOG_FILE" 2>&1 || true
}

main() {
  log "watchdog start (check=${CHECK_EVERY_SECONDS}s stale=${MAX_STALE_SECONDS}s)"
  while true; do
    if [[ -f "$STOP_FILE" ]]; then
      log "stop file detected, watchdog exiting"
      exit 0
    fi
    if ! is_agent_running; then
      log "agent not running; restarting"
      restart_agent
    elif is_loop_stale; then
      log "agent appears stale; restarting"
      restart_agent
    fi
    sleep "$CHECK_EVERY_SECONDS"
  done
}

main "$@"
