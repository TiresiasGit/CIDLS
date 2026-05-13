#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sync_agents_cidls_policy.py

Purpose:
- detect remaining CIDLS tasks from the configured source
- idempotently merge the multi-persona policy block into AGENTS.md
- emit a JSON execution report for automation runs

Important:
- this script does not register cron jobs
- this script does not create automations
- recurring execution must stay in the outer Code Apps automation layer
- the outer automation should be created once and only invoke this script
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Iterable


MARKER_START = "<!-- CIDLS_MULTI_PERSONA_POLICY_START -->"
MARKER_END = "<!-- CIDLS_MULTI_PERSONA_POLICY_END -->"
DEFAULT_CIDLS_TASK_SOURCES = (
    "kanban_project.html",
    "project_kanban.html",
)
DEFAULT_REPORT_PATH = Path("logs") / "cidls_agents_sync_report.json"


@dataclass
class Task:
    title: str
    raw: str
    status: str
    priority: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp932"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"decode failed: {path}")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def backup_file(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".bak.{timestamp}")
    shutil.copy2(path, backup_path)
    return backup_path


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return text


def strip_html_tags(text: str) -> str:
    text = re.sub(
        r"<!--\s*PROJECT_MD_MIGRATION_START\s*-->.*?<!--\s*PROJECT_MD_MIGRATION_END\s*-->",
        "",
        text,
        flags=re.I | re.S,
    )
    text = re.sub(r"<script\b[^>]*>.*?</script>", "", text, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", "", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", "\n", text)
    return unescape(text)


def map_status(status: str) -> str:
    if status in {"todo", "open", "backlog", "next", "queued"}:
        return "todo"
    if status in {"doing", "in_progress", "in-progress", "wip", "active"}:
        return "doing"
    if status in {"blocked", "hold", "pending"}:
        return "blocked"
    if status in {"review", "qa", "verify"}:
        return "review"
    return "unknown"


def map_priority(priority: str) -> str:
    if priority in {"p0", "highest", "critical", "urgent"}:
        return "p0"
    if priority in {"p1", "high"}:
        return "p1"
    if priority in {"p2", "medium", "normal"}:
        return "p2"
    return "unknown"


def detect_tasks_from_json(text: str) -> list[Task]:
    tasks: list[Task] = []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return tasks

    candidates: list[dict] = []
    if isinstance(data, list):
        candidates = [x for x in data if isinstance(x, dict)]
    elif isinstance(data, dict):
        for key in ("tasks", "items", "cards", "todos"):
            value = data.get(key)
            if isinstance(value, list):
                candidates.extend([x for x in value if isinstance(x, dict)])

    for item in candidates:
        title = str(
            item.get("title")
            or item.get("name")
            or item.get("task")
            or item.get("summary")
            or ""
        ).strip()
        if not title:
            continue

        status = str(item.get("status") or item.get("state") or "unknown").strip().lower()
        priority = str(item.get("priority") or item.get("prio") or "unknown").strip().lower()

        if status in {"done", "completed", "closed"}:
            continue

        tasks.append(
            Task(
                title=title,
                raw=json.dumps(item, ensure_ascii=False),
                status=map_status(status),
                priority=map_priority(priority),
            )
        )
    return tasks


def detect_tasks_from_js_tickets(text: str) -> list[Task]:
    tasks: list[Task] = []
    match = re.search(r"const\s+tickets\s*=\s*\[(.*?)\]\s*;", text, flags=re.S)
    if not match:
        return tasks

    tickets_body = match.group(1)
    object_pattern = re.compile(r"\{(.*?)\}", flags=re.S)
    field_patterns = {
        "title": re.compile(r'title:\s*"((?:\\.|[^"\\])*)"', flags=re.S),
        "status": re.compile(r'status:\s*"((?:\\.|[^"\\])*)"', flags=re.S),
        "priority": re.compile(r'priority:\s*"((?:\\.|[^"\\])*)"', flags=re.S),
    }

    for obj_match in object_pattern.finditer(tickets_body):
        raw = obj_match.group(0)
        fields: dict[str, str] = {}
        for key, pattern in field_patterns.items():
            value_match = pattern.search(raw)
            if not value_match:
                fields[key] = ""
                continue
            fields[key] = (
                value_match.group(1)
                .replace('\\"', '"')
                .replace("\\\\", "\\")
                .strip()
            )

        title = fields["title"]
        status = fields["status"].lower()
        priority = fields["priority"].lower()

        if not title or status in {"done", "completed", "closed"}:
            continue

        tasks.append(
            Task(
                title=title,
                raw=raw,
                status=map_status(status),
                priority=map_priority(priority),
            )
        )
    return tasks


