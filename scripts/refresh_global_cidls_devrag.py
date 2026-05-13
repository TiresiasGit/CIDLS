#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Guarded refresh for the global CIDLS devrag runtime config.

The global generator lives outside the workspace. This wrapper audits the
current global wiring first and skips refreshes while the known broad-root
configuration remains in place, so repo-local hooks do not keep re-expanding
the CIDLS corpus accidentally.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from audit_global_cidls_wiring import (
    GLOBAL_GENERATOR_PATH,
    GLOBAL_RUNTIME_CONFIG_PATH,
    build_report,
    load_json,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "logs" / "global_cidls_refresh_report.json"


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_report(report):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )


def append_issue(report, issue):
    if issue not in report["issues"]:
        report["issues"].append(issue)


def load_generator_module():
    spec = importlib.util.spec_from_file_location(
        "cidls_global_build_runtime_config",
        GLOBAL_GENERATOR_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load runtime config generator: {GLOBAL_GENERATOR_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_expected_runtime_config():
    module = load_generator_module()
    return {
        "document_patterns": module.build_document_patterns(),
        "db_path": str(module.DB_PATH),
        "chunk_size": 500,
        "search_top_k": 5,
        "compute": {
            "device": "cpu",
            "fallback_to_cpu": True,
        },
        "model": {
            "name": "multilingual-e5-small",
            "dimensions": 384,
        },
    }


def current_runtime_config_matches_expected():
    if not GLOBAL_RUNTIME_CONFIG_PATH.exists():
        return False

    current_config = load_json(GLOBAL_RUNTIME_CONFIG_PATH)
    expected_config = build_expected_runtime_config()
    return current_config == expected_config


def classify_refresh_failure(completed):
    stderr = completed.stderr or ""

    if "PermissionError" in stderr and "runtime-devrag-config.json" in stderr:
        return {
            "status": "blocked_external_acl",
            "failure_type": "global_runtime_config_acl",
            "issue": (
                "global runtime config write is blocked by filesystem ACL; "
                "manual CODEX_HOME ACL or launcher-context repair is required"
            ),
        }

    if "ONNX Runtime" in stderr or "failed to initialize embedder" in stderr:
        return {
            "status": "blocked_devrag_runtime",
            "failure_type": "devrag_onnx_runtime",
            "issue": (
                "devrag embedder failed to initialize because the available "
                "ONNX Runtime API is incompatible"
            ),
        }

    return {
        "status": "refresh_failed",
        "failure_type": "unclassified_refresh_failure",
        "issue": "global devrag refresh failed without a known failure signature",
    }


def auto_repair_vectors_db_acl(audit_report):
    if not audit_report.get("runtime_db_has_write_deny_acl"):
        return None
    repair_script = REPO_ROOT / "scripts" / "repair_vectors_db_acl.py"
    if not repair_script.exists():
        return {"status": "repair_script_missing"}
    completed = subprocess.run(
        [sys.executable, str(repair_script)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    try:
        result = json.loads(completed.stdout)
    except (json.JSONDecodeError, ValueError):
        result = {"status": "repair_parse_error", "raw": completed.stdout[:500]}
    return result


def main():
    audit_report = build_report()

    # Auto-repair vectors.db write-deny ACL before main logic
    acl_repair = auto_repair_vectors_db_acl(audit_report)
    if acl_repair and acl_repair.get("status") == "repaired":
        # Re-audit so the fixed state is captured in this run's report
        audit_report = build_report()

    blocked = (
        audit_report.get("runtime_contains_bare_codex_home")
        or audit_report.get("generator_contains_bare_codex_home")
    )

    report = {
        "generated_at_utc": utc_now_iso(),
        "status": "skipped_scope_blocked" if blocked else "pending",
        "generator_path": str(GLOBAL_GENERATOR_PATH),
        "audit_report_path": str(REPO_ROOT / "logs" / "global_cidls_wiring_report.json"),
        "issues": audit_report.get("issues", []),
        "audit": audit_report,
    }
    if acl_repair:
        report["vectors_db_acl_repair"] = acl_repair

    if blocked:
        report["message"] = (
            "Skipped global devrag refresh because bare Codex home scope is "
            "still present in the runtime or generator."
        )
        write_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if current_runtime_config_matches_expected():
        report["status"] = "already_current"
        report["message"] = (
            "Skipped global devrag refresh because runtime-devrag-config.json "
            "already matches the expected CIDLS-only config."
        )
        write_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    completed = subprocess.run(
        [sys.executable, str(GLOBAL_GENERATOR_PATH)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode == 0:
        report["status"] = "refreshed"
    else:
        failure = classify_refresh_failure(completed)
        report["status"] = failure["status"]
        report["failure_type"] = failure["failure_type"]
        append_issue(report, failure["issue"])

    report["returncode"] = completed.returncode
    report["stdout"] = completed.stdout
    report["stderr"] = completed.stderr
    write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
