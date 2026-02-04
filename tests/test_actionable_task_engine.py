"""
Tests for ActionableTaskEngine.

Validates the Actionable Communication Framework:
1. Task creation with goals, owners, deadlines
2. Verification before completion
3. Dependency management (blocked_by/blocks)
4. Escalation on deadline breach
5. CEO approval workflow
"""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestration.actionable_task_engine import (
    ActionableTaskEngine,
    TaskStatus,
    TaskOwner,
)


@pytest.fixture
def engine(tmp_path):
    """Create engine with temp storage."""
    # Patch the TASKS_FILE to use temp directory
    tasks_file = tmp_path / "actionable_tasks.json"
    with patch("src.orchestration.actionable_task_engine.TASKS_FILE", tasks_file):
        with patch("src.orchestration.actionable_task_engine.DATA_DIR", tmp_path):
            eng = ActionableTaskEngine()
            yield eng


class TestTaskCreation:
    """Test Framework Steps 1-5: Goal, Tasks, Owners, Deadlines, Criteria."""

    def test_create_trade_entry_tasks_creates_7_tasks(self, engine):
        """Trade entry should create 7 sequential tasks."""
        task_ids = engine.create_trade_entry_tasks(
            ticker="SPY", strategy="iron_condor", parameters={"dte": 35, "max_loss": 500}
        )

        assert len(task_ids) == 7
        assert "checklist" in task_ids[0]
        assert "smoke" in task_ids[1]
        assert "gateway" in task_ids[2]
        assert "approval" in task_ids[3]
        assert "execute" in task_ids[4]
        assert "stoploss" in task_ids[5]
        assert "rag" in task_ids[6]

    def test_tasks_have_correct_owners(self, engine):
        """CTO executes, CEO approves."""
        task_ids = engine.create_trade_entry_tasks(
            ticker="SPY", strategy="iron_condor", parameters={}
        )

        # Approval task should be CEO
        approval_task = engine.tasks[task_ids[3]]
        assert approval_task.owner == TaskOwner.CEO

        # Other tasks should be CTO
        for i, tid in enumerate(task_ids):
            if i != 3:  # Skip approval
                assert engine.tasks[tid].owner == TaskOwner.CTO

    def test_tasks_have_deadlines(self, engine):
        """All tasks should have deadlines."""
        task_ids = engine.create_trade_entry_tasks(
            ticker="SPY", strategy="iron_condor", parameters={}, deadline_hours=2
        )

        for tid in task_ids:
            task = engine.tasks[tid]
            assert task.deadline is not None
            deadline = datetime.fromisoformat(task.deadline.replace("Z", ""))
            assert deadline > datetime.utcnow()

    def test_tasks_have_success_criteria(self, engine):
        """Each task should have success criteria."""
        task_ids = engine.create_trade_entry_tasks(
            ticker="SPY", strategy="iron_condor", parameters={}
        )

        for tid in task_ids:
            task = engine.tasks[tid]
            assert len(task.success_criteria) > 0
            assert task.success_criteria[0].get("check_function") is not None

    def test_tasks_have_dependencies(self, engine):
        """Tasks should be properly chained."""
        task_ids = engine.create_trade_entry_tasks(
            ticker="SPY", strategy="iron_condor", parameters={}
        )

        # First task has no dependencies
        assert len(engine.tasks[task_ids[0]].blocked_by) == 0

        # Subsequent tasks depend on previous
        for i in range(1, len(task_ids)):
            task = engine.tasks[task_ids[i]]
            assert task_ids[i - 1] in task.blocked_by


class TestTaskExecution:
    """Test task lifecycle: start, verify, complete."""

    def test_start_task_checks_dependencies(self, engine):
        """Cannot start blocked task."""
        task_ids = engine.create_trade_entry_tasks(
            ticker="SPY", strategy="iron_condor", parameters={}
        )

        # Try to start second task (should fail - first not done)
        result = engine.start_task(task_ids[1])
        assert result is False
        assert engine.tasks[task_ids[1]].status == TaskStatus.BLOCKED

    def test_start_first_task_succeeds(self, engine):
        """First task has no dependencies."""
        task_ids = engine.create_trade_entry_tasks(
            ticker="SPY", strategy="iron_condor", parameters={}
        )

        result = engine.start_task(task_ids[0])
        assert result is True
        assert engine.tasks[task_ids[0]].status == TaskStatus.IN_PROGRESS

    def test_complete_requires_verification(self, engine):
        """Cannot complete unverified task."""
        task_ids = engine.create_trade_entry_tasks(
            ticker="SPY", strategy="iron_condor", parameters={}
        )

        engine.start_task(task_ids[0])

        # Try to complete without verification
        result = engine.complete_task(task_ids[0])
        assert result is False

    def test_completing_unblocks_dependents(self, engine):
        """Completing a task unblocks tasks that depend on it."""
        task_ids = engine.create_trade_entry_tasks(
            ticker="SPY", strategy="iron_condor", parameters={}
        )

        # Manually set first task to verified and complete
        engine.tasks[task_ids[0]].status = TaskStatus.VERIFIED
        engine.complete_task(task_ids[0])

        # Second task should no longer be blocked by first
        task2 = engine.tasks[task_ids[1]]
        assert task_ids[0] not in task2.blocked_by