def cleanup_task_title(text: str) -> str:
    text = re.sub(r"\[(?: |x|X|-)\]\s*", "", text)
    text = re.sub(
        r"\b(todo|doing|in[- ]?progress|wip|blocked|review|open|backlog|next|pending)\b[:：]?",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"\b(P0|P1|P2|critical|urgent|high|medium|normal)\b[:：]?",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(r"\s+", " ", text).strip(" -:：\t")
    return text


def deduplicate_tasks(tasks: Iterable[Task]) -> list[Task]:
    seen: set[str] = set()
    result: list[Task] = []
    for task in tasks:
        key = normalize_whitespace(task.title).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(task)
    return result


def detect_tasks_from_lines(text: str) -> list[Task]:
    tasks: list[Task] = []
    lines = text.splitlines()

    bullet_pattern = re.compile(
        r"^\s*(?:[-*+]|\d+[.)])\s*(?:\[(?P<check>[ xX-])\]\s*)?(?P<body>.+?)\s*$"
    )
    status_pattern = re.compile(
        r"\b(todo|doing|in[- ]?progress|wip|blocked|review|open|backlog|next|pending|done|completed|closed)\b",
        flags=re.I,
    )
    priority_pattern = re.compile(r"\b(P0|P1|P2|critical|urgent|high|medium|normal)\b", flags=re.I)

    for line in lines:
        m = bullet_pattern.match(line)
        if not m:
            continue

        body = m.group("body").strip()
        check = (m.group("check") or "").strip().lower()

        if not body:
            continue

        lowered = body.lower()

        if check == "x":
            continue
        if re.search(r"\b(done|completed|closed)\b", lowered):
            continue

        status_match = status_pattern.search(body)
        priority_match = priority_pattern.search(body)

        status = "todo"
        if status_match:
            status = map_status(status_match.group(1).lower())

        priority = "unknown"
        if priority_match:
            priority = map_priority(priority_match.group(1).lower())

        tasks.append(
            Task(
                title=cleanup_task_title(body),
                raw=line,
                status=status,
                priority=priority,
            )
        )

    return deduplicate_tasks(tasks)


def extract_open_tasks(cidls_path: Path) -> list[Task]:
    text = read_text(cidls_path)
    suffix = cidls_path.suffix.lower()

    if suffix == ".json":
        return deduplicate_tasks(detect_tasks_from_json(text))

    if suffix in {".html", ".htm"}:
        if re.search(r"const\s+tickets\s*=\s*\[", text, flags=re.S):
            return deduplicate_tasks(detect_tasks_from_js_tickets(text))
        js_tasks = detect_tasks_from_js_tickets(text)
        if js_tasks:
            return deduplicate_tasks(js_tasks)
        text = strip_html_tags(text)

    text = normalize_whitespace(text)
    tasks = detect_tasks_from_json(text)
    if tasks:
        return deduplicate_tasks(tasks)

    return detect_tasks_from_lines(text)


def rank_tasks(tasks: list[Task]) -> list[Task]:
    priority_order = {"p0": 0, "p1": 1, "p2": 2, "unknown": 3}
    status_order = {"doing": 0, "todo": 1, "review": 2, "blocked": 3, "unknown": 4}
    return sorted(
        tasks,
        key=lambda x: (
            priority_order.get(x.priority, 9),
            status_order.get(x.status, 9),
            x.title.lower(),
        ),
    )


def build_policy_block(tasks: list[Task], cidls_path: Path) -> str:
    cidls_source_label = f"<CIDLS_REPO>\\{cidls_path.name}"
    task_lines = "\n".join(
        f"- {task.title} (status={task.status}, priority={task.priority})"
        for task in tasks[:20]
    )
    if not task_lines:
        task_lines = "- No open CIDLS tasks detected."

    return f"""{MARKER_START}
## Current CIDLS Task Snapshot
### Purpose
Keep AGENTS.md aligned with the open CIDLS tasks from the operating board.
Review the current task source before implementation, surface the highest-value
work first, and keep related docs, code, QA, and mirrors in sync.

### Working rules
1. Start from the latest open CIDLS tasks and verify the root cause before editing.
2. Use multiple specialist lenses such as Architect, Analyzer, Security, Performance, QA, Backend, and Refactorer.
3. For each active task, capture:
   - investigation summary
   - affected source of truth and mirrors
   - implementation and verification plan
   - remaining blockers and risks
   - next action
4. Treat gaps as explicit decisions. Do not hide issues behind catch-all labels.
5. Keep AGENTS.md synchronized with the operating board, and review the impact before writing.
6. Keep working the CIDLS loop while kanban open work remains; do not stop at a partial checkpoint when unresolved CIDLS tickets still exist.
7. When the task snapshot changes, regenerate this block so the current priorities stay visible.

### CIDLS task snapshot source
Source path: {cidls_source_label}

{task_lines}

### Execution template
- Step 1: Inspect the latest CIDLS task snapshot
- Step 2: Identify the highest-value unresolved task
- Step 3: Trace the root cause and impacted artifacts
- Step 4: Implement and verify the fix, then update mirrors
- Step 5: Record blockers, decisions, and next actions

{MARKER_END}"""


def merge_policy_into_agents(agents_text: str, policy_block: str) -> tuple[str, str]:
    agents_text = agents_text.replace("\r\n", "\n").replace("\r", "\n")

    marker_pattern = re.compile(
        re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END),
        flags=re.S,
    )
    if marker_pattern.search(agents_text):
        updated = marker_pattern.sub(lambda _: policy_block, agents_text)
        return updated, "updated"

    insert_patterns = [
        re.compile(r"(?im)^##\s*(?:Current Policy|PROTOCOL|PROCESS|\[P1\]|\[P2\])\b"),
    ]

    for pattern in insert_patterns:
        match = pattern.search(agents_text)
        if match:
            idx = match.start()
            updated = agents_text[:idx].rstrip() + "\n\n" + policy_block + "\n\n" + agents_text[idx:].lstrip()
            return updated, "inserted"

    updated = agents_text.rstrip() + "\n\n" + policy_block + "\n"
    return updated, "appended"


