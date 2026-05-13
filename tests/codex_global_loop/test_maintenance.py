from unittest.mock import patch

import pytest

from cidls.codex_global_loop.maintenance import CIDLSSyncOrchestrator
from cidls.codex_global_loop.models import KanbanTicketUpdate


class Completed:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_pre_prompt_cycle_succeeds_without_installer():
    orchestrator = CIDLSSyncOrchestrator(repo_root=".")
    with patch.object(
        orchestrator,
        "_run_command",
        side_effect=[Completed(0, stdout='{"ok": true}')],
    ) as mock_run:
        result = orchestrator.run_pre_prompt_cycle()

    assert result.ok is True
    assert result.attempted_installer is False
    assert mock_run.call_count == 1


def test_pre_prompt_cycle_retries_after_installer_once():
    orchestrator = CIDLSSyncOrchestrator(repo_root=".")
    with patch.object(
        orchestrator,
        "_run_command",
        side_effect=[
            Completed(1, stderr="runtime is not initialized"),
            Completed(0, stdout="installer ok"),
            Completed(0, stdout='{"ok": true}'),
        ],
    ) as mock_run:
        result = orchestrator.run_pre_prompt_cycle()

    assert result.ok is True
    assert result.attempted_installer is True
    assert result.installer_returncode == 0
    assert mock_run.call_count == 3


def test_sync_agents_policy_parses_json():
    orchestrator = CIDLSSyncOrchestrator(repo_root=".")
    with patch.object(
        orchestrator,
        "_run_command",
        return_value=Completed(0, stdout='{"ok": true, "action": "unchanged"}'),
    ):
        result = orchestrator.sync_agents_policy()

    assert result["ok"] is True
    assert result["action"] == "unchanged"


def test_upsert_kanban_ticket_requires_ticket_update():
    orchestrator = CIDLSSyncOrchestrator(repo_root=".")
    with pytest.raises(ValueError):
        orchestrator.upsert_kanban_ticket({})


def test_run_full_loop_includes_optional_devrag_and_ticket_updates():
    orchestrator = CIDLSSyncOrchestrator(repo_root=".")
    ticket_update = KanbanTicketUpdate(
        title="Track OCR wiring audit",
        copy="Keep the Codex wiring audit and OCR pipeline aligned.",
        asis="Audit output did not include skill and global AGENTS checks.",
        tobe="Loop result includes audit, devrag, and kanban updates.",
        evidence="Added loop coverage in a unit test.",
        trace=["CIDLS", "OCR"],
    )

    with patch.object(orchestrator, "run_pre_prompt_cycle", return_value=type("HookResult", (), {"to_dict": lambda self: {"ok": True}})()):
        with patch.object(orchestrator, "sync_agents_policy", return_value={"ok": True, "action": "unchanged"}):
            with patch.object(orchestrator, "audit_global_wiring", return_value=type("AuditResult", (), {"to_dict": lambda self: {"issues": []}})()):
                with patch.object(orchestrator, "search_devrag", return_value={"results": [{"document": "docs/ocr_pipeline_requirements.md"}]}):
                    with patch.object(orchestrator, "upsert_kanban_ticket", return_value={"ticket_id": "CIDLS-999", "action": "created"}):
                        result = orchestrator.run_full_loop(
                            devrag_query="Snipping Tool OCR",
                            devrag_top_k=3,
                            ticket_update=ticket_update,
                        )

    assert result["pre_prompt_cycle"]["ok"] is True
    assert result["sync_agents_policy"]["action"] == "unchanged"
    assert result["audit_global_wiring"]["issues"] == []
    assert result["devrag_search"]["results"][0]["document"] == "docs/ocr_pipeline_requirements.md"
    assert result["kanban_update"]["ticket_id"] == "CIDLS-999"
