import json
from pathlib import Path
from unittest.mock import patch

from cidls.codex_global_loop.wiring_audit import build_report


def make_path_map(repo_root, codex_home):
    repo_root_text = str(repo_root)
    codex_home_text = str(codex_home)
    return {
        repo_root / ".mcp.json": json.dumps({
            "mcpServers": {
                "devrag": {
                    "command": str(codex_home / "mcp" / "cidls_global" / "launch-devrag.cmd"),
                }
            }
        }),
        codex_home / "hooks" / "run-cidls-hook.cmd": '\n'.join([
            '@echo off',
            "call :resolve_global_cidls_root",
            'set "LOCAL_HOOK=%CURRENT_DIR%\\pre_prompt_cycle.bat"',
            'set "GLOBAL_HOOK=%GLOBAL_CIDLS_ROOT%\\pre_prompt_cycle.bat"',
            'set "GLOBAL_INSTALLER=%GLOBAL_CIDLS_ROOT%\\installer.bat"',
            "if defined CIDLS_REPO (",
            ")",
            'if exist "%LOCAL_HOOK%" (',
            '  call :run_hook "%CURRENT_DIR%" "%LOCAL_HOOK%" "%LOCAL_INSTALLER%" "%CURRENT_DIR%"',
            ')',
        ]),
        codex_home / "AGENTS.md": '\n'.join([
            r"cmd /c %CODEX_HOME%\hooks\run-cidls-hook.cmd",
            r"<CIDLS_REPO>\AGENTS.md",
            r"%CODEX_HOME%\skills\cidls-global-ops",
            r"%CODEX_HOME%\skills\cidls-devrag-rag",
        ]),
        codex_home / "mcp" / "cidls_global" / "runtime-devrag-config.json": json.dumps({
            "document_patterns": [
                f"{repo_root_text}\\AGENTS.md",
                f"{repo_root_text}\\documents\\**\\*.md",
                f"{repo_root_text}\\docs\\**\\*.md",
                f"{repo_root_text}\\.github\\**\\*.md",
                f"{codex_home_text}\\AGENTS.md",
                f"{codex_home_text}\\skills\\cidls-global-ops\\**\\*.md",
                f"{codex_home_text}\\skills\\cidls-devrag-rag\\**\\*.md",
                f"{codex_home_text}\\automations\\agents-sw-cycle\\memory.md",
            ]
        }),
        codex_home / "mcp" / "cidls_global" / "build-runtime-config.py": "patterns = []\n",
        codex_home / "mcp" / "cidls_global" / "launch-devrag.cmd": '\n'.join([
            f'powershell -NoProfile -ExecutionPolicy Bypass -File "{repo_root_text}\\scripts\\cleanup_cidls_devrag_processes.ps1" -MinAgeMinutes 720 -Quiet',
            '"C:\\tools\\devrag.exe" schema >nul 2>nul',
        ]),
        codex_home / "skills" / "cidls-global-ops" / "SKILL.md": "run-cidls-hook.cmd\nproject_kanban.html\nsync_agents_cidls_policy.py\n",
        codex_home / "skills" / "cidls-devrag-rag" / "SKILL.md": "mcp__devrag__search\nruntime-devrag-config.json\n%CODEX_HOME%\\AGENTS.md\n",
    }


def patch_virtual_fs(path_map):
    def fake_exists(path):
        return Path(path) in path_map

    def fake_read_text(path):
        return path_map[Path(path)]

    def fake_load_json(path):
        return json.loads(path_map[Path(path)])

    return fake_exists, fake_read_text, fake_load_json


def test_build_report_passes_when_required_global_paths_exist():
    repo_root = Path("E:/portable/CIDLS")
    codex_home = Path("D:/profiles/alice/.codex")
    path_map = make_path_map(repo_root, codex_home)
    fake_exists, fake_read_text, fake_load_json = patch_virtual_fs(path_map)

    with patch("cidls.codex_global_loop.wiring_audit.file_exists", side_effect=fake_exists):
        with patch("cidls.codex_global_loop.wiring_audit.read_text", side_effect=fake_read_text):
            with patch("cidls.codex_global_loop.wiring_audit.load_json", side_effect=fake_load_json):
                with patch("cidls.codex_global_loop.wiring_audit.probe_runtime_acl", return_value={"available": True, "has_write_deny_acl": False, "raw_output": ""}):
                    with patch("cidls.codex_global_loop.wiring_audit.probe_devrag_execution", return_value={"available": True, "status": "ok", "returncode": 0, "stdout": "", "stderr": "", "error": ""}):
                        with patch("cidls.codex_global_loop.wiring_audit.probe_devrag_process_count", return_value={"available": True, "count": 1, "stderr": ""}):
                            report = build_report(repo_root=repo_root, codex_home=codex_home)

    assert report["issues"] == []
    assert report["global_agents_mirror_contract"].startswith("subset_required_strings")
    assert report["global_agents_byte_identical_to_repo"] is False
    assert report["global_agents_missing_required_strings"] == []
    assert report["runtime_missing_required_patterns"] == []
    assert report["skills"][0]["missing_required_strings"] == []


