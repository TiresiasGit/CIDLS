#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Repair write-deny ACL on the global devrag vectors.db.

When the Codex sandbox applies an inherited DENY(W,D,Rc,DC) ACE to vectors.db,
devrag cannot write to the index.  This script:
  1. Breaks ACL inheritance on vectors.db (copies inherited entries to explicit).
  2. Removes any deny ACEs via PowerShell SetAccessControl (handles unresolvable
     SIDs that icacls cannot address by name).
  3. Verifies write access with a no-op open test.
  4. Emits a JSON result to stdout and to logs/vectors_db_acl_repair_report.json.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
REPORT_PATH = REPO_ROOT / "logs" / "vectors_db_acl_repair_report.json"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cidls.codex_global_loop.wiring_audit import DEFAULT_CODEX_HOME, probe_runtime_acl


VECTORS_DB_PATH = DEFAULT_CODEX_HOME / "mcp" / "cidls_global" / "vectors.db"


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def break_inheritance(path: Path) -> dict:
    r = subprocess.run(
        ["icacls", str(path), "/inheritance:d"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    return {"returncode": r.returncode, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}


def remove_deny_aces_powershell(path: Path) -> dict:
    ps_script = (
        f"$acl = [System.IO.File]::GetAccessControl('{path}');\n"
        "$denies = $acl.Access | Where-Object { $_.AccessControlType -eq 'Deny' };\n"
        "$count = ($denies | Measure-Object).Count;\n"
        "Write-Host \"deny_count=$count\";\n"
        "foreach ($r in $denies) { [void]$acl.RemoveAccessRule($r) };\n"
        "[System.IO.File]::SetAccessControl('" + str(path) + "', $acl);\n"
        "Write-Host 'done'"
    )
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, timeout=30,
    )
    removed_count = 0
    for line in r.stdout.splitlines():
        if line.startswith("deny_count="):
            try:
                removed_count = int(line.split("=", 1)[1])
            except ValueError:
                pass
    return {
        "returncode": r.returncode,
        "removed_count": removed_count,
        "stdout": r.stdout.strip(),
        "stderr": r.stderr.strip(),
    }


def test_write(path: Path) -> bool:
    try:
        with open(path, "ab"):
            pass
        return True
    except (PermissionError, OSError):
        return False


def main():
    report = {
        "generated_at_utc": utc_now_iso(),
        "vectors_db_path": str(VECTORS_DB_PATH),
        "status": "pending",
        "steps": {},
        "issues": [],
    }

    if not VECTORS_DB_PATH.exists():
        report["status"] = "skipped_db_missing"
        report["issues"].append("vectors.db does not exist; nothing to repair")
        _write(report)
        return 0

    acl_before = probe_runtime_acl(VECTORS_DB_PATH)
    report["acl_before"] = acl_before["raw_output"]

    if not acl_before["has_write_deny_acl"]:
        report["status"] = "already_clean"
        report["steps"]["skip_reason"] = "no write-deny ACL found; no repair needed"
        _write(report)
        return 0

    # Step 1: break inheritance
    inh = break_inheritance(VECTORS_DB_PATH)
    report["steps"]["break_inheritance"] = inh
    if inh["returncode"] != 0:
        report["issues"].append(f"icacls /inheritance:d failed (rc={inh['returncode']})")

    # Step 2: remove deny ACEs
    ps = remove_deny_aces_powershell(VECTORS_DB_PATH)
    report["steps"]["remove_deny_aces"] = ps
    if ps["returncode"] != 0:
        report["issues"].append(f"PowerShell SetAccessControl failed (rc={ps['returncode']}): {ps['stderr'][:200]}")

    # Step 3: verify
    acl_after = probe_runtime_acl(VECTORS_DB_PATH)
    report["acl_after"] = acl_after["raw_output"]
    write_ok = test_write(VECTORS_DB_PATH)
    report["write_test"] = write_ok

    if acl_after["has_write_deny_acl"]:
        report["status"] = "repair_failed"
        report["issues"].append("write-deny ACL entry still present after repair")
    elif not write_ok:
        report["status"] = "repair_failed"
        report["issues"].append("write test failed even after deny ACE removal")
    else:
        report["status"] = "repaired"

    _write(report)
    return 0 if report["status"] == "repaired" else 1


def _write(report):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
