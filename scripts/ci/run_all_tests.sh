#!/usr/bin/env bash
# CI test runner with watchdog timeouts and deterministic artifacts.

set -euo pipefail

REPORT_DIR="${REPORT_DIR:-artifacts/test-reports}"
PYTEST_TIMEOUT_SECONDS="${PYTEST_TIMEOUT_SECONDS:-300}"
CORE_TIMEOUT_MINUTES="${CORE_TIMEOUT_MINUTES:-28}"
INTEGRATION_TIMEOUT_MINUTES="${INTEGRATION_TIMEOUT_MINUTES:-12}"
COV_FAIL_UNDER="${COV_FAIL_UNDER:-15}"

mkdir -p "${REPORT_DIR}"

log() {
  printf '[ci-tests] %s\n' "$1"
}

resolve_timeout_cmd() {
  if command -v timeout >/dev/null 2>&1; then
    echo "timeout"
    return 0
  fi
  if command -v gtimeout >/dev/null 2>&1; then
    echo "gtimeout"
    return 0
  fi
  echo ""
  return 0
}

run_phase() {
  local phase="$1"
  local max_minutes="$2"
  shift 2

  local timeout_cmd
  timeout_cmd="$(resolve_timeout_cmd)"
  local log_file="${REPORT_DIR}/${phase}.log"
  local junit_file="${REPORT_DIR}/junit-${phase}.xml"

  log "starting phase=${phase} timeout=${max_minutes}m"
  set +e
  if [[ -n "${timeout_cmd}" ]]; then
    "${timeout_cmd}" --signal=TERM --kill-after=120 "$((max_minutes * 60))" \
      python -m pytest \
      -v \
      --tb=long \
      --durations=25 \
      --timeout="${PYTEST_TIMEOUT_SECONDS}" \
      --timeout-method=thread \
      --cov=src \
      --cov-append \
      --cov-report= \
      --junitxml="${junit_file}" \
      "$@" 2>&1 | tee "${log_file}"
  else
    log "timeout command not available; running phase without outer watchdog"
    python -m pytest \
      -v \
      --tb=long \
      --durations=25 \
      --timeout="${PYTEST_TIMEOUT_SECONDS}" \
      --timeout-method=thread \
      --cov=src \
      --cov-append \
      --cov-report= \
      --junitxml="${junit_file}" \
      "$@" 2>&1 | tee "${log_file}"
  fi
  local rc=${PIPESTATUS[0]}
  set -e

  if [[ ${rc} -eq 124 ]]; then
    log "phase=${phase} timed out"
    tail -n 200 "${log_file}" || true
    return 124
  fi
  if [[ ${rc} -ne 0 ]]; then
    log "phase=${phase} failed with rc=${rc}"
    tail -n 200 "${log_file}" || true
    return "${rc}"
  fi

  log "phase=${phase} passed"
}

rm -f .coverage coverage.xml

if [[ ! -d tests ]]; then
  log "tests directory missing"
  exit 1
fi

run_phase "core" "${CORE_TIMEOUT_MINUTES}" tests --ignore=tests/integration

if find tests/integration -name 'test_*.py' -print -quit 2>/dev/null | grep -q .; then
  run_phase "integration" "${INTEGRATION_TIMEOUT_MINUTES}" tests/integration
else
  log "integration phase skipped: no tests/integration test files"
fi

python -m coverage xml -o coverage.xml
python -m coverage report --fail-under="${COV_FAIL_UNDER}" | tee "${REPORT_DIR}/coverage.txt"

log "all phases complete"
