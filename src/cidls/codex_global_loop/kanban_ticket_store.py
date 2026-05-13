import json
import re
from pathlib import Path

from .models import KanbanTicketUpdate


class ProjectKanbanTicketStore:
    ARRAY_PATTERN = re.compile(
        r"const\s+tickets\s*=\s*\[(?P<body>.*?)\]\s*;",
        flags=re.S,
    )

    def __init__(self, board_path="project_kanban.html"):
        self.board_path = Path(board_path)

    def read_text(self):
        return self.board_path.read_text(encoding="utf-8")

    def write_text(self, text):
        self.board_path.write_text(text, encoding="utf-8", newline="\n")

    def list_ticket_dicts(self):
        match = self.ARRAY_PATTERN.search(self.read_text())
        if not match:
            raise ValueError("tickets array not found in project_kanban.html")
        return self._parse_ticket_objects(match.group("body"))

    def next_ticket_id(self):
        max_number = 100
        for ticket in self.list_ticket_dicts():
            raw_value = str(ticket.get("id", ""))
            if not raw_value.startswith("CIDLS-"):
                continue
            suffix = raw_value.split("-", 1)[1]
            if suffix.isdigit():
                max_number = max(max_number, int(suffix))
        return f"CIDLS-{max_number + 1}"

    def upsert(self, ticket_update):
        if not isinstance(ticket_update, KanbanTicketUpdate):
            raise ValueError("ticket_update must be KanbanTicketUpdate")

        text = self.read_text()
        match = self.ARRAY_PATTERN.search(text)
        if not match:
            raise ValueError("tickets array not found in project_kanban.html")

        tickets = self._parse_ticket_objects(match.group("body"))
        payload = ticket_update.to_ticket_dict()
        ticket_id = payload["id"] or self.next_ticket_id()
        payload["id"] = ticket_id

        replaced = False
        for index, ticket in enumerate(tickets):
            if ticket.get("id") == ticket_id:
                merged = dict(ticket)
                merged.update(payload)
                tickets[index] = merged
                replaced = True
                break
        if not replaced:
            tickets.append(payload)

        rendered = self._render_ticket_array(tickets)
        updated = text[: match.start("body")] + rendered + text[match.end("body") :]
        self.write_text(updated)
        return ticket_id, "updated" if replaced else "created"

    def _parse_ticket_objects(self, body):
        objects = []
        chunk = []
        depth = 0
        in_string = False
        escape = False
        for char in body:
            if escape:
                chunk.append(char)
                escape = False
                continue
            if char == "\\":
                chunk.append(char)
                escape = True
                continue
            if char == '"':
                chunk.append(char)
                in_string = not in_string
                continue
            if not in_string and char == "{":
                depth += 1
            if depth > 0:
                chunk.append(char)
            if not in_string and char == "}":
                depth -= 1
                if depth == 0 and chunk:
                    objects.append("".join(chunk))
                    chunk = []
        tickets = []
        for obj in objects:
            ticket = {}
            for key, value in re.findall(
                r'(\w+):\s*"((?:\\.|[^"\\])*)"',
                obj,
                flags=re.S,
            ):
                ticket[key] = value.replace('\\"', '"').replace("\\\\", "\\")
            trace_match = re.search(r"trace:\s*\[(.*?)\]", obj, flags=re.S)
            if trace_match:
                ticket["trace"] = [
                    item.replace('\\"', '"').replace("\\\\", "\\")
                    for item in re.findall(r'"((?:\\.|[^"\\])*)"', trace_match.group(1))
                ]
            tickets.append(ticket)
        return tickets

    def _render_ticket_array(self, tickets):
        chunks = []
        for ticket in tickets:
            lines = [
                "  {",
                f'    id: {json.dumps(ticket.get("id", ""), ensure_ascii=False)},',
                f'    status: {json.dumps(ticket.get("status", "todo"), ensure_ascii=False)},',
                f'    priority: {json.dumps(ticket.get("priority", "medium"), ensure_ascii=False)},',
                f'    title: {json.dumps(ticket.get("title", ""), ensure_ascii=False)},',
                f'    copy: {json.dumps(ticket.get("copy", ""), ensure_ascii=False)},',
                f'    stageId: {json.dumps(ticket.get("stageId", "fusion"), ensure_ascii=False)},',
                f'    asis: {json.dumps(ticket.get("asis", ""), ensure_ascii=False)},',
                f'    tobe: {json.dumps(ticket.get("tobe", ""), ensure_ascii=False)},',
                f'    evidence: {json.dumps(ticket.get("evidence", ""), ensure_ascii=False)},',
            ]
            trace_values = ", ".join(
                json.dumps(value, ensure_ascii=False)
                for value in ticket.get("trace", [])
            )
            lines.append(f"    trace: [{trace_values}]")
            lines.append("  }")
            chunks.append("\n".join(lines))
        return "\n" + ",\n".join(chunks) + "\n"
