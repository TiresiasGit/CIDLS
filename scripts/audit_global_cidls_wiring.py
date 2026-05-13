#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
REPORT_PATH = REPO_ROOT / "logs" / "global_cidls_wiring_report.json"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cidls.codex_global_loop.wiring_audit import DEFAULT_CODEX_HOME, build_report, load_json

GLOBAL_MCP_ROOT = DEFAULT_CODEX_HOME / "mcp" / "cidls_global"
GLOBAL_GENERATOR_PATH = GLOBAL_MCP_ROOT / "build-runtime-config.py"
GLOBAL_RUNTIME_CONFIG_PATH = GLOBAL_MCP_ROOT / "runtime-devrag-config.json"


def main():
    report = build_report(repo_root=REPO_ROOT)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
