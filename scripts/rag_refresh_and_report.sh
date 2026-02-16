#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

FORCE="${FORCE:-0}"
LOG_FILE="${LOG_FILE:-$REPO_ROOT/artifacts/devloop/rag_refresh.log}"
OUT_REPORT="${OUT_REPORT:-$REPO_ROOT/artifacts/devloop/rag_status.md}"
STATUS_FILE="${STATUS_FILE:-$REPO_ROOT/artifacts/devloop/rag_refresh_status.txt}"
if [[ -x "$REPO_ROOT/.venv-devloop/bin/python" ]]; then
  PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/.venv-devloop/bin/python}"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"
touch "$STATUS_FILE"

log() {
  local msg="$1"
  printf "[%s] %s\n" "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$msg" | tee -a "$LOG_FILE"
}

run_reindex() {
  log "RAG reindex start (force=$FORCE)"
  local cmd_exit=0
  local health_exit=0
  local exit_code=0
  set +e
  if [[ "$FORCE" == "1" ]]; then
    "$PYTHON_BIN" scripts/reindex_rag.py --force >>"$LOG_FILE" 2>&1
  else
    "$PYTHON_BIN" scripts/reindex_rag.py >>"$LOG_FILE" 2>&1
  fi
  cmd_exit=$?
  "$PYTHON_BIN" - <<'PY' >>"$LOG_FILE" 2>&1
import json
from pathlib import Path
stats = Path(".claude/memory/lancedb/index_stats.json")
if not stats.exists():
    raise SystemExit(2)
payload = json.loads(stats.read_text(encoding="utf-8", errors="ignore"))
errors = payload.get("errors", [])
raise SystemExit(1 if isinstance(errors, list) and len(errors) > 0 else 0)
PY
  health_exit=$?
  set -e
  if [[ "$cmd_exit" -ne 0 ]] || [[ "$health_exit" -ne 0 ]]; then
    exit_code=1
  fi
  printf "reindex_exit=%s\n" "$exit_code" >>"$STATUS_FILE"
  log "RAG reindex done (exit=$exit_code cmd=$cmd_exit health=$health_exit)"
}

run_query_index() {
  log "RAG query-index build start"
  local exit_code=0
  set +e
  "$PYTHON_BIN" scripts/build_rag_query_index.py >>"$LOG_FILE" 2>&1
  exit_code=$?
  set -e
  printf "query_index_exit=%s\n" "$exit_code" >>"$STATUS_FILE"
  log "RAG query-index build done (exit=$exit_code)"
}

run_status_report() {
  log "RAG status report generation start"
  local exit_code=0
  set +e
  "$PYTHON_BIN" scripts/generate_rag_status_report.py --repo-root . --out "$OUT_REPORT" --refresh-log "$LOG_FILE" --status-file "$STATUS_FILE" >>"$LOG_FILE" 2>&1
  exit_code=$?
  set -e
  printf "report_exit=%s\n" "$exit_code" >>"$STATUS_FILE"
  log "RAG status report generation done (exit=$exit_code)"
}

usage() {
  cat <<EOF
Usage: $0 <refresh|report|full>

Commands:
  refresh  Run reindex + query index update.
  report   Generate status report only.
  full     Refresh and then generate status report.

Environment:
  FORCE=1           Force rebuild reindex table
  LOG_FILE=...      Refresh log path (default: artifacts/devloop/rag_refresh.log)
  OUT_REPORT=...    Status report path (default: artifacts/devloop/rag_status.md)
  STATUS_FILE=...   Step status path (default: artifacts/devloop/rag_refresh_status.txt)
  PYTHON_BIN=...    Python executable (default: .venv-devloop/bin/python if present)
EOF
}

main() {
  local cmd="${1:-full}"
  : > "$STATUS_FILE"
  case "$cmd" in
    refresh)
      run_reindex
      run_query_index
      ;;
    report)
      run_status_report
      ;;
    full)
      run_reindex
      run_query_index
      run_status_report
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
