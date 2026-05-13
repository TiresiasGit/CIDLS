#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules"}


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def should_skip(path):
    return any(part in SKIP_DIRS for part in path.parts)


def collect_files(root_dir, patterns):
    found = {}
    for pattern in patterns:
        matches = []
        for path in root_dir.rglob(pattern):
            if path.is_file() and not should_skip(path):
                matches.append(str(path))
        found[pattern] = sorted(matches)
    return found


def build_report(root_dir):
    patterns = [
        "alaya_analyzer.py",
        "*.duckdb",
        "*.db",
        "*.sqlite",
        "*.jsonl",
    ]
    found = collect_files(root_dir, patterns)
    logs_dir = root_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    analyzer_exists = bool(found["alaya_analyzer.py"])
    db_exists = bool(found["*.duckdb"] or found["*.db"] or found["*.sqlite"])
    trace_exists = bool(found["*.jsonl"])

    next_actions = []
    if not analyzer_exists:
        next_actions.append("alaya_analyzer.py が未配置のため、将来の解析器入力契約を別途定義する。")
    if not db_exists:
        next_actions.append("DuckDB / DB ファイルが未配置のため、最初のログ格納先を決める。")
    if not trace_exists:
        next_actions.append("JSONL trace が未配置のため、automation か対話ログの出力元を決める。")
    if analyzer_exists or db_exists or trace_exists:
        next_actions.append("検出済み入力を優先順位順に読み、改善候補を CIDLS チケットへ還元する。")

    report = {
        "generated_at_utc": utc_now_iso(),
        "root_dir": str(root_dir),
        "found": found,
        "summary": {
            "analyzer_exists": analyzer_exists,
            "db_exists": db_exists,
            "trace_exists": trace_exists,
        },
        "next_actions": next_actions,
    }
    report_path = logs_dir / "alaya_intake_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path, report


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

    root_dir = Path(__file__).resolve().parents[1]
    report_path, report = build_report(root_dir)
    print(
        json.dumps(
            {
                "ok": True,
                "report_path": str(report_path),
                "summary": report["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
