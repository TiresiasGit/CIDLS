"""Unit tests for compute_use.agent (no Anthropic API calls)."""

from pathlib import Path
from unittest.mock import MagicMock, patch, call
import base64

import pytest

from cidls.compute_use.agent import (
    ComputeUseAgent,
    ComputeUseUnavailableError,
    _blank_png_b64,
    make_evolution_task,
)
from cidls.compute_use.models import (
    ActionType,
    AgentResult,
    EvolutionTask,
    LoopState,
    StopReason,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_anthropic_module():
    """Return a mock anthropic module with Anthropic client class."""
    mock_module = MagicMock()
    mock_client = MagicMock()
    mock_module.Anthropic.return_value = mock_client
    return mock_module, mock_client


def _make_end_turn_response(text: str = "Task complete"):
    """Create a mock Anthropic response that ends the loop."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [block]
    return response


def _make_tool_use_response(action: str, coordinate: list | None = None):
    """Create a mock response with a computer tool_use block."""
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "computer"
    tool_block.id = "tool_abc123"
    tool_block.input = {"action": action}
    if coordinate is not None:
        tool_block.input["coordinate"] = coordinate

    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [tool_block]
    return response


# ---------------------------------------------------------------------------
# _blank_png_b64
# ---------------------------------------------------------------------------

class TestBlankPngB64:
    def test_returns_valid_base64(self) -> None:
        b64 = _blank_png_b64()
        decoded = base64.standard_b64decode(b64)
        # PNG magic bytes
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"


# ---------------------------------------------------------------------------
# make_evolution_task
# ---------------------------------------------------------------------------

class TestMakeEvolutionTask:
    def test_factory_sets_fields(self, tmp_path: Path) -> None:
        task = make_evolution_task(
            description="Do something",
            goal="Achieve X",
            max_iterations=5,
            screenshot_dir=tmp_path,
        )
        assert task.description == "Do something"
        assert task.goal == "Achieve X"
        assert task.max_iterations == 5
        assert task.screenshot_dir == tmp_path
        assert len(task.task_id) > 0

    def test_unique_task_ids(self, tmp_path: Path) -> None:
        t1 = make_evolution_task("a", "b", screenshot_dir=tmp_path)
        t2 = make_evolution_task("c", "d", screenshot_dir=tmp_path)
        assert t1.task_id != t2.task_id


# ---------------------------------------------------------------------------
# ComputeUseUnavailableError
# ---------------------------------------------------------------------------

class TestComputeUseUnavailableError:
    def test_raises_when_anthropic_missing(self, tmp_path: Path) -> None:
        with patch("cidls.compute_use.agent.ANTHROPIC_AVAILABLE", False):
            with pytest.raises(ComputeUseUnavailableError):
                ComputeUseAgent(api_key="dummy-api-key", screenshot_dir=tmp_path)


# ---------------------------------------------------------------------------
# ComputeUseAgent (mocked anthropic)
# ---------------------------------------------------------------------------

class TestComputeUseAgentInit:
    def test_init_with_mock_anthropic(self, tmp_path: Path) -> None:
        mock_mod, _mock_client = _mock_anthropic_module()
        with patch("cidls.compute_use.agent.ANTHROPIC_AVAILABLE", True), \
             patch.dict("sys.modules", {"anthropic": mock_mod}):
            agent = ComputeUseAgent(
                api_key="dummy-api-key",
                screenshot_dir=tmp_path,
                dry_run=True,
            )
            assert agent._dry_run is True
            assert agent._screenshot_dir == tmp_path


class TestComputeUseAgentRun:
    """Tests that run the agentic loop with the anthropic client fully mocked."""

    def _make_agent_with_client(
        self, tmp_path: Path, mock_client
    ) -> tuple["ComputeUseAgent", MagicMock, MagicMock]:
        """Return (agent, mock_module, patch_obj) – caller keeps patch active."""
        mock_mod, _ = _mock_anthropic_module()
        mock_mod.Anthropic.return_value = mock_client
        p_avail = patch("cidls.compute_use.agent.ANTHROPIC_AVAILABLE", True)
        p_mod = patch.dict("sys.modules", {"anthropic": mock_mod})
        p_avail.start()
        p_mod.start()
        agent = ComputeUseAgent(
            api_key="dummy-api-key",
            screenshot_dir=tmp_path,
            dry_run=True,
        )
        return agent, p_avail, p_mod

    def test_end_turn_immediately(self, tmp_path: Path) -> None:
        mock_client = MagicMock()
        mock_client.beta.messages.create.return_value = _make_end_turn_response("Done")

        agent, p1, p2 = self._make_agent_with_client(tmp_path, mock_client)
        task = make_evolution_task("desc", "goal", max_iterations=5, screenshot_dir=tmp_path)
        try:
            with patch("cidls.compute_use.agent.MSS_AVAILABLE", False):
                result = agent.run(task)
        finally:
            p1.stop(); p2.stop()

        assert result.success is True
        assert result.stop_reason == StopReason.END_TURN
        assert result.iterations == 1
        assert "Done" in result.final_message

    def test_max_iterations_reached(self, tmp_path: Path) -> None:
        mock_client = MagicMock()
        mock_client.beta.messages.create.return_value = _make_tool_use_response("screenshot")

        agent, p1, p2 = self._make_agent_with_client(tmp_path, mock_client)
        task = make_evolution_task("desc", "goal", max_iterations=3, screenshot_dir=tmp_path)
        try:
            with patch("cidls.compute_use.agent.MSS_AVAILABLE", False):
                result = agent.run(task)
        finally:
            p1.stop(); p2.stop()

        assert result.iterations == 3
        assert result.stop_reason == StopReason.TOOL_USE

    def test_error_propagation(self, tmp_path: Path) -> None:
        mock_client = MagicMock()
        mock_client.beta.messages.create.side_effect = RuntimeError("API down")

        agent, p1, p2 = self._make_agent_with_client(tmp_path, mock_client)
        task = make_evolution_task("desc", "goal", max_iterations=5, screenshot_dir=tmp_path)
        try:
            with patch("cidls.compute_use.agent.MSS_AVAILABLE", False):
                result = agent.run(task)
        finally:
            p1.stop(); p2.stop()

        assert result.success is False
        assert result.stop_reason == StopReason.ERROR
        assert "API down" in (result.error or "")

    def test_dry_run_skips_actions(self, tmp_path: Path) -> None:
        """In dry_run mode, tool_use actions are acknowledged but not executed."""
        mock_client = MagicMock()
        mock_client.beta.messages.create.side_effect = [
            _make_tool_use_response("left_click", [100, 200]),
            _make_end_turn_response("Finished"),
        ]

        agent, p1, p2 = self._make_agent_with_client(tmp_path, mock_client)
        task = make_evolution_task("desc", "goal", max_iterations=5, screenshot_dir=tmp_path)
        try:
            with patch("cidls.compute_use.agent.MSS_AVAILABLE", False):
                result = agent.run(task)
        finally:
            p1.stop(); p2.stop()

        assert result.success is True


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

class TestBuildSystemPrompt:
    def _make_agent(self, tmp_path: Path) -> "ComputeUseAgent":
        mock_mod, _mc = _mock_anthropic_module()
        with patch("cidls.compute_use.agent.ANTHROPIC_AVAILABLE", True), \
             patch.dict("sys.modules", {"anthropic": mock_mod}):
            return ComputeUseAgent(api_key="k", screenshot_dir=tmp_path)

    def test_contains_goal(self, tmp_path: Path) -> None:
        agent = self._make_agent(tmp_path)
        task = make_evolution_task(
            description="Run the CIDLS pipeline",
            goal="Achieve compound self-evolution",
            screenshot_dir=tmp_path,
        )
        prompt = agent._build_system_prompt(task)
        assert "Achieve compound self-evolution" in prompt
        assert task.task_id in prompt

    def test_contains_safety_rules(self, tmp_path: Path) -> None:
        agent = self._make_agent(tmp_path)
        task = make_evolution_task("d", "g", screenshot_dir=tmp_path)
        prompt = agent._build_system_prompt(task)
        assert "destructive" in prompt.lower() or "evidence" in prompt.lower()


class TestExtractText:
    def test_single_text_block(self) -> None:
        block = MagicMock()
        block.type = "text"
        block.text = "Hello"
        result = ComputeUseAgent._extract_text([block])
        assert result == "Hello"

    def test_multiple_text_blocks(self) -> None:
        b1 = MagicMock(); b1.type = "text"; b1.text = "Part A"
        b2 = MagicMock(); b2.type = "text"; b2.text = "Part B"
        result = ComputeUseAgent._extract_text([b1, b2])
        assert "Part A" in result
        assert "Part B" in result

    def test_non_text_block_ignored(self) -> None:
        tool = MagicMock(); tool.type = "tool_use"
        text = MagicMock(); text.type = "text"; text.text = "Only me"
        result = ComputeUseAgent._extract_text([tool, text])
        assert result == "Only me"

    def test_empty_content(self) -> None:
        result = ComputeUseAgent._extract_text([])
        assert result == ""
