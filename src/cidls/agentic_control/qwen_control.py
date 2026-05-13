"""Qwen programmer control gate for CIDLS.

This module does not call Qwen models directly. It detects whether the local
Qwen CLI is usable, verifies that a credential source exists, and builds a
Codex-controlled programmer brief so external model output cannot bypass TDD,
DISTSEC, review, or rollback requirements.
"""

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import shutil
import subprocess


QWEN_CREDENTIAL_ENV_NAMES = (
    "QWEN_API_KEY",
    "DASHSCOPE_API_KEY",
    "OPENROUTER_API_KEY",
)


@dataclass
class CommandResult:
    """Small subprocess result used to keep tests independent from the shell."""

    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass
class QwenEnvironmentStatus:
    """Detected Qwen CLI and credential readiness."""

    cli_available: bool
    cli_command: str = ""
    cli_version: str = ""
    credential_available: bool = False
    credential_sources: list[str] = field(default_factory=list)
    powershell_script_blocked: bool = False
    invocation_ready: bool = False
    blockers: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return JSON-serialisable status."""
        return {
            "cli_available": self.cli_available,
            "cli_command": self.cli_command,
            "cli_version": self.cli_version,
            "credential_available": self.credential_available,
            "credential_sources": self.credential_sources,
            "powershell_script_blocked": self.powershell_script_blocked,
            "invocation_ready": self.invocation_ready,
            "blockers": self.blockers,
            "next_actions": self.next_actions,
        }

    def to_json(self) -> str:
        """Return deterministic JSON text."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class QwenUnavailableError(RuntimeError):
    """Raised when Qwen should not be invoked."""


def _default_command_runner(command: list[str], timeout: int) -> CommandResult:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    return CommandResult(
        completed.returncode,
        completed.stdout or "",
        completed.stderr or "",
    )


def _default_path_lookup(name: str) -> str | None:
    return shutil.which(name)


def _select_qwen_command(path_lookup) -> str:
    for candidate in ("qwen.cmd", "qwen", "qwen.ps1"):
        path = path_lookup(candidate)
        if path:
            return candidate
    return ""


def _read_credentials(env: dict) -> list[str]:
    found = []
    for name in QWEN_CREDENTIAL_ENV_NAMES:
        value = env.get(name)
        if value and str(value).strip():
            found.append(name)
    return found


def _append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _probe_qwen_version(command_runner, timeout: int) -> tuple[bool, str]:
    result = command_runner(["cmd", "/c", "qwen", "--version"], timeout)
    if result.returncode != 0:
        return False, ""
    return True, (result.stdout or "").strip().splitlines()[0].strip()


def _probe_powershell_block(command_runner, timeout: int) -> bool:
    result = command_runner(
        ["powershell", "-NoProfile", "-Command", "qwen --version"],
        timeout,
    )
    combined = f"{result.stdout}\n{result.stderr}".lower()
    return (
        result.returncode != 0
        and "cannot be loaded" in combined
        and "running scripts is disabled" in combined
    )


def detect_qwen_environment(
    env: dict | None = None,
    command_runner=None,
    path_lookup=None,
    timeout: int = 10,
    probe_powershell: bool = True,
) -> QwenEnvironmentStatus:
    """Detect whether Qwen can be safely used as a CIDLS Programmer."""
    effective_env = dict(os.environ if env is None else env)
    runner = command_runner or _default_command_runner
    lookup = path_lookup or _default_path_lookup

    cli_command = _select_qwen_command(lookup)
    cli_exists = bool(cli_command)
    cli_available = False
    cli_version = ""
    blockers: list[str] = []
    next_actions: list[str] = []

    if cli_exists:
        cli_available, cli_version = _probe_qwen_version(runner, timeout)
    if not cli_available:
        _append_unique(blockers, "qwen_cli_missing")
        next_actions.append("Install or repair the qwen CLI, then confirm 'cmd /c qwen --version'.")

    credential_sources = _read_credentials(effective_env)
    credential_available = bool(credential_sources)
    if not credential_available:
        _append_unique(blockers, "qwen_credentials_missing")
        next_actions.append(
            "Set QWEN_API_KEY, DASHSCOPE_API_KEY, or OPENROUTER_API_KEY outside chat."
        )

    powershell_blocked = False
    if probe_powershell and cli_exists:
        powershell_blocked = _probe_powershell_block(runner, timeout)
        if powershell_blocked:
            _append_unique(blockers, "powershell_execution_policy_blocks_qwen_ps1")
            next_actions.append(
                "Use 'cmd /c qwen ...' from automation unless PowerShell policy is intentionally changed."
            )

    invocation_ready = cli_available and credential_available
    if invocation_ready:
        next_actions.append("Qwen may be used only as Programmer; Codex keeps TDD, review, merge, and rollback control.")

    return QwenEnvironmentStatus(
        cli_available=cli_available,
        cli_command=cli_command,
        cli_version=cli_version,
        credential_available=credential_available,
        credential_sources=credential_sources,
        powershell_script_blocked=powershell_blocked,
        invocation_ready=invocation_ready,
        blockers=blockers,
        next_actions=next_actions,
    )


def ensure_qwen_ready(status: QwenEnvironmentStatus | None = None) -> QwenEnvironmentStatus:
    """Fail fast if Qwen should not be invoked."""
    effective_status = status or detect_qwen_environment()
    if effective_status.invocation_ready:
        return effective_status

    blockers = ", ".join(effective_status.blockers)
    actions = " | ".join(effective_status.next_actions)
    raise QwenUnavailableError(
        f"Qwen invocation blocked: {blockers}. Next actions: {actions}"
    )


def build_qwen_programmer_brief(
    title: str,
    goal: str,
    files: list[str] | None = None,
    constraints: list[str] | None = None,
    test_command: str | None = None,
) -> str:
    """Build a Codex-controlled implementation brief for Qwen."""
    file_lines = _format_list(files or [], "No file scope provided; ask Codex for a bounded write set.")
    constraint_lines = _format_list(
        constraints or [],
        "Follow AGENTS.md, DISTSEC, TDD, horizontal sync, and no fallback data.",
    )
    test_line = test_command or "Codex must provide the exact pytest command before implementation."

    return (
        "# Qwen3.6ThinkingMax Programmer Brief\n\n"
        "Role contract:\n"
        "- Qwen3.6ThinkingMax is Programmer only.\n"
        "- Codex Director owns requirements, file scope, tests, review, merge, and rollback.\n"
        "- Claude may be used as Converger after Codex review.\n"
        "- Do not merge your own output or claim completion without test evidence.\n\n"
        f"Task title:\n{title}\n\n"
        f"Goal:\n{goal}\n\n"
        "Writable/readable scope:\n"
        f"{file_lines}\n\n"
        "Constraints:\n"
        f"{constraint_lines}\n\n"
        "Required output from Programmer:\n"
        "- Minimal patch proposal.\n"
        "- Test changes and expected Red/Green result.\n"
        "- Impact range and horizontal-sync candidates.\n"
        "- Security and secret-boundary notes.\n"
        "- rollback plan.\n\n"
        "Verification command:\n"
        f"{test_line}\n"
    )


def _format_list(values: list[str], empty_message: str) -> str:
    if not values:
        return f"- {empty_message}"
    return "\n".join(f"- {Path(value).as_posix()}" for value in values)