def test_build_report_flags_missing_global_agents_and_skill_guidance():
    repo_root = Path("C:/virtual/CIDLS")
    codex_home = Path("C:/virtual/.codex")
    path_map = make_path_map(repo_root, codex_home)
    path_map[codex_home / "AGENTS.md"] = "hook only\n"
    path_map[codex_home / "mcp" / "cidls_global" / "runtime-devrag-config.json"] = json.dumps({"document_patterns": []})
    path_map[codex_home / "skills" / "cidls-global-ops" / "SKILL.md"] = "project_kanban.html\n"
    path_map[codex_home / "skills" / "cidls-devrag-rag" / "SKILL.md"] = "runtime-devrag-config.json\n"
    fake_exists, fake_read_text, fake_load_json = patch_virtual_fs(path_map)

    with patch("cidls.codex_global_loop.wiring_audit.file_exists", side_effect=fake_exists):
        with patch("cidls.codex_global_loop.wiring_audit.read_text", side_effect=fake_read_text):
            with patch("cidls.codex_global_loop.wiring_audit.load_json", side_effect=fake_load_json):
                with patch("cidls.codex_global_loop.wiring_audit.probe_runtime_acl", return_value={"available": True, "has_write_deny_acl": False, "raw_output": ""}):
                    with patch("cidls.codex_global_loop.wiring_audit.probe_devrag_execution", return_value={"available": True, "status": "ok", "returncode": 0, "stdout": "", "stderr": "", "error": ""}):
                        with patch("cidls.codex_global_loop.wiring_audit.probe_devrag_process_count", return_value={"available": True, "count": 1, "stderr": ""}):
                            report = build_report(repo_root=repo_root, codex_home=codex_home)

    assert "global AGENTS.md is missing required CIDLS wiring instructions" in report["issues"]
    assert "runtime config is missing required CIDLS document patterns" in report["issues"]
    assert "skill file is missing required guidance: cidls-global-ops" in report["issues"]
    assert "skill file is missing required guidance: cidls-devrag-rag" in report["issues"]


def test_build_report_flags_missing_devrag_cleanup_guard():
    repo_root = Path("C:/virtual/CIDLS")
    codex_home = Path("C:/virtual/.codex")
    path_map = make_path_map(repo_root, codex_home)
    path_map[codex_home / "mcp" / "cidls_global" / "launch-devrag.cmd"] = '"C:\\tools\\devrag.exe" schema >nul 2>nul\n'
    fake_exists, fake_read_text, fake_load_json = patch_virtual_fs(path_map)

    with patch("cidls.codex_global_loop.wiring_audit.file_exists", side_effect=fake_exists):
        with patch("cidls.codex_global_loop.wiring_audit.read_text", side_effect=fake_read_text):
            with patch("cidls.codex_global_loop.wiring_audit.load_json", side_effect=fake_load_json):
                with patch("cidls.codex_global_loop.wiring_audit.probe_runtime_acl", return_value={"available": True, "has_write_deny_acl": False, "raw_output": ""}):
                    with patch("cidls.codex_global_loop.wiring_audit.probe_devrag_execution", return_value={"available": True, "status": "ok", "returncode": 0, "stdout": "", "stderr": "", "error": ""}):
                        with patch("cidls.codex_global_loop.wiring_audit.probe_devrag_process_count", return_value={"available": True, "count": 1, "stderr": ""}):
                            report = build_report(repo_root=repo_root, codex_home=codex_home)

    assert "launch-devrag.cmd does not clean stale devrag processes before MCP startup" in report["issues"]


def test_build_report_flags_excess_devrag_processes():
    repo_root = Path("C:/virtual/CIDLS")
    codex_home = Path("C:/virtual/.codex")
    path_map = make_path_map(repo_root, codex_home)
    fake_exists, fake_read_text, fake_load_json = patch_virtual_fs(path_map)

    with patch("cidls.codex_global_loop.wiring_audit.file_exists", side_effect=fake_exists):
        with patch("cidls.codex_global_loop.wiring_audit.read_text", side_effect=fake_read_text):
            with patch("cidls.codex_global_loop.wiring_audit.load_json", side_effect=fake_load_json):
                with patch("cidls.codex_global_loop.wiring_audit.probe_runtime_acl", return_value={"available": True, "has_write_deny_acl": False, "raw_output": ""}):
                    with patch("cidls.codex_global_loop.wiring_audit.probe_devrag_execution", return_value={"available": True, "status": "ok", "returncode": 0, "stdout": "", "stderr": "", "error": ""}):
                        with patch("cidls.codex_global_loop.wiring_audit.probe_devrag_process_count", return_value={"available": True, "count": 4, "stderr": ""}):
                            report = build_report(repo_root=repo_root, codex_home=codex_home)

    assert "too many devrag-windows-x64 processes are currently running" in report["issues"]


def test_build_report_flags_runtime_db_write_deny_acl():
    repo_root = Path("C:/virtual/CIDLS")
    codex_home = Path("C:/virtual/.codex")
    path_map = make_path_map(repo_root, codex_home)
    fake_exists, fake_read_text, fake_load_json = patch_virtual_fs(path_map)

    acl_results = [
        {"available": True, "has_write_deny_acl": False, "raw_output": ""},
        {"available": True, "has_write_deny_acl": True, "raw_output": "(DENY)(W,D,Rc,DC)"},
    ]

    with patch("cidls.codex_global_loop.wiring_audit.file_exists", side_effect=fake_exists):
        with patch("cidls.codex_global_loop.wiring_audit.read_text", side_effect=fake_read_text):
            with patch("cidls.codex_global_loop.wiring_audit.load_json", side_effect=fake_load_json):
                with patch("cidls.codex_global_loop.wiring_audit.probe_runtime_acl", side_effect=acl_results):
                    with patch("cidls.codex_global_loop.wiring_audit.probe_devrag_execution", return_value={"available": True, "status": "ok", "returncode": 0, "stdout": "", "stderr": "", "error": ""}):
                        with patch("cidls.codex_global_loop.wiring_audit.probe_devrag_process_count", return_value={"available": True, "count": 1, "stderr": ""}):
                            report = build_report(repo_root=repo_root, codex_home=codex_home)

    assert "global devrag vectors.db currently has an inherited write-deny ACL entry" in report["issues"]
    assert report["runtime_db_has_write_deny_acl"] is True
