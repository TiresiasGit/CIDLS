import json
import os
import subprocess
from pathlib import Path

from .devrag_bridge import DevragBridge
from .kanban_ticket_store import ProjectKanbanTicketStore
from .models import KanbanTicketUpdate
from .models import GlobalWiringAuditResult, HookExecutionResult


class CIDLSSyncOrchestrator:
    def __init__(self, repo_root=".", codex_home="", board_path="project_kanban.html"):
        userprofile = Path(os.environ.get("USERPROFILE", "").strip()) if os.environ.get("USERPROFILE", "").strip() else Path.home()
        self.repo_root = Path(repo_root).resolve()
        self.codex_home = Path(codex_home) if codex_home else userprofile / ".codex"
        self.board_path = Path(board_path)

    def run_pre_prompt_cycle(self):
        hook_path = self.repo_root / "pre_prompt_cycle.bat"
        installer_path = self.repo_root / "installer.bat"
        first = self._run_command(["cmd", "/c", str(hook_path)])
        if first.returncode == 0:
            return HookExecutionResult(
                ok=True,
                command="cmd /c pre_prompt_cycle.bat",
                returncode=first.returncode,
                stdout=first.stdout,
                stderr=first.stderr,
            )

        if not self._needs_runtime_install(first.stdout + "\n" + first.stderr):
            return HookExecutionResult(
                ok=False,
                command="cmd /c pre_prompt_cycle.bat",
                returncode=first.returncode,
                stdout=first.stdout,
                stderr=first.stderr,
            )

        installer = self._run_command(["cmd", "/c", str(installer_path)])
        second = self._run_command(["cmd", "/c", str(hook_path)])
        return HookExecutionResult(
            ok=second.returncode == 0,
            command="cmd /c pre_prompt_cycle.bat",
            returncode=second.returncode,
            stdout=second.stdout,
            stderr=second.stderr,
            attempted_installer=True,
            installer_command="cmd /c installer.bat",
            installer_returncode=installer.returncode,
        )

    def sync_agents_policy(self):
        completed = self._run_command(["python", "scripts\\sync_agents_cidls_policy.py"])
        return self._load_json_result(completed)

    def audit_global_wiring(self):
        completed = self._run_command(["python", "scripts\\audit_global_cidls_wiring.py"])
        return GlobalWiringAuditResult(self._load_json_result(completed))

    def search_devrag(self, query, top_k=5, directory="", file_pattern=""):
        bridge = DevragBridge(codex_home=self.codex_home)
        return bridge.search(
            query=query,
            top_k=top_k,
            directory=directory,
            file_pattern=file_pattern,
        ).to_dict()

    def upsert_kanban_ticket(self, ticket_update):
        if not isinstance(ticket_update, KanbanTicketUpdate):
            raise ValueError("ticket_update must be KanbanTicketUpdate")
        store = ProjectKanbanTicketStore(board_path=self.repo_root / self.board_path)
        ticket_id, action = store.upsert(ticket_update)
        return {
            "ticket_id": ticket_id,
            "action": action,
        }

    def run_full_loop(self, devrag_query="", devrag_top_k=5, devrag_directory="", devrag_file_pattern="", ticket_update=None):
        result = {
            "pre_prompt_cycle": self.run_pre_prompt_cycle().to_dict(),
            "sync_agents_policy": self.sync_agents_policy(),
            "audit_global_wiring": self.audit_global_wiring().to_dict(),
        }
        if devrag_query:
            result["devrag_search"] = self.search_devrag(
                query=devrag_query,
                top_k=devrag_top_k,
                directory=devrag_directory,
                file_pattern=devrag_file_pattern,
            )
        if ticket_update:
            result["kanban_update"] = self.upsert_kanban_ticket(ticket_update)
        return result

    def _run_command(self, command):
        return subprocess.run(
            command,
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

    def _load_json_result(self, completed):
        stdout = (completed.stdout or "").strip()
        if stdout:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                return {
                    "ok": False,
                    "returncode": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                }
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    def _needs_runtime_install(self, output):
        lowered = str(output or "").lower()
        signals = [
            "runtime is not initialized",
            "not initialized",
            "installer.bat",
            "missing runtime",
            "cidls runtime",
        ]
        return any(signal in lowered for signal in signals)
