"""
Daggr Workflow Visualizer - Visual DAG for Trading Pipelines.

Turns AI workflows into visual graphs for:
- Debugging trading decisions
- Inspecting gate outputs
- Replaying failed workflows
- Performance profiling

Based on Daggr: Code-first Python library for AI workflow visualization.

Author: Claude CTO
Date: February 2026
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional
import time

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
WORKFLOW_STATE_DIR = PROJECT_ROOT / "data" / "workflow_state"
WORKFLOW_HISTORY_FILE = WORKFLOW_STATE_DIR / "workflow_history.jsonl"


class NodeStatus(Enum):
    """Status of a workflow node."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class NodeType(Enum):
    """Type of workflow node."""

    GATE = "gate"  # Trading gate (security, momentum, risk, etc.)
    TRANSFORM = "transform"  # Data transformation
    DECISION = "decision"  # Branch point
    ACTION = "action"  # External action (API call, trade execution)
    CHECKPOINT = "checkpoint"  # State checkpoint


@dataclass
class NodeResult:
    """Result from executing a workflow node."""

    node_id: str
    status: NodeStatus
    output: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass
class WorkflowNode:
    """A single node in the workflow DAG."""

    node_id: str
    name: str
    node_type: NodeType
    function: Optional[Callable] = None
    inputs: list[str] = field(default_factory=list)  # Node IDs this depends on
    outputs: list[str] = field(default_factory=list)  # Node IDs that depend on this
    status: NodeStatus = NodeStatus.PENDING
    result: Optional[NodeResult] = None
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type.value,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "status": self.status.value,
            "description": self.description,
            "result": self.result.to_dict() if self.result else None,
        }


