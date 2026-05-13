import importlib.util
import sys
from pathlib import Path


def load_sync_module():
    repo = Path(__file__).resolve().parents[1]
    module_path = repo / "scripts" / "sync_agents_cidls_policy.py"
    spec = importlib.util.spec_from_file_location("sync_agents_cidls_policy", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_html_ticket_source_with_all_done_tickets_does_not_parse_command_text(tmp_path):
    module = load_sync_module()
    board = tmp_path / "project_kanban.html"
    board.write_text(
        """
        <html><body>
        <script>
        const tickets = [
          { id: "CIDLS-1", status: "done", priority: "high", title: "Closed task" }
        ];
        </script>
        - `python scripts\\audit_distribution_security.py dist --report logs\\distribution_security_audit.json` runs.
        </body></html>
        """,
        encoding="utf-8",
    )

    assert module.extract_open_tasks(board) == []