class TestCEOApproval:
    """Test CEO approval workflow per LL-325."""

    def test_approval_task_starts_awaiting(self, engine):
        """Approval tasks start in AWAITING_APPROVAL."""
        task_ids = engine.create_trade_entry_tasks(
            ticker="SPY", strategy="iron_condor", parameters={}
        )

        approval_task = engine.tasks[task_ids[3]]
        assert approval_task.status == TaskStatus.AWAITING_APPROVAL
        assert approval_task.owner == TaskOwner.CEO

    def test_ceo_can_approve(self, engine):
        """CEO approval transitions to VERIFIED."""
        task_ids = engine.create_trade_entry_tasks(
            ticker="SPY", strategy="iron_condor", parameters={}
        )

        approval_id = task_ids[3]
        result = engine.approve_task(approval_id, approver="Igor")

        assert result is True
        assert engine.tasks[approval_id].status == TaskStatus.VERIFIED

    def test_exit_requires_ceo_approval(self, engine):
        """Trade exit requires CEO approval per LL-325."""
        task_ids = engine.create_trade_exit_tasks(
            ticker="SPY", position_id="pos_123", exit_reason="50% profit"
        )

        # Find approval task
        approval_tasks = [tid for tid in task_ids if engine.tasks[tid].owner == TaskOwner.CEO]

        assert len(approval_tasks) > 0
        assert engine.tasks[approval_tasks[0]].status == TaskStatus.AWAITING_APPROVAL


class TestEscalation:
    """Test deadline enforcement and escalation."""

    def test_overdue_tasks_escalate(self, engine):
        """Overdue tasks should be escalated."""
        task_ids = engine.create_trade_entry_tasks(
            ticker="SPY",
            strategy="iron_condor",
            parameters={},
            deadline_hours=0,  # Immediate deadline
        )

        # Set deadline to past
        past_deadline = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
        engine.tasks[task_ids[0]].deadline = past_deadline

        escalations = engine.check_deadlines()

        assert len(escalations) > 0
        assert escalations[0]["task_id"] == task_ids[0]
        assert engine.tasks[task_ids[0]].status == TaskStatus.ESCALATED

    def test_escalation_count_increments(self, engine):
        """Multiple escalations should increment count."""
        task_ids = engine.create_trade_entry_tasks(
            ticker="SPY", strategy="iron_condor", parameters={}, deadline_hours=0
        )

        past_deadline = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
        engine.tasks[task_ids[0]].deadline = past_deadline

        engine.check_deadlines()
        engine.check_deadlines()

        assert engine.tasks[task_ids[0]].escalation_count == 2


class TestStatusReport:
    """Test Framework Step 7: Check-in reporting."""

    def test_status_report_structure(self, engine):
        """Report should have all required sections."""
        engine.create_trade_entry_tasks(ticker="SPY", strategy="iron_condor", parameters={})

        report = engine.get_status_report()

        assert "summary" in report
        assert "done" in report
        assert "blocked" in report
        assert "awaiting_approval" in report
        assert "next" in report

    def test_report_counts_correct(self, engine):
        """Report should count tasks correctly."""
        engine.create_trade_entry_tasks(ticker="SPY", strategy="iron_condor", parameters={})

        report = engine.get_status_report()

        assert report["summary"]["total"] == 7
        assert report["summary"]["awaiting_approval"] == 1  # CEO approval task


class TestPersistence:
    """Test task storage and retrieval."""

    def test_tasks_persist_to_file(self, engine, tmp_path):
        """Tasks should be saved to JSON file."""
        with patch("src.orchestration.actionable_task_engine.TASKS_FILE", tmp_path / "tasks.json"):
            engine.create_trade_entry_tasks(ticker="SPY", strategy="iron_condor", parameters={})

            # Check file exists and has content
            tasks_file = tmp_path / "tasks.json"
            assert tasks_file.exists()

            with open(tasks_file) as f:
                data = json.load(f)

            assert data["task_count"] == 7
            assert len(data["tasks"]) == 7


class TestVerification:
    """Test verification functions."""

    def test_verify_calls_check_function(self, engine):
        """Verification should call registered check function."""
        call_count = [0]

        def mock_verify(task, context):
            call_count[0] += 1
            return (True, "All passed")

        # Replace the verifier in the engine's registry
        engine._verifiers["checklist_passed"] = mock_verify

        task_ids = engine.create_trade_entry_tasks(
            ticker="SPY", strategy="iron_condor", parameters={}
        )

        engine.verify_task(task_ids[0])

        assert call_count[0] == 1

    def test_verification_records_results(self, engine):
        """Verification results should be recorded."""
        task_ids = engine.create_trade_entry_tasks(
            ticker="SPY", strategy="iron_condor", parameters={}
        )

        # Mock the verifier to pass
        engine._verifiers["checklist_passed"] = lambda t, c: (True, "OK")

        engine.verify_task(task_ids[0])

        task = engine.tasks[task_ids[0]]
        assert len(task.verification_results) > 0
        assert task.verification_results[0]["passed"] is True


class TestIntegration:
    """Integration tests with trading system components."""

    @patch("src.risk.pre_trade_checklist.PreTradeChecklist.validate")
    def test_checklist_integration(self, mock_validate, engine):
        """Should integrate with PreTradeChecklist."""
        mock_validate.return_value = (True, [])

        task_ids = engine.create_trade_entry_tasks(
            ticker="SPY",
            strategy="iron_condor",
            parameters={"max_loss": 500, "dte": 35, "stop_loss_defined": True},
        )

        passed, reason = engine._verify_checklist(engine.tasks[task_ids[0]], {})

        assert passed is True
        mock_validate.assert_called_once()

    @patch("src.safety.pre_trade_smoke_test.run_smoke_tests")
    def test_smoke_test_integration(self, mock_smoke, engine):
        """Should integrate with smoke tests."""
        mock_result = MagicMock()
        mock_result.all_passed = True
        mock_smoke.return_value = mock_result

        task_ids = engine.create_trade_entry_tasks(
            ticker="SPY", strategy="iron_condor", parameters={}
        )

        passed, reason = engine._verify_smoke_tests(engine.tasks[task_ids[1]], {})

        assert passed is True
