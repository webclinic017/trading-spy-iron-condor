import json
import os

import pytest
from scripts.collect_unsloth_dataset import collect_trading_codebase
from scripts.monitor_llm_roi import log_inference

TEST_LOG_FILE = "data/test_performance_log.json"
TEST_DATASET_FILE = "data/ml_training_data/test_dataset.json"


@pytest.fixture
def clean_test_files():
    """Ensure test files are removed before and after tests."""
    files = [TEST_LOG_FILE, TEST_DATASET_FILE]
    for f in files:
        if os.path.exists(f):
            os.remove(f)
    yield
    for f in files:
        if os.path.exists(f):
            os.remove(f)


def test_collect_trading_codebase():
    """Verify that the dataset collector picks up relevant files."""
    data = collect_trading_codebase()
    assert isinstance(data, list)
    if len(data) > 0:
        sample = data[0]
        assert "instruction" in sample
        assert "output" in sample
        assert "metadata" in sample
        assert "path" in sample["metadata"]


def test_monitor_llm_roi(clean_test_files, monkeypatch):
    """Test the ROI monitor's calculation and logging logic."""
    # Patch the LOG_FILE path to a test location
    monkeypatch.setattr("scripts.monitor_llm_roi.LOG_FILE", TEST_LOG_FILE)

    tokens_in = 1000
    tokens_out = 500
    latency = 1200

    # Test local inference (should save money)
    log_inference("Test-Model-Local", True, tokens_in, tokens_out, latency)

    assert os.path.exists(TEST_LOG_FILE)
    with open(TEST_LOG_FILE) as f:
        logs = json.load(f)
        assert len(logs) == 1
        entry = logs[0]
        assert entry["is_local"] is True
        assert entry["cost_saved_usd"] > 0

    # Test cloud inference (should NOT save money)
    log_inference("Test-Model-Cloud", False, tokens_in, tokens_out, latency)
    with open(TEST_LOG_FILE) as f:
        logs = json.load(f)
        assert len(logs) == 2
        assert logs[1]["cost_saved_usd"] == 0


def test_dataset_integrity():
    """Verify the generated JSON is valid and has expected fields."""
    output_dir = "data/ml_training_data"
    os.makedirs(output_dir, exist_ok=True)
    data = collect_trading_codebase()

    with open(TEST_DATASET_FILE, "w") as f:
        json.dump(data, f)

    with open(TEST_DATASET_FILE) as f:
        loaded_data = json.load(f)
        assert len(loaded_data) == len(data)
        if len(loaded_data) > 0:
            assert "instruction" in loaded_data[0]
