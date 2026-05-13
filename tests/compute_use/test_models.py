"""Unit tests for compute_use.models."""

from pathlib import Path

import pytest

from cidls.compute_use.models import (
    ActionType,
    AgentResult,
    ComputerAction,
    EvolutionTask,
    LoopState,
    StopReason,
)


class TestComputerAction:
    def test_to_input_click(self) -> None:
        action = ComputerAction(
            action=ActionType.CLICK,
            coordinate=(100, 200),
        )
        payload = action.to_input()
        assert payload["action"] == "left_click"
        assert payload["coordinate"] == [100, 200]

    def test_to_input_type(self) -> None:
        action = ComputerAction(
            action=ActionType.TYPE,
            text="hello world",
        )
        payload = action.to_input()
        assert payload["action"] == "type"
        assert payload["text"] == "hello world"
        assert "coordinate" not in payload

    def test_to_input_key(self) -> None:
        action = ComputerAction(action=ActionType.KEY, key="ctrl+c")
        payload = action.to_input()
        assert payload["key"] == "ctrl+c"

    def test_to_input_scroll(self) -> None:
        action = ComputerAction(
            action=ActionType.SCROLL,
            coordinate=(50, 50),
            direction="up",
            amount=5,
        )
        payload = action.to_input()
        assert payload["direction"] == "up"
        assert payload["amount"] == 5

    def test_to_input_screenshot(self) -> None:
        action = ComputerAction(action=ActionType.SCREENSHOT)
        payload = action.to_input()
        assert payload["action"] == "screenshot"
        assert "coordinate" not in payload


class TestEvolutionTask:
    def test_defaults(self, tmp_path: Path) -> None:
        task = EvolutionTask(
            task_id="abc123",
            description="Test task",
            goal="Achieve X",
            screenshot_dir=tmp_path,
        )
        assert task.task_id == "abc123"
        assert task.max_iterations == 20
        assert task.success is None
        assert task.iterations_used == 0
        assert task.evidence_paths == []

    def test_custom_max_iterations(self, tmp_path: Path) -> None:
        task = EvolutionTask(
            task_id="xyz",
            description="desc",
            goal="goal",
            max_iterations=5,
            screenshot_dir=tmp_path,
        )
        assert task.max_iterations == 5


class TestAgentResult:
    def test_success_result(self) -> None:
        result = AgentResult(
            task_id="t1",
            stop_reason=StopReason.END_TURN,
            iterations=3,
            success=True,
            summary="All done",
        )
        assert result.success is True
        assert result.stop_reason == StopReason.END_TURN
        assert result.error is None

    def test_error_result(self) -> None:
        result = AgentResult(
            task_id="t2",
            stop_reason=StopReason.ERROR,
            iterations=1,
            success=False,
            summary="",
            error="network error",
        )
        assert result.success is False
        assert result.error == "network error"


class TestLoopState:
    def test_initial_state(self) -> None:
        state = LoopState()
        assert state.messages == []
        assert state.iteration == 0
        assert state.screenshots == []
        assert state.tool_results == []
        assert state.last_tool_use_id is None

    def test_message_append(self) -> None:
        state = LoopState()
        state.messages.append({"role": "user", "content": "hello"})
        assert len(state.messages) == 1


class TestActionTypeEnum:
    def test_all_values_unique(self) -> None:
        values = [a.value for a in ActionType]
        assert len(values) == len(set(values))

    def test_click_value(self) -> None:
        assert ActionType.CLICK.value == "left_click"

    def test_screenshot_value(self) -> None:
        assert ActionType.SCREENSHOT.value == "screenshot"


class TestStopReasonEnum:
    def test_all_values_unique(self) -> None:
        values = [s.value for s in StopReason]
        assert len(values) == len(set(values))

    def test_end_turn(self) -> None:
        assert StopReason.END_TURN.value == "end_turn"