def ensure_file_exists(path: Path, default_content: str = "") -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        write_text(path, default_content)


def resolve_cidls_tasks_path() -> Path:
    configured_path = os.environ.get("CIDLS_TASKS_FILE")
    if configured_path:
        return Path(configured_path).resolve()

    for candidate in DEFAULT_CIDLS_TASK_SOURCES:
        candidate_path = Path(candidate)
        if candidate_path.exists():
            return candidate_path.resolve()

    return Path(DEFAULT_CIDLS_TASK_SOURCES[0]).resolve()


def resolve_report_path() -> Path:
    configured_path = os.environ.get("SYNC_REPORT_PATH")
    if configured_path:
        return Path(configured_path).resolve()
    return DEFAULT_REPORT_PATH.resolve()


def build_default_agents_stub() -> str:
    return """# AGENTS.md

## Current Policy
- Keep AGENTS.md aligned with the current CIDLS task source.
- Review the latest tasks before implementation.
- Synchronize related docs, code, QA, and mirrors together.
"""


def make_report(
    agents_path: Path,
    cidls_path: Path,
    tasks: list[Task],
    action: str,
    backup_path: Path | None,
) -> dict:
    return {
        "ok": True,
        "generated_at_utc": utc_now_iso(),
        "agents_md": str(agents_path),
        "cidls_source": str(cidls_path),
        "action": action,
        "task_count": len(tasks),
        "tasks": [
            {
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
            }
            for task in tasks[:50]
        ],
        "backup_path": str(backup_path) if backup_path else None,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

    agents_md_path = Path(os.environ.get("AGENTS_MD_PATH", "AGENTS.md")).resolve()
    cidls_tasks_path = resolve_cidls_tasks_path()
    report_path = resolve_report_path()
    dry_run = os.environ.get("DRY_RUN", "0").strip() == "1"

    ensure_file_exists(agents_md_path, build_default_agents_stub())

    if not cidls_tasks_path.exists():
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"CIDLS task source not found: {cidls_tasks_path}",
                    "hint": (
                        "Set CIDLS_TASKS_FILE explicitly, for example project_kanban.html "
                        "/ kanban_project.html / project.md / TODO.md / tasks.json."
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    agents_text = read_text(agents_md_path)
    tasks = rank_tasks(extract_open_tasks(cidls_tasks_path))
    policy_block = build_policy_block(tasks, cidls_tasks_path)
    merged_text, action = merge_policy_into_agents(agents_text, policy_block)

    content_changed = merged_text != agents_text
    backup_path: Path | None = None
    if not dry_run and content_changed:
        backup_path = backup_file(agents_md_path)
        write_text(agents_md_path, merged_text)

    report = make_report(
        agents_path=agents_md_path,
        cidls_path=cidls_tasks_path,
        tasks=tasks,
        action=(
            "dry-run"
            if dry_run
            else action if content_changed else "unchanged"
        ),
        backup_path=backup_path,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_text(report_path, json.dumps(report, ensure_ascii=False, indent=2))

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