class WorkflowGraph:
    """
    Visual workflow graph for trading pipelines.

    Provides:
    - DAG construction with automatic dependency tracking
    - Execution with intermediate state capture
    - Visualization for debugging
    - Replay from any checkpoint
    - Performance profiling
    """

    def __init__(self, name: str = "trading_workflow"):
        self.name = name
        self.nodes: dict[str, WorkflowNode] = {}
        self.execution_order: list[str] = []
        self.state: dict[str, Any] = {}  # Intermediate outputs
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Create necessary directories."""
        WORKFLOW_STATE_DIR.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # Graph Construction
    # =========================================================================

    def add_node(
        self,
        node_id: str,
        name: str,
        node_type: NodeType,
        function: Optional[Callable] = None,
        depends_on: list[str] = None,
        description: str = "",
    ) -> "WorkflowGraph":
        """
        Add a node to the workflow graph.

        Args:
            node_id: Unique identifier for the node
            name: Human-readable name
            node_type: Type of node (gate, transform, decision, action)
            function: Callable to execute (receives state dict, returns output)
            depends_on: List of node IDs this node depends on
            description: Description of what this node does

        Returns:
            Self for chaining
        """
        depends_on = depends_on or []

        node = WorkflowNode(
            node_id=node_id,
            name=name,
            node_type=node_type,
            function=function,
            inputs=depends_on,
            description=description,
        )

        self.nodes[node_id] = node

        # Update outputs of dependency nodes
        for dep_id in depends_on:
            if dep_id in self.nodes:
                self.nodes[dep_id].outputs.append(node_id)

        # Recompute execution order
        self._compute_execution_order()

        return self

    def _compute_execution_order(self):
        """Topological sort to determine execution order."""
        visited = set()
        order = []

        def visit(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)

            node = self.nodes.get(node_id)
            if node:
                for dep_id in node.inputs:
                    visit(dep_id)
                order.append(node_id)

        for node_id in self.nodes:
            visit(node_id)

        self.execution_order = order

    # =========================================================================
    # Execution
    # =========================================================================

    def execute(self, initial_state: dict = None) -> dict[str, NodeResult]:
        """
        Execute the workflow graph.

        Args:
            initial_state: Initial state to pass to first nodes

        Returns:
            Dict of node_id -> NodeResult
        """
        self.state = initial_state or {}
        self.start_time = time.time()
        results = {}

        for node_id in self.execution_order:
            node = self.nodes[node_id]

            # Check if dependencies completed successfully
            deps_ok = all(
                self.nodes[dep_id].status == NodeStatus.COMPLETED
                for dep_id in node.inputs
                if dep_id in self.nodes
            )

            if not deps_ok:
                node.status = NodeStatus.SKIPPED
                node.result = NodeResult(
                    node_id=node_id, status=NodeStatus.SKIPPED, error="Dependencies not satisfied"
                )
                results[node_id] = node.result
                continue

            # Execute the node
            node.status = NodeStatus.RUNNING
            start = time.time()

            try:
                if node.function:
                    output = node.function(self.state)
                    self.state[node_id] = output
                else:
                    output = None

                elapsed_ms = (time.time() - start) * 1000
                node.status = NodeStatus.COMPLETED
                node.result = NodeResult(
                    node_id=node_id,
                    status=NodeStatus.COMPLETED,
                    output=output,
                    execution_time_ms=elapsed_ms,
                )

            except Exception as e:
                elapsed_ms = (time.time() - start) * 1000
                node.status = NodeStatus.FAILED
                node.result = NodeResult(
                    node_id=node_id,
                    status=NodeStatus.FAILED,
                    error=str(e),
                    execution_time_ms=elapsed_ms,
                )
                logger.error(f"Node {node_id} failed: {e}")

            results[node_id] = node.result

        self.end_time = time.time()
        self._save_execution()

        return results

    def execute_from(self, checkpoint_id: str, state: dict = None) -> dict[str, NodeResult]:
        """
        Execute workflow starting from a specific checkpoint.

        Useful for replaying failed workflows from the point of failure.
        """
        self.state = state or {}

        # Find index of checkpoint in execution order
        try:
            start_idx = self.execution_order.index(checkpoint_id)
        except ValueError:
            raise ValueError(f"Checkpoint {checkpoint_id} not found in workflow")

        # Mark prior nodes as completed
        for i, node_id in enumerate(self.execution_order):
            if i < start_idx:
                self.nodes[node_id].status = NodeStatus.COMPLETED

        # Execute from checkpoint
        results = {}
        for node_id in self.execution_order[start_idx:]:
            node = self.nodes[node_id]
            node.status = NodeStatus.RUNNING
            start = time.time()

            try:
                if node.function:
                    output = node.function(self.state)
                    self.state[node_id] = output
                else:
                    output = None

                elapsed_ms = (time.time() - start) * 1000
                node.status = NodeStatus.COMPLETED
                node.result = NodeResult(
                    node_id=node_id,
                    status=NodeStatus.COMPLETED,
                    output=output,
                    execution_time_ms=elapsed_ms,
                )
            except Exception as e:
                elapsed_ms = (time.time() - start) * 1000
                node.status = NodeStatus.FAILED
                node.result = NodeResult(
                    node_id=node_id,
                    status=NodeStatus.FAILED,
                    error=str(e),
                    execution_time_ms=elapsed_ms,
                )

            results[node_id] = node.result

        return results

    # =========================================================================
    # Visualization
    # =========================================================================

    def to_mermaid(self) -> str:
        """
        Generate Mermaid diagram syntax for the workflow.

        Can be rendered in GitHub, Notion, or any Mermaid-compatible viewer.
        """
        lines = ["graph TD"]

        # Add nodes with status colors
        status_styles = {
            NodeStatus.PENDING: "fill:#f9f9f9,stroke:#999",
            NodeStatus.RUNNING: "fill:#fff3cd,stroke:#ffc107",
            NodeStatus.COMPLETED: "fill:#d4edda,stroke:#28a745",
            NodeStatus.FAILED: "fill:#f8d7da,stroke:#dc3545",
            NodeStatus.SKIPPED: "fill:#e2e3e5,stroke:#6c757d",
        }

        # Add nodes
        for node_id, node in self.nodes.items():
            # Escape special characters
            safe_name = node.name.replace('"', "'")

            # Add execution time if available
            time_str = ""
            if node.result and node.result.execution_time_ms > 0:
                time_str = f" ({node.result.execution_time_ms:.0f}ms)"

            lines.append(f'    {node_id}["{safe_name}{time_str}"]')

        # Add edges
        for node_id, node in self.nodes.items():
            for dep_id in node.inputs:
                lines.append(f"    {dep_id} --> {node_id}")

        # Add styles
        for node_id, node in self.nodes.items():
            style = status_styles.get(node.status, status_styles[NodeStatus.PENDING])
            lines.append(f"    style {node_id} {style}")

        return "\n".join(lines)

    def to_ascii(self) -> str:
        """
        Generate ASCII art representation of the workflow.

        Useful for terminal output.
        """
        lines = [f"Workflow: {self.name}", "=" * 50]

        status_icons = {
            NodeStatus.PENDING: "○",
            NodeStatus.RUNNING: "◐",
            NodeStatus.COMPLETED: "●",
            NodeStatus.FAILED: "✗",
            NodeStatus.SKIPPED: "◌",
        }

        for i, node_id in enumerate(self.execution_order):
            node = self.nodes[node_id]
            icon = status_icons.get(node.status, "?")

            # Show timing if available
            time_str = ""
            if node.result and node.result.execution_time_ms > 0:
                time_str = f" [{node.result.execution_time_ms:.0f}ms]"

            # Show error if failed
            error_str = ""
            if node.result and node.result.error:
                error_str = f" ERROR: {node.result.error[:50]}"

            # Indentation based on dependencies
            indent = "  " * len(node.inputs) if node.inputs else ""

            lines.append(f"{indent}{icon} {node.name}{time_str}{error_str}")

            # Show connection to next node
            if i < len(self.execution_order) - 1:
                next_node = self.nodes[self.execution_order[i + 1]]
                if node_id in next_node.inputs:
                    lines.append(f"{indent}  │")
                    lines.append(f"{indent}  ▼")

        # Summary
        total_time = (self.end_time - self.start_time) * 1000 if self.end_time else 0
        completed = sum(1 for n in self.nodes.values() if n.status == NodeStatus.COMPLETED)
        failed = sum(1 for n in self.nodes.values() if n.status == NodeStatus.FAILED)

        lines.append("=" * 50)
        lines.append(f"Total: {len(self.nodes)} nodes | Completed: {completed} | Failed: {failed}")
        lines.append(f"Execution time: {total_time:.0f}ms")

        return "\n".join(lines)

    def get_summary(self) -> dict:
        """Get execution summary."""
        return {
            "name": self.name,
            "total_nodes": len(self.nodes),
            "completed": sum(1 for n in self.nodes.values() if n.status == NodeStatus.COMPLETED),
            "failed": sum(1 for n in self.nodes.values() if n.status == NodeStatus.FAILED),
            "skipped": sum(1 for n in self.nodes.values() if n.status == NodeStatus.SKIPPED),
            "total_time_ms": (self.end_time - self.start_time) * 1000 if self.end_time else 0,
            "execution_order": self.execution_order,
        }

    # =========================================================================
    # Persistence
    # =========================================================================

    def _save_execution(self):
        """Save execution history for debugging."""
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "workflow": self.name,
            "summary": self.get_summary(),
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
        }

        with open(WORKFLOW_HISTORY_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")

    def save_state(self, filepath: Path) -> None:
        """Save workflow state for later replay."""
        data = {
            "name": self.name,
            "state": {k: str(v)[:500] for k, v in self.state.items()},  # Truncate large values
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "execution_order": self.execution_order,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)


# =========================================================================
# Trading Pipeline Factory
# =========================================================================


def create_trading_pipeline(ticker: str) -> WorkflowGraph:
    """
    Create a standard trading pipeline workflow.

    Gates:
    - Gate S: Security validation
    - Gate 0: Psychology check
    - Gate 1: Momentum filter
    - Gate 1.5: Bull/Bear debate
    - Gate 3: LLM sentiment
    - Gate 4: Risk sizing
    - Gate 5: Execution
    """
    workflow = WorkflowGraph(name=f"trading_pipeline_{ticker}")

    # Input node
    workflow.add_node(
        node_id="input",
        name="Market Data Input",
        node_type=NodeType.GATE,
        description=f"Fetch market data for {ticker}",
    )

    # Security gate
    workflow.add_node(
        node_id="gate_s",
        name="Gate S: Security",
        node_type=NodeType.GATE,
        depends_on=["input"],
        description="Validate request security, check for injection",
    )

    # Psychology check
    workflow.add_node(
        node_id="gate_0",
        name="Gate 0: Psychology",
        node_type=NodeType.GATE,
        depends_on=["gate_s"],
        description="Pre-trade psychology check (FOMO, fear, etc.)",
    )

    # Momentum filter
    workflow.add_node(
        node_id="gate_1",
        name="Gate 1: Momentum",
        node_type=NodeType.GATE,
        depends_on=["gate_0"],
        description="Calculate momentum signals (RSI, MACD, etc.)",
    )

    # RAG query
    workflow.add_node(
        node_id="rag_query",
        name="RAG: Lessons Query",
        node_type=NodeType.TRANSFORM,
        depends_on=["gate_1"],
        description="Query lessons learned RAG for relevant context",
    )

    # Bull/Bear debate
    workflow.add_node(
        node_id="gate_1_5",
        name="Gate 1.5: Debate",
        node_type=NodeType.DECISION,
        depends_on=["gate_1", "rag_query"],
        description="Bull vs Bear agent debate on trade thesis",
    )

    # LLM sentiment
    workflow.add_node(
        node_id="gate_3",
        name="Gate 3: LLM Sentiment",
        node_type=NodeType.GATE,
        depends_on=["gate_1_5"],
        description="LLM-based sentiment analysis",
    )

    # Risk sizing
    workflow.add_node(
        node_id="gate_4",
        name="Gate 4: Risk Sizing",
        node_type=NodeType.GATE,
        depends_on=["gate_3"],
        description="Calculate position size based on risk rules",
    )

    # Pre-trade checklist
    workflow.add_node(
        node_id="checklist",
        name="Pre-Trade Checklist",
        node_type=NodeType.CHECKPOINT,
        depends_on=["gate_4"],
        description="7-item mandatory checklist per CLAUDE.md",
    )

    # CEO approval
    workflow.add_node(
        node_id="ceo_approval",
        name="CEO Approval",
        node_type=NodeType.DECISION,
        depends_on=["checklist"],
        description="CEO must approve before execution",
    )

    # Execution
    workflow.add_node(
        node_id="gate_5",
        name="Gate 5: Execution",
        node_type=NodeType.ACTION,
        depends_on=["ceo_approval"],
        description="Execute trade via Alpaca API",
    )

    # Post-trade logging
    workflow.add_node(
        node_id="rag_log",
        name="RAG: Log Trade",
        node_type=NodeType.ACTION,
        depends_on=["gate_5"],
        description="Log trade to RAG for future learning",
    )

    return workflow


def create_rlhf_pipeline() -> WorkflowGraph:
    """Create RLHF feedback pipeline workflow."""
    workflow = WorkflowGraph(name="rlhf_pipeline")

    workflow.add_node(
        node_id="feedback_input",
        name="User Feedback",
        node_type=NodeType.GATE,
        description="Detect thumbs up/down signal",
    )

    workflow.add_node(
        node_id="intensity",
        name="Intensity Detection",
        node_type=NodeType.TRANSFORM,
        depends_on=["feedback_input"],
        description="Calculate feedback intensity (0.5-1.0)",
    )

    workflow.add_node(
        node_id="jsonl_log",
        name="JSONL Log",
        node_type=NodeType.ACTION,
        depends_on=["intensity"],
        description="Write to feedback-log.jsonl",
    )

    workflow.add_node(
        node_id="lancedb",
        name="LanceDB Update",
        node_type=NodeType.ACTION,
        depends_on=["intensity"],
        description="Add to LanceDB vector store",
    )

    workflow.add_node(
        node_id="thompson",
        name="Thompson Sampling",
        node_type=NodeType.ACTION,
        depends_on=["intensity"],
        description="Update alpha/beta in feedback model",
    )

    workflow.add_node(
        node_id="cortex",
        name="ShieldCortex Sync",
        node_type=NodeType.ACTION,
        depends_on=["jsonl_log", "lancedb", "thompson"],
        description="Sync to Cortex MCP for cross-session persistence",
    )

    return workflow


def create_actionable_task_pipeline(task_type: str) -> WorkflowGraph:
    """Create actionable task pipeline workflow."""
    workflow = WorkflowGraph(name=f"actionable_task_{task_type}")

    if task_type == "trade_entry":
        nodes = [
            ("checklist", "Verify Checklist", NodeType.CHECKPOINT, []),
            ("smoke", "Smoke Tests", NodeType.GATE, ["checklist"]),
            ("gateway", "TradeGateway", NodeType.GATE, ["smoke"]),
            ("approval", "CEO Approval", NodeType.DECISION, ["gateway"]),
            ("execute", "Execute Trade", NodeType.ACTION, ["approval"]),
            ("stoploss", "Set Stop-Loss", NodeType.ACTION, ["execute"]),
            ("rag", "Log to RAG", NodeType.ACTION, ["stoploss"]),
        ]
    elif task_type == "trade_exit":
        nodes = [
            ("verify", "Verify Exit Conditions", NodeType.CHECKPOINT, []),
            ("approval", "CEO Approval", NodeType.DECISION, ["verify"]),
            ("execute", "Close Position", NodeType.ACTION, ["approval"]),
            ("rag", "Log P/L to RAG", NodeType.ACTION, ["execute"]),
        ]
    else:
        nodes = []

    for node_id, name, node_type, deps in nodes:
        workflow.add_node(node_id=node_id, name=name, node_type=node_type, depends_on=deps)

    return workflow


# Singleton factory
_pipelines: dict[str, WorkflowGraph] = {}


def get_trading_pipeline(ticker: str) -> WorkflowGraph:
    """Get or create a trading pipeline for a ticker."""
    key = f"trading_{ticker}"
    if key not in _pipelines:
        _pipelines[key] = create_trading_pipeline(ticker)
    return _pipelines[key]


def get_rlhf_pipeline() -> WorkflowGraph:
    """Get or create the RLHF pipeline."""
    if "rlhf" not in _pipelines:
        _pipelines["rlhf"] = create_rlhf_pipeline()
    return _pipelines["rlhf"]
