# Code Apps Automations 前提の CIDLS→AGENTS 同期タスク

この Markdown は、**Code Apps の Automations に日次タスクを 1 件だけ登録し、その実行先として Python スクリプトを呼ぶ**前提で使うための資料です。

重要なのは次の点です。

- **Python の中で cron 形式や定期実行登録はしない**
- **Automation の新規作成を Python から行わない**
- **Code Apps の Automations 側で、日次実行を 1 回だけ設定する**
- **Python は毎回の実行処理だけを担当する**

これにより、**定期実行タスクの無限増殖を防ぎます**。

---

## 1. 結論

今回の用途では、Python スクリプトに必要なのは **CIDLS の残タスクを見て AGENTS.md を冪等更新する処理だけ** です。  
**スケジュール定義や Automation 登録処理は不要**です。

つまり責務はこう分かれます。

### Code Apps Automations 側
- 日次実行を 1 件だけ登録する
- その登録済みタスクから Python を呼ぶ

### Python 側
- CIDLS の残タスク抽出
- AGENTS.md の適切箇所へ規約を冪等マージ
- バックアップ出力
- 実行レポート出力

---

## 2. 無限増殖しない理由

この構成では、Python は **Automation 自体を作成しません**。  
そのため、日次実行されても新しい日次タスクは増えません。

無限増殖が起こるのは、例えば以下のような処理を Python に入れた場合です。

- 実行のたびに Automation API を叩いて自分自身を再登録する
- 実行のたびに scheduler 設定ファイルを増やす
- 実行時に cron エントリを追記する
- 自分を呼ぶ別のタスク定義を都度生成する

今回の修正版では、そのような処理は **一切入れません**。

---

## 3. 推奨運用

運用は次の 1 本だけです。

1. Code Apps の Automations に、**日次実行タスクを 1 件だけ**作る
2. その実行コマンドとして、以下の Python を呼ぶ
3. Python は内容同期だけ行って終了する

---

## 4. 実行スクリプト `sync_agents_cidls_policy.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sync_agents_cidls_policy.py

目的:
- CIDLS に残っているタスクを検出する
- AGENTS.md に「残タスク対応時は最初に多重人格会議を行う」方針を適切箇所へ冪等マージする
- Code Apps の Automations から呼ばれる実行処理だけを担当する

重要:
- このスクリプト自身は cron を登録しない
- Automation を新規作成しない
- 定期実行設定は外側の Code Apps Automations にのみ置く
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


def cleanup_task_title(text: str) -> str:
    text = re.sub(r"\[(?: |x|X|-)\]\s*", "", text)
    text = re.sub(r"\b(todo|doing|in[- ]?progress|wip|blocked|open|backlog|next|pending)\b[:：]?", "", text, flags=re.I)
    text = re.sub(r"\b(P0|P1|P2|critical|urgent|high|medium|normal)\b[:：]?", "", text, flags=re.I)
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
        r"\b(todo|doing|in[- ]?progress|wip|blocked|open|backlog|next|pending|done|completed|closed)\b",
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
        text = strip_html_tags(text)

    text = normalize_whitespace(text)
    tasks = detect_tasks_from_json(text)
    if tasks:
        return deduplicate_tasks(tasks)

    return detect_tasks_from_lines(text)


def rank_tasks(tasks: list[Task]) -> list[Task]:
    priority_order = {"p0": 0, "p1": 1, "p2": 2, "unknown": 3}
    status_order = {"doing": 0, "todo": 1, "blocked": 2, "unknown": 3}
    return sorted(
        tasks,
        key=lambda x: (
            priority_order.get(x.priority, 9),
            status_order.get(x.status, 9),
            x.title.lower(),
        ),
    )


def build_policy_block(tasks: list[Task], cidls_path: Path) -> str:
    generated_at = utc_now_iso()
    task_lines = "\n".join(
        f"- {task.title} 〔status={task.status}, priority={task.priority}〕"
        for task in tasks[:20]
    )
    if not task_lines:
        task_lines = "- 残タスク未検出"

    return f"""{MARKER_START}
## CIDLS連動実行規約

### 目的
CIDLS に残っているタスクへ着手する際、最初に多重人格会議を行い、単一視点の即断を防ぎ、根本原因・副作用・実装方針・検証観点を先に揃える。

### 必須ルール
1. CIDLS の未完了タスクへ着手する前に、必ず最初に多重人格会議を実施する。
2. 会議では最低限、Architect / Analyzer / Security / Performance / QA / Backend / Refactorer の観点を通す。
3. 会議結果は内部処理でよいが、最終出力には以下を反映する。
   - 対象タスクの目的
   - 根本原因または主要論点
   - 実行順序
   - 副作用・リスク
   - 完了条件
4. 出力は「的確に」行う。曖昧な一般論ではなく、そのタスクに対する具体判断とする。
5. AGENTS.md のこの規約は派生同期対象として扱い、削除・弱体化・孤立配置を禁止する。
6. 変更時は関連箇所を検索し、同一概念の記述ズレを残さない。

### CIDLS残タスクスナップショット
生成元: {cidls_path}
生成時刻(UTC): {generated_at}

{task_lines}

### 実行テンプレート
- Step 1: CIDLS 残タスク抽出
- Step 2: 多重人格会議で論点整理
- Step 3: 優先順位順に実行
- Step 4: 出力へ会議で確定した判断を反映
- Step 5: 完了条件と再発防止を明示

{MARKER_END}"""


