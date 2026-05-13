#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_tickets(board_text):
    tickets = []
    match = re.search(r"const\s+tickets\s*=\s*\[(.*?)\]\s*;", board_text, flags=re.S)
    if not match:
        return tickets

    object_pattern = re.compile(r"\{(.*?)\}", flags=re.S)
    field_patterns = {
        "id": re.compile(r'id:\s*"((?:\\.|[^"\\])*)"', flags=re.S),
        "status": re.compile(r'status:\s*"((?:\\.|[^"\\])*)"', flags=re.S),
        "priority": re.compile(r'priority:\s*"((?:\\.|[^"\\])*)"', flags=re.S),
        "title": re.compile(r'title:\s*"((?:\\.|[^"\\])*)"', flags=re.S),
    }

    for obj_match in object_pattern.finditer(match.group(1)):
        raw = obj_match.group(0)
        item = {}
        for key, pattern in field_patterns.items():
            value_match = pattern.search(raw)
            if not value_match:
                item[key] = ""
                continue
            item[key] = (
                value_match.group(1)
                .replace('\\"', '"')
                .replace("\\\\", "\\")
                .strip()
            )
        if item.get("id") and item.get("title"):
            tickets.append(item)
    return tickets


def load_json_if_exists(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    repo_root = Path(__file__).resolve().parent.parent
    state_dir = repo_root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    source_board = repo_root / "project_kanban.html"
    legacy_board = repo_root / "kanban_project.html"
    agents_path = repo_root / "AGENTS.md"
    sync_report = repo_root / "logs" / "cidls_agents_sync_report.json"

    if not source_board.exists():
        raise FileNotFoundError("Source board not found: " + str(source_board))

    shutil.copy2(source_board, legacy_board)

    board_text = source_board.read_text(encoding="utf-8")
    tickets = parse_tickets(board_text)
    open_tickets = [ticket for ticket in tickets if ticket.get("status") not in {"done", "closed", "completed"}]
    review_tickets = [ticket for ticket in tickets if ticket.get("status") == "review"]
    todo_tickets = [ticket for ticket in tickets if ticket.get("status") == "todo"]

    report = load_json_if_exists(sync_report)
    runtime_state = {
        "generated_at_utc": utc_now_iso(),
        "repo_root": str(repo_root),
        "source_board": str(source_board),
        "legacy_board": str(legacy_board),
        "agents_md": str(agents_path),
        "sync_report": str(sync_report),
        "sync_report_action": report.get("action"),
        "ticket_count": len(tickets),
        "open_ticket_ids": [ticket["id"] for ticket in open_tickets],
        "review_ticket_ids": [ticket["id"] for ticket in review_tickets],
        "todo_ticket_ids": [ticket["id"] for ticket in todo_tickets],
        "highest_priority_open": [
            {
                "id": ticket["id"],
                "priority": ticket.get("priority", ""),
                "title": ticket["title"],
            }
            for ticket in open_tickets[:8]
        ],
        "hook_status": "ok",
    }

    (state_dir / "autonomy_state.json").write_text(
        json.dumps(runtime_state, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
