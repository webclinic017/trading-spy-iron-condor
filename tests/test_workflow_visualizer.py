"""
Tests for Workflow Visualizer.

Validates:
1. Graph construction and topological sort
2. Execution with dependency resolution
3. Failure handling and skip propagation
4. Visualization output (Mermaid, ASCII)
5. Checkpoint and replay
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestration.workflow_visualizer import (
    NodeStatus,
    NodeType,
    WorkflowGraph,
    create_actionable_task_pipeline,
    create_rlhf_pipeline,
    create_trading_pipeline,
)


@pytest.fixture
def workflow(tmp_path):
    """Create workflow with temp storage."""
    with patch("src.orchestration.workflow_visualizer.WORKFLOW_STATE_DIR", tmp_path):
        with patch(
            "src.orchestration.workflow_visualizer.WORKFLOW_HISTORY_FILE",
            tmp_path / "history.jsonl",
        ):
            wf = WorkflowGraph(name="test_workflow")
            yield wf


class TestGraphConstruction:
    """Test DAG construction."""

    def test_add_node(self, workflow):
        """Should add nodes to the graph."""
        workflow.add_node("a", "Node A", NodeType.GATE)
        workflow.add_node("b", "Node B", NodeType.GATE, depends_on=["a"])

        assert "a" in workflow.nodes
        assert "b" in workflow.nodes
        assert workflow.nodes["b"].inputs == ["a"]
        assert "b" in workflow.nodes["a"].outputs

    def test_topological_sort(self, workflow):
        """Should compute correct execution order."""
        workflow.add_node("a", "A", NodeType.GATE)
        workflow.add_node("b", "B", NodeType.GATE, depends_on=["a"])
        workflow.add_node("c", "C", NodeType.GATE, depends_on=["a"])
        workflow.add_node("d", "D", NodeType.GATE, depends_on=["b", "c"])

        order = workflow.execution_order
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")

    def test_chaining(self, workflow):
        """Should support method chaining."""
        workflow.add_node("a", "A", NodeType.GATE).add_node(
            "b", "B", NodeType.GATE, depends_on=["a"]
        )

        assert len(workflow.nodes) == 2


class TestExecution:
    """Test workflow execution."""

    def test_simple_execution(self, workflow):
        """Should execute nodes in order."""
        results = []

        def node_a(state):
            results.append("a")
            return {"value": 1}

        def node_b(state):
            results.append("b")
            return {"value": state["a"]["value"] + 1}

        workflow.add_node("a", "A", NodeType.GATE, function=node_a)
        workflow.add_node("b", "B", NodeType.GATE, function=node_b, depends_on=["a"])

        workflow.execute()

        assert results == ["a", "b"]
        assert workflow.state["a"]["value"] == 1
        assert workflow.state["b"]["value"] == 2

    def test_failure_handling(self, workflow):
        """Should handle node failures gracefully."""

        def failing_node(state):
            raise ValueError("Intentional failure")

        def dependent_node(state):
            return {"value": "should not run"}

        workflow.add_node("a", "A", NodeType.GATE, function=failing_node)
        workflow.add_node(
            "b", "B", NodeType.GATE, function=dependent_node, depends_on=["a"]
        )

        results = workflow.execute()

        assert results["a"].status == NodeStatus.FAILED
        assert results["b"].status == NodeStatus.SKIPPED
        assert "Intentional failure" in results["a"].error

    def test_execution_timing(self, workflow):
        """Should track execution time."""
        import time

        def slow_node(state):
            time.sleep(0.01)
            return {}

        workflow.add_node("a", "A", NodeType.GATE, function=slow_node)
        results = workflow.execute()

        assert results["a"].execution_time_ms >= 10

    def test_parallel_dependencies(self, workflow):
        """Should handle nodes with multiple dependencies."""
        executed = []

        def node_func(name):
            def inner(state):
                executed.append(name)
                return {name: True}

            return inner

        workflow.add_node("a", "A", NodeType.GATE, function=node_func("a"))
        workflow.add_node("b", "B", NodeType.GATE, function=node_func("b"))
        workflow.add_node(
            "c", "C", NodeType.GATE, function=node_func("c"), depends_on=["a", "b"]
        )

        workflow.execute()

        # a and b should run before c
        assert executed.index("a") < executed.index("c")
        assert executed.index("b") < executed.index("c")


class TestCheckpointReplay:
    """Test checkpoint and replay functionality."""

    def test_execute_from_checkpoint(self, workflow):
        """Should execute from a specific checkpoint."""
        executed = []

        def node_func(name):
            def inner(state):
                executed.append(name)
                return {}

            return inner

        workflow.add_node("a", "A", NodeType.GATE, function=node_func("a"))
        workflow.add_node(
            "b", "B", NodeType.CHECKPOINT, function=node_func("b"), depends_on=["a"]
        )
        workflow.add_node(
            "c", "C", NodeType.GATE, function=node_func("c"), depends_on=["b"]
        )

        # Execute from checkpoint b (skipping a)
        workflow.execute_from("b")

        # Only b and c should have executed
        assert "a" not in executed
        assert "b" in executed
        assert "c" in executed


class TestVisualization:
    """Test visualization outputs."""

    def test_mermaid_output(self, workflow):
        """Should generate valid Mermaid syntax."""
        workflow.add_node("a", "Node A", NodeType.GATE)
        workflow.add_node("b", "Node B", NodeType.GATE, depends_on=["a"])

        mermaid = workflow.to_mermaid()

        assert "graph TD" in mermaid
        assert 'a["Node A' in mermaid
        assert 'b["Node B' in mermaid
        assert "a --> b" in mermaid

    def test_ascii_output(self, workflow):
        """Should generate ASCII representation."""
        workflow.add_node("a", "Node A", NodeType.GATE)
        workflow.add_node("b", "Node B", NodeType.GATE, depends_on=["a"])

        ascii_art = workflow.to_ascii()

        assert "Node A" in ascii_art
        assert "Node B" in ascii_art
        assert "○" in ascii_art or "●" in ascii_art  # Status icons

    def test_mermaid_with_timing(self, workflow):
        """Should include timing in Mermaid output after execution."""
        import time

        def slow_node(state):
            time.sleep(0.01)  # 10ms to ensure measurable timing
            return {}

        workflow.add_node("a", "A", NodeType.GATE, function=slow_node)
        workflow.execute()

        mermaid = workflow.to_mermaid()
        assert "ms)" in mermaid  # Timing should be included

    def test_summary(self, workflow):
        """Should provide execution summary."""
        workflow.add_node("a", "A", NodeType.GATE, function=lambda s: {})
        workflow.add_node(
            "b", "B", NodeType.GATE, function=lambda s: {}, depends_on=["a"]
        )
        workflow.execute()

        summary = workflow.get_summary()

        assert summary["total_nodes"] == 2
        assert summary["completed"] == 2
        assert summary["failed"] == 0


class TestTradingPipeline:
    """Test pre-built trading pipeline."""

    def test_create_trading_pipeline(self):
        """Should create a complete trading pipeline."""
        pipeline = create_trading_pipeline("SPY")

        assert len(pipeline.nodes) > 0
        assert "gate_1" in pipeline.nodes
        assert "gate_4" in pipeline.nodes
        assert "gate_5" in pipeline.nodes

    def test_trading_pipeline_dependencies(self):
        """Trading pipeline should have correct dependencies."""
        pipeline = create_trading_pipeline("SPY")

        # Execution should come after approval
        exec_node = pipeline.nodes["gate_5"]
        assert "ceo_approval" in exec_node.inputs

        # Approval should come after checklist
        approval_node = pipeline.nodes["ceo_approval"]
        assert "checklist" in approval_node.inputs


class TestRLHFPipeline:
    """Test RLHF feedback pipeline."""

    def test_create_rlhf_pipeline(self):
        """Should create RLHF pipeline."""
        pipeline = create_rlhf_pipeline()

        assert "feedback_input" in pipeline.nodes
        assert "thompson" in pipeline.nodes
        assert "cortex" in pipeline.nodes

    def test_rlhf_parallel_writes(self):
        """RLHF pipeline should have parallel write nodes."""
        pipeline = create_rlhf_pipeline()

        # jsonl_log, lancedb, thompson should all depend on intensity
        assert "intensity" in pipeline.nodes["jsonl_log"].inputs
        assert "intensity" in pipeline.nodes["lancedb"].inputs
        assert "intensity" in pipeline.nodes["thompson"].inputs


class TestActionableTaskPipeline:
    """Test actionable task pipelines."""

    def test_trade_entry_pipeline(self):
        """Should create trade entry pipeline."""
        pipeline = create_actionable_task_pipeline("trade_entry")

        assert "checklist" in pipeline.nodes
        assert "approval" in pipeline.nodes
        assert "execute" in pipeline.nodes
        assert "stoploss" in pipeline.nodes

    def test_trade_exit_pipeline(self):
        """Should create trade exit pipeline."""
        pipeline = create_actionable_task_pipeline("trade_exit")

        assert "verify" in pipeline.nodes
        assert "approval" in pipeline.nodes
        assert "execute" in pipeline.nodes

    def test_exit_requires_approval(self):
        """Trade exit should require CEO approval."""
        pipeline = create_actionable_task_pipeline("trade_exit")

        exec_node = pipeline.nodes["execute"]
        assert "approval" in exec_node.inputs


class TestPersistence:
    """Test state persistence."""

    def test_save_state(self, workflow, tmp_path):
        """Should save workflow state to file."""
        workflow.add_node("a", "A", NodeType.GATE, function=lambda s: {"result": 42})
        workflow.execute()

        state_file = tmp_path / "state.json"
        workflow.save_state(state_file)

        assert state_file.exists()

        import json

        with open(state_file) as f:
            data = json.load(f)

        assert data["name"] == "test_workflow"
        assert "a" in data["nodes"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
