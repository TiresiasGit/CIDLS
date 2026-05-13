"""
cidls.compute_use - Anthropic Computer Use integration for CIDLS.

Provides an agentic loop that drives desktop GUI autonomously to
execute CIDLS self-evolution tasks (CU_EVOLVE in AGENTS直交圧縮.md).

Public API:
    ComputeUseAgent      -- main agent class
    ComputeUseUnavailableError
    make_evolution_task  -- EvolutionTask factory
    run_daily_evolution  -- daily 10:00 self-evolution entry point

Availability:
    The anthropic package is optional. All imports raise
    ComputeUseUnavailableError at runtime if not installed.
    Install with: uv add anthropic
"""

from .agent import (
    ComputeUseAgent,
    ComputeUseUnavailableError,
    make_evolution_task,
)
from .evolution_runner import run_daily_evolution
from .models import (
    ActionType,
    AgentResult,
    ComputerAction,
    EvolutionTask,
    LoopState,
    StopReason,
)

__all__ = [
    "ComputeUseAgent",
    "ComputeUseUnavailableError",
    "make_evolution_task",
    "run_daily_evolution",
    "ActionType",
    "AgentResult",
    "ComputerAction",
    "EvolutionTask",
    "LoopState",
    "StopReason",
]
