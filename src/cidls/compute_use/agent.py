"""
compute_use.agent - ComputeUse agentic loop for CIDLS autonomous evolution.

Implements the Anthropic Computer Use API agentic loop pattern:
  1. Send task + screenshot to model.
  2. Model returns text OR tool_use(computer_20251124).
  3. If tool_use: execute action on desktop, capture screenshot, feed back.
  4. Repeat until stop_reason == "end_turn" or iteration limit reached.

Safety boundaries (CU_GUARD):
  - Screenshots and action logs are persisted as evidence.
  - Destructive operations require human_gate=True callback.
  - No secrets are typed into the screen.

Dependencies (optional):
  anthropic  - pip-free install: uv add anthropic
  mss        - already in pyproject.toml
  Pillow     - already in pyproject.toml
  pyautogui  - already in pyproject.toml
"""

import base64
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path

from .models import (
    ActionType,
    AgentResult,
    ComputerAction,
    EvolutionTask,
    LoopState,
    StopReason,
)

logger = logging.getLogger(__name__)

# --- optional imports with availability check ---

def _check_anthropic() -> bool:
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False


def _check_mss() -> bool:
    try:
        import mss  # noqa: F401
        return True
    except ImportError:
        return False


ANTHROPIC_AVAILABLE = _check_anthropic()
MSS_AVAILABLE = _check_mss()

# Computer-use display defaults (match the model's coordinate space)
DEFAULT_DISPLAY_WIDTH = 1920
DEFAULT_DISPLAY_HEIGHT = 1080
DEFAULT_MODEL = "claude-opus-4-5"
CU_BETA = "computer-use-2025-11-24"
CU_TOOL_TYPE = "computer_20251124"


class ComputeUseUnavailableError(RuntimeError):
    """Raised when the anthropic package is not installed."""


