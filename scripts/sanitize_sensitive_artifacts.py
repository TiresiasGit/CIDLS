#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Sanitize local-only paths and token-like strings from CIDLS artifacts."""

import argparse
import json
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cidls.security_redaction import redact_sensitive_text


TEXT_SUFFIXES = {
    ".cmd",
    ".html",
    ".json",
    ".log",
    ".md",
    ".ps1",
    ".py",
    ".toml",
    ".txt",
    ".yml",
    ".yaml",
}
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    ".uv-cache",
    "__pycache__",
    "node_modules",
    "models",
    "cerememory-main",
}


def read_text(path):
    for encoding in ("utf-8", "utf-8-sig", "cp932"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return None


def iter_targets(paths):
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            continue
        if path.is_file():
            yield path
            continue
        for current, dirs, files in os.walk(path, onerror=lambda _error: None):
            current_path = Path(current)
            dirs[:] = [
                name for name in dirs
                if name not in EXCLUDED_PARTS and name not in {".pytest_tmp", "pytest_tmp"}
            ]
            if any(part in EXCLUDED_PARTS for part in current_path.parts):
                continue
            for name in files:
                child = current_path / name
                if child.suffix.lower() in TEXT_SUFFIXES:
                    yield child


def sanitize_file(path, repo_root, codex_home):
    text = read_text(path)
    if text is None:
        return False
    redacted = redact_sensitive_text(text, repo_root=repo_root, codex_home=codex_home)
    if redacted == text:
        return False
    path.write_text(redacted, encoding="utf-8", newline="\n")
    return True


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Sanitize CIDLS local artifacts.")
    parser.add_argument("paths", nargs="*", default=["logs", "reports"])
    parser.add_argument("--codex-home", default=str(Path.home() / ".codex"))
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    changed = []
    for path in iter_targets(args.paths):
        if sanitize_file(path, REPO_ROOT, Path(args.codex_home)):
            changed.append(str(path))
    result = {
        "changed_count": len(changed),
        "changed": changed,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
