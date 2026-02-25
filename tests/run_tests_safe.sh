#!/bin/bash
# High-throughput, memory-safe test runner for trading system
# Prevents OOM (Exit 137) by partitioning tests and appending coverage.

# Set strict mode
set -e

# Default parameters
VENV_PATH=".venv/bin/pytest"
COVERAGE_CMD=".venv/bin/coverage"

echo "\ud83d\ude80 Starting memory-safe test suite execution..."

# Clean up previous coverage
rm -f .coverage total_coverage_report.txt

# Function to run a test batch
run_batch() {
    local batch_name=$1
    shift
    local test_paths=("$@")
    echo "--------------------------------------------------------"
    echo "\ud83d\udce6 Running Batch: $batch_name (${test_paths[*]})"
    echo "--------------------------------------------------------"
    
    $VENV_PATH "${test_paths[@]}" --cov=src --cov-append -q --maxfail=10
    
    # Check current memory usage (macOS RSS in MB)
    MEM_USAGE=$(ps -o rss= -p $$ | awk '{print $1 / 1024}')
    echo "\ud83d\udcca Current Memory Usage: ${MEM_USAGE}MB"
}

# 1. Unit Tests (Smallest footprint)
run_batch "Unit" "tests/unit/"

# 2. Integration Tests (Medium footprint)
run_batch "Integration" "tests/integration/"

# 3. Agents & Strategy (Large footprint)
run_batch "Agents" "tests/test_momentum_agent.py" "tests/test_audit_agent.py"

# 4. Core Orchestrator & Safety (Hardened)
run_batch "Orchestrator" "tests/test_orchestrator_main.py" "tests/test_orchestrator_hardening.py" "tests/test_north_star_guard.py" "tests/test_behavioral_guard.py"

# 5. All remaining tests (Catch-all)
echo "\ud83d\udd0e Collecting remaining tests..."
$VENV_PATH tests/ --cov=src --cov-append -q --ignore=tests/unit/ --ignore=tests/integration/ \
    --ignore=tests/test_momentum_agent.py --ignore=tests/test_audit_agent.py \
    --ignore=tests/test_orchestrator_main.py --ignore=tests/test_orchestrator_hardening.py \
    --ignore=tests/test_north_star_guard.py --ignore=tests/test_behavioral_guard.py \
    -p no:warnings

# Final Coverage Report
echo "--------------------------------------------------------"
echo "\ud83d\udcca Generating Final Coverage Report..."
$COVERAGE_CMD report -m > total_coverage_report.txt
# Filter to see only the orchestrator's progress
grep "src/orchestrator/main.py" total_coverage_report.txt

echo "\u2705 Memory-safe test run completed."