class ComputeUseAgent:
    """
    CIDLS ComputeUse agent that drives desktop GUI autonomously.

    Usage:
        agent = ComputeUseAgent(api_key="<ANTHROPIC_API_KEY>", task_description="...")
        result = agent.run(task)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        display_width: int = DEFAULT_DISPLAY_WIDTH,
        display_height: int = DEFAULT_DISPLAY_HEIGHT,
        screenshot_dir: Path | str = Path("reports/compute_use"),
        human_gate: "HumanGateCallable | None" = None,
        dry_run: bool = False,
    ) -> None:
        """
        Initialise the ComputeUse agent.

        Args:
            api_key:        Anthropic API key (reads ANTHROPIC_API_KEY env if None).
            model:          Claude model to use (must support computer-use beta).
            display_width:  Logical screen width the model coordinates map to.
            display_height: Logical screen height the model coordinates map to.
            screenshot_dir: Directory to persist PNG evidence.
            human_gate:     Optional callable(action) -> bool for high-risk ops.
            dry_run:        If True, take screenshots but do NOT execute actions.
        """
        if not ANTHROPIC_AVAILABLE:
            raise ComputeUseUnavailableError(
                "anthropic package not installed. Run: uv add anthropic"
            )
        import anthropic as _ant  # deferred - only if available

        self._client = _ant.Anthropic(api_key=api_key)
        self._model = model
        self._display_width = display_width
        self._display_height = display_height
        self._screenshot_dir = Path(screenshot_dir)
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)
        self._human_gate = human_gate
        self._dry_run = dry_run

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, task: EvolutionTask) -> AgentResult:
        """Execute the agentic loop for the given EvolutionTask."""
        started_at = datetime.now()
        logger.info("[PROCESS_START] ComputeUseAgent task_id=%s desc=%s",
                    task.task_id, task.description[:80])

        state = LoopState()
        state.messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": self._build_system_prompt(task),
                    }
                ],
            }
        ]

        stop_reason = StopReason.MAX_ITERATIONS
        final_message = ""
        error_msg: str | None = None

        try:
            for iteration in range(1, task.max_iterations + 1):
                state.iteration = iteration
                logger.info("[STEP] iteration=%d/%d", iteration, task.max_iterations)

                # capture current screen state
                screenshot_b64 = self._capture_screenshot(task, iteration)
                state.screenshots.append(screenshot_b64)

                # append screenshot to current user turn
                self._inject_screenshot(state, screenshot_b64)

                # call the model
                response = self._call_model(state)
                stop_reason_raw = response.stop_reason

                # extract content blocks
                assistant_content = response.content
                state.messages.append({"role": "assistant", "content": assistant_content})

                if stop_reason_raw == "end_turn":
                    stop_reason = StopReason.END_TURN
                    final_message = self._extract_text(assistant_content)
                    logger.info("[SUCC] end_turn iteration=%d", iteration)
                    break

                if stop_reason_raw == "tool_use":
                    # handle computer tool use blocks
                    tool_results = self._handle_tool_use(assistant_content, task, state)
                    state.messages.append({"role": "user", "content": tool_results})
                    stop_reason = StopReason.TOOL_USE  # will continue
                    continue

                # unexpected stop reason
                logger.warning("[WARN] unexpected stop_reason=%s", stop_reason_raw)
                stop_reason = StopReason.STOP_SEQUENCE
                break

        except Exception as exc:
            logger.error("[ERR] agentic loop error: %s", exc, exc_info=True)
            error_msg = str(exc)
            stop_reason = StopReason.ERROR

        task.iterations_used = state.iteration
        task.completed_at = datetime.now()
        task.success = stop_reason == StopReason.END_TURN

        result = AgentResult(
            task_id=task.task_id,
            stop_reason=stop_reason,
            iterations=state.iteration,
            success=task.success,
            summary=final_message[:500] if final_message else "",
            evidence_paths=task.evidence_paths,
            final_message=final_message,
            error=error_msg,
            started_at=started_at,
            finished_at=datetime.now(),
        )
        logger.info("[PROCESS_END] task_id=%s success=%s stop=%s",
                    task.task_id, result.success, result.stop_reason)
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_system_prompt(self, task: EvolutionTask) -> str:
        return (
            f"CIDLS ComputeUse autonomous evolution task.\n\n"
            f"Task ID : {task.task_id}\n"
            f"Goal    : {task.goal}\n\n"
            f"Instructions:\n{task.description}\n\n"
            "Rules:\n"
            "- Verify each action succeeded before proceeding.\n"
            "- Capture evidence screenshots after key milestones.\n"
            "- If an operation looks destructive, report it rather than executing.\n"
            "- When the goal is fully achieved, respond with a clear summary and stop.\n"
        )

    def _capture_screenshot(self, task: EvolutionTask, iteration: int) -> str:
        """Capture screen as PNG and return base64-encoded bytes."""
        if not MSS_AVAILABLE:
            logger.warning("[WARN] mss unavailable - returning blank 1x1 PNG")
            return _blank_png_b64()

        import mss
        import mss.tools

        with mss.mss() as sct:
            monitor = sct.monitors[0]  # full virtual screen
            sct_img = sct.grab(monitor)
            from PIL import Image
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            # scale to model display dimensions
            img = img.resize((self._display_width, self._display_height))

            png_path = (
                self._screenshot_dir
                / f"{task.task_id}_iter{iteration:03d}.png"
            )
            img.save(png_path, "PNG")
            task.evidence_paths.append(str(png_path))

            import io
            buf = io.BytesIO()
            img.save(buf, "PNG")
            return base64.standard_b64encode(buf.getvalue()).decode()

    def _inject_screenshot(self, state: LoopState, screenshot_b64: str) -> None:
        """Append the latest screenshot into the last user message."""
        if not state.messages or state.messages[-1]["role"] != "user":
            state.messages.append({"role": "user", "content": []})

        last = state.messages[-1]
        if isinstance(last["content"], list):
            last["content"].append(
                {
                    "type": "tool_result",
                    "tool_use_id": state.last_tool_use_id or "init",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": screenshot_b64,
                            },
                        }
                    ],
                }
            )

    def _call_model(self, state: LoopState):  # -> anthropic.types.Message
        return self._client.beta.messages.create(
            model=self._model,
            max_tokens=4096,
            tools=[
                {
                    "type": CU_TOOL_TYPE,
                    "name": "computer",
                    "display_width_px": self._display_width,
                    "display_height_px": self._display_height,
                    "display_number": 1,
                }
            ],
            messages=state.messages,
            betas=[CU_BETA],
        )

    def _handle_tool_use(
        self,
        content_blocks: list,
        task: EvolutionTask,
        state: LoopState,
    ) -> list[dict]:
        """Execute computer actions and return tool_result blocks."""
        tool_results: list[dict] = []

        for block in content_blocks:
            if not hasattr(block, "type") or block.type != "tool_use":
                continue
            if block.name != "computer":
                logger.warning("[WARN] unknown tool: %s", block.name)
                continue

            state.last_tool_use_id = block.id
            input_data = block.input
            action_name = input_data.get("action", "")

            logger.info("[STEP] tool_use id=%s action=%s", block.id, action_name)

            if self._dry_run:
                logger.info("[PROG] dry_run=True - skipping action execution")
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "dry_run: action skipped",
                    }
                )
                continue

            # safety gate for destructive operations
            if self._human_gate and not self._human_gate(input_data):
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "blocked by human gate",
                        "is_error": True,
                    }
                )
                continue

            # execute the action
            try:
                self._execute_action(input_data, task, state)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"action '{action_name}' executed",
                    }
                )
            except Exception as exc:
                logger.error("[ERR] action execution failed: %s", exc)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"action failed: {exc}",
                        "is_error": True,
                    }
                )

        return tool_results

    def _execute_action(
        self,
        input_data: dict,
        task: EvolutionTask,
        state: LoopState,
    ) -> None:
        """Execute a single computer action via pyautogui."""
        import pyautogui  # noqa: import inside method - optional dep

        action = input_data.get("action", "")
        coord = input_data.get("coordinate")  # [x, y]
        text = input_data.get("text", "")
        key = input_data.get("key", "")
        direction = input_data.get("direction", "down")
        amount = input_data.get("amount", 3)

        # scale model coords → actual screen coords
        if coord:
            sx = int(coord[0] * pyautogui.size().width / self._display_width)
            sy = int(coord[1] * pyautogui.size().height / self._display_height)
        else:
            sx, sy = None, None

        if action == ActionType.SCREENSHOT.value:
            pass  # next iteration will capture automatically
        elif action == ActionType.CLICK.value and sx is not None:
            pyautogui.click(sx, sy)
        elif action == ActionType.DOUBLE_CLICK.value and sx is not None:
            pyautogui.doubleClick(sx, sy)
        elif action == ActionType.RIGHT_CLICK.value and sx is not None:
            pyautogui.rightClick(sx, sy)
        elif action == ActionType.MOVE.value and sx is not None:
            pyautogui.moveTo(sx, sy)
        elif action == ActionType.TYPE.value:
            pyautogui.write(text, interval=0.02)
        elif action == ActionType.KEY.value:
            pyautogui.hotkey(*key.split("+"))
        elif action == ActionType.SCROLL.value and sx is not None:
            clicks = amount if direction == "up" else -amount
            pyautogui.scroll(clicks, x=sx, y=sy)
        elif action == ActionType.DRAG.value:
            start = input_data.get("start_coordinate", coord)
            if start and coord:
                ssx = int(start[0] * pyautogui.size().width / self._display_width)
                ssy = int(start[1] * pyautogui.size().height / self._display_height)
                pyautogui.dragTo(sx, sy, button="left", duration=0.3,
                                 _pause=False)
                pyautogui.moveTo(ssx, ssy)
                pyautogui.mouseDown(button="left")
                pyautogui.moveTo(sx, sy, duration=0.3)
                pyautogui.mouseUp(button="left")
        else:
            raise ValueError(f"Unknown or unsupported action: {action}")

        time.sleep(0.5)  # allow GUI to settle

    @staticmethod
    def _extract_text(content_blocks: list) -> str:
        """Extract plain text from assistant content blocks."""
        parts: list[str] = []
        for block in content_blocks:
            if hasattr(block, "type") and block.type == "text":
                parts.append(block.text)
        return "\n".join(parts)


# ------------------------------------------------------------------
# Utility
# ------------------------------------------------------------------

def _blank_png_b64() -> str:
    """Return a 1x1 transparent PNG as base64 (fallback when mss unavailable)."""
    data = bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de"
        "0000000c4944415408d763f8cfc000000002000177e1e1480000000049454e44ae426082"
    )
    return base64.standard_b64encode(data).decode()


def make_evolution_task(
    description: str,
    goal: str,
    max_iterations: int = 20,
    screenshot_dir: Path | str = Path("reports/compute_use"),
) -> EvolutionTask:
    """Convenience factory for EvolutionTask."""
    return EvolutionTask(
        task_id=uuid.uuid4().hex,
        description=description,
        goal=goal,
        max_iterations=max_iterations,
        screenshot_dir=Path(screenshot_dir),
    )
