"""
Multi-Agent AI Trading System (2025 Standard)

Architecture inspired by:
- AlphaQuanter: Tool-orchestrated agentic RL framework
- P1GPT: Multi-agent LLM for multi-modal financial analysis
- Hi-DARTS: Hierarchical meta-agent coordination
- Trading-R1: LLM reasoning with reinforcement learning

Agents:
- ExecutionAgent: Order execution and timing optimization
- FundFlowAgent: Institutional fund flow signals
- MacroeconomicAgent: Macro regime assessment
- MomentumAgent: Technical momentum analysis
- PerplexityResearchAgent: Deep research and backtesting
- RLFilter: Reinforcement learning trade filter
- SandboxAgent: Safe simulation environment
"""

__version__ = "2.0.0"

from .base_agent import BaseAgent
from .execution_agent import ExecutionAgent
from .fund_flow_agent import FundFlowAgent, FundFlowSignal
from .macro_agent import MacroeconomicAgent
from .momentum_agent import MomentumAgent, MomentumSignal
from .research_agent import PerplexityResearchAgent
from .rl_agent import RLFilter
from .sandbox_agent import SandboxAgent, SandboxCapabilities, SandboxResult

__all__ = [
    "BaseAgent",
    "ExecutionAgent",
    "FundFlowAgent",
    "FundFlowSignal",
    "MacroeconomicAgent",
    "MomentumAgent",
    "MomentumSignal",
    "PerplexityResearchAgent",
    "RLFilter",
    "SandboxAgent",
    "SandboxCapabilities",
    "SandboxResult",
]
