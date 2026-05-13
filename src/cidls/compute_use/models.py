"""
compute_use.models - Data models for ComputeUse agentic loop.

Anthropic Computer Use API:
  tool type : computer_20251124
  beta      : computer-use-2025-11-24
  ref       : https://docs.anthropic.com/en/docs/computer-use
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum


class ActionType(str, Enum):
    """Types of computer actions the agent can perform."""
    SCREENSHOT = "screenshot"
    CLICK = "left_click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    KEY = "key"
    SCROLL = "scroll"
    MOVE = "mouse_move"
    DRAG = "left_click_drag"
    CURSOR_POSITION = "cursor_position"


class StopReason(str, Enum):
    """Why the agentic loop terminated."""
    END_TURN = "end_turn"
    MAX_TOKENS = "max_tokens"
    TOOL_USE = "tool_use"
    STOP_SEQUENCE = "stop_sequence"
    ERROR = "error"
    MAX_ITERATIONS = "max_iterations"


@dataclass
class ComputerAction:
    """A single computer action produced by the model."""
    action: ActionType
    coordinate: tuple[int, int] | None = None  # (x, y)
    text: str | None = None
    key: str | None = None
    direction: str | None = None
    amount: int | None = None
    start_coordinate: tuple[int, int] | None = None

    def to_input(self) -> dict:
        """Serialise to Anthropic tool_result input format."""
        payload: dict = {"action": self.action.value}
        if self.coordinate is not None:
            payload["coordinate"] = list(self.coordinate)
        if self.text is not None:
            payload["text"] = self.text
        if self.key is not None:
            payload["key"] = self.key
        if self.direction is not None:
            payload["direction"] = self.direction
        if self.amount is not None:
            payload["amount"] = self.amount
        if self.start_coordinate is not None:
            payload["start_coordinate"] = list(self.start_coordinate)
        return payload


@dataclass
class EvolutionTask:
    """A CIDLS autonomous-evolution task driven by ComputeUse."""
    task_id: str
    description: str
    goal: str
    max_iterations: int = 20
    screenshot_dir: Path = field(default_factory=lambda: Path("reports/compute_use"))
    evidence_paths: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    success: bool | None = None
    failure_reason: str | None = None
    iterations_used: int = 0


@dataclass
class AgentResult:
    """Result of one ComputeUse agentic loop run."""
    task_id: str
    stop_reason: StopReason
    iterations: int
    success: bool
    summary: str
    evidence_paths: list[str] = field(default_factory=list)
    final_message: str = ""
    error: str | None = None
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime = field(default_factory=datetime.now)


@dataclass
class LoopState:
    """Internal state threaded through the agentic loop."""
    messages: list[dict] = field(default_factory=list)
    iteration: int = 0
    screenshots: list[str] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    last_tool_use_id: str | None = None