def merge_policy_into_agents(agents_text: str, policy_block: str) -> tuple[str, str]:
    agents_text = agents_text.replace("\r\n", "\n").replace("\r", "\n")

    marker_pattern = re.compile(
        re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END),
        flags=re.S,
    )
    if marker_pattern.search(agents_text):
        updated = marker_pattern.sub(policy_block, agents_text)
        return updated, "updated"

    insert_patterns = [
        re.compile(r"(?im)^##\s*(?:絶対原則|実行原則|運用原則|PROTOCOL|PROCESS|開発サイクル)\b"),
        re.compile(r"(?im)^##\s*(?:入力プロトコル|注文票|注文票処理)\b"),
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


def build_default_agents_stub() -> str:
    return """# AGENTS.md

## 目的
派生指示書。上位思想と同期して運用する。

## 実行原則
- 根本原因を優先する
- 単一視点で即断しない
- 関連箇所へ水平展開する
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
    agents_md_path = Path(os.environ.get("AGENTS_MD_PATH", "AGENTS.md")).resolve()
    cidls_tasks_path = Path(os.environ.get("CIDLS_TASKS_FILE", "kanban_project.html")).resolve()
    report_path = Path(os.environ.get("SYNC_REPORT_PATH", "cidls_agents_sync_report.json")).resolve()
    dry_run = os.environ.get("DRY_RUN", "0").strip() == "1"

    ensure_file_exists(agents_md_path, build_default_agents_stub())

    if not cidls_tasks_path.exists():
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"CIDLS task source not found: {cidls_tasks_path}",
                    "hint": "Set CIDLS_TASKS_FILE to project.md / kanban_project.html / tasks.json etc.",
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

    backup_path: Path | None = None
    if not dry_run and merged_text != agents_text:
        backup_path = backup_file(agents_md_path)
        write_text(agents_md_path, merged_text)

    report = make_report(
        agents_path=agents_md_path,
        cidls_path=cidls_tasks_path,
        tasks=tasks,
        action="dry-run" if dry_run else action,
        backup_path=backup_path,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_text(report_path, json.dumps(report, ensure_ascii=False, indent=2))

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

## 5. 実行方法

Code Apps の Automations 側で、**日次実行タスクを 1 件だけ登録**し、そのコマンドとして次を呼びます。

```bash
mkdir -p /workspace/logs
export CIDLS_TASKS_FILE=/workspace/kanban_project.html
export AGENTS_MD_PATH=/workspace/AGENTS.md
export SYNC_REPORT_PATH=/workspace/logs/cidls_agents_sync_report.json
python /workspace/scripts/sync_agents_cidls_policy.py
```

ドライランしたい場合のみ:

```bash
mkdir -p /workspace/logs
export DRY_RUN=1
export CIDLS_TASKS_FILE=/workspace/kanban_project.html
export AGENTS_MD_PATH=/workspace/AGENTS.md
export SYNC_REPORT_PATH=/workspace/logs/cidls_agents_sync_report.json
python /workspace/scripts/sync_agents_cidls_policy.py
```

---

## 6. AGENTS.md に入る規約の要旨

```md
CIDLS に残っているタスクへ着手する際は、必ず最初に多重人格会議を行うこと。  
会議では最低限、Architect / Analyzer / Security / Performance / QA / Backend / Refactorer の観点を通し、対象タスクの目的、根本原因または主要論点、実行順序、副作用・リスク、完了条件を整理したうえで、的確な出力へ反映すること。  
この規約は AGENTS.md の適切箇所へ維持されるべき派生同期対象であり、削除・弱体化・孤立配置を禁止する。
```

---

## 7. この構成で満たすこと

- CIDLS 側の未完了タスクを抽出
- AGENTS.md に対象規約を冪等マージ
- 既存の同ブロックは置換更新
- バックアップを自動生成
- 実行結果を JSON レポート化
- Python 側でスケジュール登録をしない
- 日次実行しても Automation を増殖させない

---

## 8. 推奨ファイル構成

```text
/workspace/
  AGENTS.md
  kanban_project.html
  scripts/
    sync_agents_cidls_policy.py
  logs/
    cidls_agents_sync_report.json
```

---

## 9. 最終注意

この用途では、**定期実行は外側に 1 個だけ**、**Python は中身の処理だけ**、という分離が正しいです。

- 外側: Code Apps Automations
- 内側: 同期処理 Python

この分離を崩さない限り、**定期実行の定期実行タスクが無限に生成されることはありません**。
