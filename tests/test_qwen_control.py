import json
import os

import pytest

from cidls.agentic_control.qwen_control import (
    CommandResult,
    QwenUnavailableError,
    build_qwen_programmer_brief,
    detect_qwen_environment,
    ensure_qwen_ready,
)
from cidls.agentic_control.cli import main as qwen_cli_main


def test_detect_qwen_blocks_without_credentials():
    calls = []

    def fake_runner(command, timeout):
        calls.append(command)
        if command[:2] == ["cmd", "/c"]:
            return CommandResult(0, "0.15.10\n", "")
        return CommandResult(
            1,
            "",
            "qwen.ps1 cannot be loaded because running scripts is disabled",
        )

    status = detect_qwen_environment(
        env={},
        command_runner=fake_runner,
        path_lookup=lambda name: f"C:/npm/{name}" if name in {"qwen.cmd", "qwen.ps1"} else None,
    )

    assert status.cli_available is True
    assert status.cli_version == "0.15.10"
    assert status.credential_available is False
    assert status.invocation_ready is False
    assert "qwen_credentials_missing" in status.blockers
    assert "powershell_execution_policy_blocks_qwen_ps1" in status.blockers
    assert calls[0] == ["cmd", "/c", "qwen", "--version"]


def test_detect_qwen_ready_when_cli_and_credential_exist():
    def fake_runner(command, timeout):
        return CommandResult(0, "0.15.10", "")

    status = detect_qwen_environment(
        env={"DASHSCOPE_API_KEY": "secret-value"},
        command_runner=fake_runner,
        path_lookup=lambda name: f"C:/npm/{name}" if name == "qwen.cmd" else None,
        probe_powershell=False,
    )

    assert status.invocation_ready is True
    assert status.credential_sources == ["DASHSCOPE_API_KEY"]
    assert status.blockers == []


def test_ensure_qwen_ready_raises_with_actionable_blockers():
    status = detect_qwen_environment(
        env={},
        command_runner=lambda command, timeout: CommandResult(1, "", "not found"),
        path_lookup=lambda name: None,
        probe_powershell=False,
    )

    with pytest.raises(QwenUnavailableError) as exc:
        ensure_qwen_ready(status)

    message = str(exc.value)
    assert "qwen_cli_missing" in message
    assert "qwen_credentials_missing" in message


def test_build_qwen_programmer_brief_encodes_codex_control_contract():
    brief = build_qwen_programmer_brief(
        title="Implement billing gate",
        goal="Reject client-side plan spoofing before checkout.",
        files=["src/billing.py", "tests/test_billing.py"],
        constraints=["No operator secret in frontend", "TDD first"],
        test_command="uv run python -m pytest tests/test_billing.py -q",
    )

    assert "Qwen3.6ThinkingMax" in brief
    assert "Programmer" in brief
    assert "Codex Director" in brief
    assert "Do not merge your own output" in brief
    assert "src/billing.py" in brief
    assert "uv run python -m pytest tests/test_billing.py -q" in brief
    assert "rollback" in brief.lower()


def test_cli_status_json_reports_not_ready_without_secret(capsys):
    exit_code = qwen_cli_main(
        ["status", "--json", "--no-powershell-probe"],
        env={},
        command_runner=lambda command, timeout: CommandResult(0, "0.15.10", ""),
        path_lookup=lambda name: "C:/npm/qwen.cmd" if name == "qwen.cmd" else None,
    )

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert exit_code == 0
    assert payload["invocation_ready"] is False
    assert payload["cli_version"] == "0.15.10"
    assert payload["credential_available"] is False


def test_cli_status_strict_fails_when_not_ready():
    exit_code = qwen_cli_main(
        ["status", "--strict", "--no-powershell-probe"],
        env=os.environ.copy() | {"QWEN_API_KEY": ""},
        command_runner=lambda command, timeout: CommandResult(1, "", "not found"),
        path_lookup=lambda name: None,
    )

    assert exit_code == 2


def test_cli_brief_outputs_programmer_contract(capsys):
    exit_code = qwen_cli_main(
        [
            "brief",
            "--title",
            "Implement report export",
            "--goal",
            "Create commercial Excel export.",
            "--file",
            "src/report.py",
            "--constraint",
            "A5M2 table detail",
            "--test-command",
            "uv run python -m pytest tests/test_report.py -q",
        ]
    )

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Qwen3.6ThinkingMax" in out
    assert "Codex Director" in out
    assert "src/report.py" in out
