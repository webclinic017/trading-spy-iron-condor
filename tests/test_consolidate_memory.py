"""Tests for memory consolidation script."""

import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.consolidate_memory import (
    classify_cell,
    compute_salience,
    consolidate_scene,
    extract_date_key,
    is_noise,
    load_jsonl,
)


class TestIsNoise:
    def test_unknown_decision_is_noise(self):
        entry = {"principle": "Avoid: unknown decision", "context": "thumbs up"}
        assert is_noise(entry) is True

    def test_undefined_decision_is_noise(self):
        entry = {
            "userFeedback": "The agent's decision was incorrect: undefined. This approach should be avoided",
            "context": "",
        }
        assert is_noise(entry) is True

    def test_real_principle_not_noise(self):
        entry = {"principle": "ALWAYS write to ALL 4 stores", "context": "CTO approved"}
        assert is_noise(entry) is False

    def test_noise_pattern_with_rich_context_not_noise(self):
        """If there's a noise principle but meaningful context, keep it."""
        entry = {
            "principle": "Avoid: unknown decision",
            "context": "CRITICAL ERROR - User frustrated: this is unacceptable!!!!",
        }
        assert is_noise(entry) is False

    def test_empty_entry_not_noise(self):
        assert is_noise({}) is False


class TestClassifyCell:
    def test_risk_classification(self):
        assert classify_cell({"context": "Phil Town Rule #1 violated"}) == "risk"
        assert classify_cell({"context": "stop-loss triggered"}) == "risk"

    def test_decision_classification(self):
        assert classify_cell({"context": "decided to use iron condors"}) == "decision"

    def test_preference_classification(self):
        assert classify_cell({"context": "should always verify before claiming"}) == "preference"

    def test_plan_classification(self):
        assert classify_cell({"context": "plan to implement consolidation"}) == "plan"

    def test_task_classification(self):
        assert classify_cell({"context": "fix the failing CI test"}) == "task"

    def test_default_fact(self):
        assert classify_cell({"context": "thumbs up"}) == "fact"
        assert classify_cell({}) == "fact"


class TestComputeSalience:
    def test_baseline_salience(self):
        score = compute_salience({})
        assert score == pytest.approx(0.3)

    def test_intensity_boost(self):
        score = compute_salience({"intensity": 5})
        assert score > 0.3

    def test_rich_context_boost(self):
        score = compute_salience({"context": "x" * 150})
        assert score == pytest.approx(0.5)

    def test_critical_signal_boost(self):
        score = compute_salience(
            {
                "signal": "negative_strong",
                "context": "CRITICAL ERROR - User frustrated: this is unacceptable!!!! The system broke again and we lost data in the process of recovery",
            }
        )
        assert score > 0.5

    def test_salience_capped_at_1(self):
        score = compute_salience(
            {
                "intensity": 10,
                "context": "x" * 200,
                "reward": 1.0,
                "signal": "positive_strong",
            }
        )
        assert score <= 1.0


class TestExtractDateKey:
    def test_iso_format(self):
        assert extract_date_key("2026-02-14T19:16:08Z") == "2026-02-14"

    def test_iso_with_microseconds(self):
        assert extract_date_key("2026-02-14T20:00:47.090451+00:00") == "2026-02-14"

    def test_empty_string(self):
        assert extract_date_key("") == "unknown"

    def test_short_string(self):
        assert extract_date_key("2026") == "unknown"

    def test_plain_date(self):
        assert extract_date_key("2026-02-14T00:00:00.000Z") == "2026-02-14"


class TestLoadJsonl:
    def test_load_valid_file(self, tmp_path):
        f = tmp_path / "test.jsonl"
        f.write_text('{"a": 1}\n{"b": 2}\n')
        entries = load_jsonl(f)
        assert len(entries) == 2
        assert entries[0] == {"a": 1}

    def test_skip_malformed_lines(self, tmp_path):
        f = tmp_path / "test.jsonl"
        f.write_text('{"a": 1}\nBAD LINE\n{"b": 2}\n')
        entries = load_jsonl(f)
        assert len(entries) == 2

    def test_nonexistent_file(self, tmp_path):
        entries = load_jsonl(tmp_path / "nope.jsonl")
        assert entries == []

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.jsonl"
        f.write_text("")
        entries = load_jsonl(f)
        assert entries == []


class TestConsolidateScene:
    def test_basic_scene(self):
        entries = [
            {"signal": "positive", "intensity": 3, "context": "Good work on the CI fix"},
            {"signal": "negative", "intensity": 4, "context": "CRITICAL ERROR - User frustrated"},
            {"signal": "positive", "intensity": 3, "context": "Thumbs up for clean code"},
        ]
        result = consolidate_scene("2026-02-14:general", entries)

        assert result["scene"] == "2026-02-14:general"
        assert result["entry_count"] == 3
        assert result["positive"] == 2
        assert result["negative"] == 1
        assert result["satisfaction_rate"] == pytest.approx(0.67, abs=0.01)
        assert result["avg_salience"] > 0
        assert len(result["key_contexts"]) <= 5

    def test_noise_filtering_in_scene(self):
        entries = [
            {"principle": "Avoid: unknown decision", "context": "thumbs up"},
            {"principle": "Real principle here", "context": "Something meaningful and long enough"},
        ]
        result = consolidate_scene("2026-02-04:general", entries)
        assert result["noise_filtered"] == 1

    def test_session_json_filtered(self):
        entries = [
            {"context": '{"session_id":"abc-123","transcript_path":"/Users/..."}'},
            {"context": "Real feedback about architecture decisions that matter"},
        ]
        result = consolidate_scene("2026-02-14:general", entries)
        # Session JSON should not appear in key_contexts
        for ctx in result["key_contexts"]:
            assert "session_id" not in ctx

    def test_empty_scene(self):
        result = consolidate_scene("2026-02-14:general", [])
        assert result["entry_count"] == 0
        assert result["satisfaction_rate"] == 0

    def test_dedup_contexts(self):
        entries = [
            {"context": "Same feedback repeated in multiple entries"},
            {"context": "Same feedback repeated in multiple entries"},
            {"context": "Same feedback repeated in multiple entries"},
        ]
        result = consolidate_scene("2026-02-14:general", entries)
        assert len(result["key_contexts"]) == 1
