from pathlib import Path

from cidls.codex_global_loop.kanban_ticket_store import ProjectKanbanTicketStore
from cidls.codex_global_loop.models import KanbanTicketUpdate


BOARD_TEMPLATE = """<!DOCTYPE html>
<script>
const tickets = [
  {
    id: "CIDLS-101",
    status: "done",
    priority: "medium",
    title: "Existing ticket",
    copy: "Existing copy",
    stageId: "fusion",
    asis: "old as-is",
    tobe: "old to-be",
    evidence: "old evidence",
    trace: ["A", "B"]
  }
];
</script>
"""


def test_upsert_creates_new_ticket():
    store = ProjectKanbanTicketStore(board_path="project_kanban.html")
    captured = {"text": BOARD_TEMPLATE}
    store.read_text = lambda: captured["text"]
    store.write_text = lambda value: captured.__setitem__("text", value)

    ticket_id, action = store.upsert(
        KanbanTicketUpdate(
            title="New OCR ticket",
            copy="Add OCR evidence flow",
            asis="No OCR ticket exists.",
            tobe="OCR work is tracked.",
            evidence="Created during test.",
            trace=["OCR", "Board"],
        )
    )

    text = captured["text"]
    assert action == "created"
    assert ticket_id == "CIDLS-102"
    assert "New OCR ticket" in text


def test_upsert_updates_existing_ticket():
    store = ProjectKanbanTicketStore(board_path="project_kanban.html")
    captured = {"text": BOARD_TEMPLATE}
    store.read_text = lambda: captured["text"]
    store.write_text = lambda value: captured.__setitem__("text", value)

    ticket_id, action = store.upsert(
        KanbanTicketUpdate(
            ticket_id="CIDLS-101",
            status="review",
            priority="high",
            title="Existing ticket",
            copy="Updated copy",
            asis="updated as-is",
            tobe="updated to-be",
            evidence="updated evidence",
            trace=["Updated"],
        )
    )

    text = captured["text"]
    assert action == "updated"
    assert ticket_id == "CIDLS-101"
    assert '"status": "review"' not in text
    assert 'status: "review"' in text
    assert "Updated copy" in text
