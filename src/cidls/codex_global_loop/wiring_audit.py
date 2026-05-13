import json
import hashlib
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from cidls.security_redaction import redact_mapping


DEFAULT_USERPROFILE = Path(os.environ.get("USERPROFILE", "").strip()) if os.environ.get("USERPROFILE", "").strip() else Path.home()
DEFAULT_CODEX_HOME = Path(os.environ.get("CODEX_HOME", "").strip()) if os.environ.get("CODEX_HOME", "").strip() else DEFAULT_USERPROFILE / ".codex"


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_required_global_agents_strings(repo_root, codex_home):
    return [
        r"cmd /c %CODEX_HOME%\hooks\run-cidls-hook.cmd",
        r"<CIDLS_REPO>\AGENTS.md",
        r"%CODEX_HOME%\skills\cidls-global-ops",
        r"%CODEX_HOME%\skills\cidls-devrag-rag",
    ]


def build_required_runtime_patterns(repo_root, codex_home):
    return [
        f"{repo_root}\\AGENTS.md",
        f"{repo_root}\\documents\\**\\*.md",
        f"{repo_root}\\docs\\**\\*.md",
        f"{repo_root}\\.github\\**\\*.md",
        f"{codex_home}\\AGENTS.md",
        f"{codex_home}\\skills\\cidls-global-ops\\**\\*.md",
        f"{codex_home}\\skills\\cidls-devrag-rag\\**\\*.md",
        f"{codex_home}\\automations\\agents-sw-cycle\\memory.md",
    ]


def build_skill_requirements(codex_home):
    return [
        {
            "name": "cidls-global-ops",
            "relative_path": Path("skills") / "cidls-global-ops" / "SKILL.md",
            "required_strings": [
                "run-cidls-hook.cmd",
                "project_kanban.html",
                "sync_agents_cidls_policy.py",
            ],
        },
        {
            "name": "cidls-devrag-rag",
            "relative_path": Path("skills") / "cidls-devrag-rag" / "SKILL.md",
            "required_strings": [
                "mcp__devrag__search",
                "runtime-devrag-config.json",
                r"%CODEX_HOME%\AGENTS.md",
            ],
        },
    ]


def read_text(path):
    for encoding in ("utf-8", "utf-8-sig", "cp932"):
        try:
            return Path(path).read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"decode failed: {path}")


def load_json(path):
    return json.loads(read_text(path).lstrip("\ufeff"))


def file_exists(path):
    return Path(path).exists()


def find_missing_strings(text, required_strings):
    missing = []
    for candidate in required_strings:
        if candidate not in text:
            missing.append(candidate)
    return missing


def content_sha256(path):
    if not file_exists(path):
        return ""
    text = read_text(path)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hook_prefers_local(hook_text):
    return 'if exist "%LOCAL_HOOK%"' in hook_text and 'call :run_hook "%CURRENT_DIR%"' in hook_text


def hook_targets_expected_paths(hook_text, repo_root):
    required = [
        "call :resolve_global_cidls_root",
        'set "LOCAL_HOOK=%CURRENT_DIR%\\pre_prompt_cycle.bat"',
        'set "GLOBAL_HOOK=%GLOBAL_CIDLS_ROOT%\\pre_prompt_cycle.bat"',
        'set "GLOBAL_INSTALLER=%GLOBAL_CIDLS_ROOT%\\installer.bat"',
        "CIDLS_REPO",
    ]
    return not find_missing_strings(hook_text, required)


def runtime_contains_bare_codex_home(runtime_config, codex_home):
    document_patterns = runtime_config.get("document_patterns", [])
    return str(Path(codex_home)) in document_patterns


def generator_contains_bare_codex_home(generator_text):
    return bool(re.search(r"^\s*CODEX_HOME\s*,\s*$", generator_text, flags=re.M))


def extract_mcp_command(mcp_config):
    servers = mcp_config.get("mcpServers", {})
    devrag_config = servers.get("devrag", {})
    return devrag_config.get("command", "")


def resolve_configured_path(value, repo_root, codex_home):
    """Resolve placeholders used in public configs to local paths for audit checks."""
    resolved = str(value or "")
    resolved = resolved.replace("%CODEX_HOME%", str(codex_home))
    resolved = resolved.replace("<CIDLS_REPO>", str(repo_root))
    resolved = resolved.replace("%USERPROFILE%", str(DEFAULT_USERPROFILE))
    return resolved


def extract_devrag_executable_path(launcher_text):
    match = re.search(r'"([^"]*devrag[^"]*\.exe)"', launcher_text, flags=re.I)
    if not match:
        return ""
    return match.group(1)


def launcher_writes_stdout_preamble(launcher_text, generator_text):
    runs_generator = "build-runtime-config.py" in launcher_text
    silences_output = ">nul" in launcher_text.lower() or "1>nul" in launcher_text.lower()
    generator_prints = "print(" in generator_text
    return runs_generator and generator_prints and not silences_output


def launcher_has_devrag_cleanup_guard(launcher_text):
    return (
        "cleanup_cidls_devrag_processes.ps1" in launcher_text
        and "-MinAgeMinutes" in launcher_text
        and "-Quiet" in launcher_text
    )


def probe_devrag_process_count():
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "(Get-Process -Name devrag-windows-x64 -ErrorAction SilentlyContinue | Measure-Object).Count",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        return {
            "available": False,
            "count": None,
            "stderr": completed.stderr.strip(),
        }
    raw_count = (completed.stdout or "0").strip()
    try:
        count = int(raw_count)
    except ValueError:
        count = None
    return {
        "available": True,
        "count": count,
        "stderr": completed.stderr.strip(),
    }


def probe_runtime_acl(path):
    if not file_exists(path):
        return {
            "available": False,
            "has_write_deny_acl": False,
            "raw_output": "",
        }

    completed = subprocess.run(
        ["icacls", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    acl_output = completed.stdout or ""
    has_write_deny_acl = "(DENY)" in acl_output and "(W" in acl_output
    return {
        "available": completed.returncode == 0,
        "has_write_deny_acl": has_write_deny_acl,
        "raw_output": acl_output.strip(),
    }


def classify_devrag_probe_failure(message):
    lowered = message.lower()
    if "winerror 4551" in lowered or "application control policy" in lowered:
        return "blocked_application_control_policy"
    if "繧｢繝励Μ繧ｱ繝ｼ繧ｷ繝ｧ繝ｳ蛻ｶ蠕｡繝昴Μ繧ｷ繝ｼ" in message:
        return "blocked_application_control_policy"
    if "onnx runtime" in lowered:
        return "blocked_devrag_runtime"
    return "os_error"


def probe_devrag_execution(devrag_executable_path):
    if not devrag_executable_path:
        return {
            "available": False,
            "status": "missing_launcher_target",
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "error": "",
        }

    devrag_path = Path(devrag_executable_path)
    if not file_exists(devrag_path):
        return {
            "available": False,
            "status": "missing_executable",
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "error": "",
        }

    try:
        completed = subprocess.run(
            [str(devrag_path), "schema"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=15,
        )
    except OSError as exc:
        return {
            "available": True,
            "status": classify_devrag_probe_failure(str(exc)),
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "error": str(exc),
        }

    stderr = completed.stderr or ""
    stdout = completed.stdout or ""
    status = "ok" if completed.returncode == 0 else "failed"
    if "ONNX Runtime" in stderr or "failed to initialize embedder" in stderr:
        status = "blocked_devrag_runtime"

    return {
        "available": True,
        "status": status,
        "returncode": completed.returncode,
        "stdout": stdout.strip(),
        "stderr": stderr.strip(),
        "error": "",
    }


def evaluate_skill_requirements(codex_home):
    results = []
    for rule in build_skill_requirements(codex_home):
        skill_path = Path(codex_home) / rule["relative_path"]
        exists = file_exists(skill_path)
        skill_text = read_text(skill_path) if exists else ""
        missing_strings = find_missing_strings(skill_text, rule["required_strings"]) if exists else list(rule["required_strings"])
        results.append(
            {
                "name": rule["name"],
                "path": str(skill_path),
                "exists": exists,
                "missing_required_strings": missing_strings,
            }
        )
    return results


def build_report(repo_root="", codex_home=""):
    issues = []
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[3]
    codex_home = Path(codex_home) if codex_home else DEFAULT_CODEX_HOME
    repo_root_text = str(repo_root)
    codex_home_text = str(codex_home)

    mcp_config_path = repo_root / ".mcp.json"
    global_hook_path = codex_home / "hooks" / "run-cidls-hook.cmd"
    global_agents_path = codex_home / "AGENTS.md"
    global_mcp_root = codex_home / "mcp" / "cidls_global"
    runtime_config_path = global_mcp_root / "runtime-devrag-config.json"
    generator_path = global_mcp_root / "build-runtime-config.py"
    launcher_path_expected = global_mcp_root / "launch-devrag.cmd"

    if not file_exists(mcp_config_path):
        issues.append("repo .mcp.json is missing")
    if not file_exists(global_hook_path):
        issues.append("global hook script is missing")
    if not file_exists(global_agents_path):
        issues.append("global AGENTS.md is missing")
    if not file_exists(generator_path):
        issues.append("global runtime config generator is missing")
    if not file_exists(launcher_path_expected):
        issues.append("global devrag launcher is missing")

    mcp_config = load_json(mcp_config_path) if file_exists(mcp_config_path) else {}
    hook_text = read_text(global_hook_path) if file_exists(global_hook_path) else ""
    global_agents_text = read_text(global_agents_path) if file_exists(global_agents_path) else ""
    runtime_config_generated_on_demand = (
        not file_exists(runtime_config_path) and file_exists(generator_path)
    )
    runtime_config = load_json(runtime_config_path) if file_exists(runtime_config_path) else {}
    generator_text = read_text(generator_path) if file_exists(generator_path) else ""
    mcp_command = extract_mcp_command(mcp_config)
    resolved_mcp_command = resolve_configured_path(mcp_command, repo_root, codex_home)
    launcher_path = Path(resolved_mcp_command) if resolved_mcp_command else Path()
    launcher_text = read_text(launcher_path) if mcp_command and file_exists(launcher_path) else ""
    devrag_executable_path = extract_devrag_executable_path(launcher_text)
    launcher_has_stdout_preamble = launcher_writes_stdout_preamble(launcher_text, generator_text)
    launcher_cleanup_guard = launcher_has_devrag_cleanup_guard(launcher_text)
    runtime_acl = probe_runtime_acl(runtime_config_path)
    runtime_db_path = Path(runtime_config.get("db_path", global_mcp_root / "vectors.db"))
    runtime_db_acl = probe_runtime_acl(runtime_db_path)
    devrag_processes = probe_devrag_process_count()
    devrag_probe = probe_devrag_execution(devrag_executable_path)
    global_agents_missing_strings = find_missing_strings(
        global_agents_text,
        build_required_global_agents_strings(repo_root_text, codex_home_text),
    )
    repo_agents_path = repo_root / "AGENTS.md"
    repo_agents_hash = content_sha256(repo_agents_path)
    global_agents_hash = content_sha256(global_agents_path)
    global_agents_byte_identical = (
        bool(repo_agents_hash)
        and bool(global_agents_hash)
        and repo_agents_hash == global_agents_hash
    )
    skill_reports = evaluate_skill_requirements(codex_home)

    runtime_has_bare_root = runtime_contains_bare_codex_home(runtime_config, codex_home)
    generator_has_bare_root = generator_contains_bare_codex_home(generator_text)
    runtime_patterns = list(runtime_config.get("document_patterns", []))
    missing_runtime_patterns = find_missing_strings(
        "\n".join(runtime_patterns),
        build_required_runtime_patterns(repo_root_text, codex_home_text),
    )
    if runtime_config_generated_on_demand:
        missing_runtime_patterns = []
    if runtime_has_bare_root:
        issues.append("runtime config still contains bare Codex home document root")
    if generator_has_bare_root:
        issues.append("generator still injects bare Codex home document root")
    if runtime_acl["has_write_deny_acl"]:
        issues.append("runtime config currently has an inherited write-deny ACL entry")
    if runtime_db_acl["has_write_deny_acl"]:
        issues.append("global devrag vectors.db currently has an inherited write-deny ACL entry")
    if launcher_has_stdout_preamble:
        issues.append(
            "launch-devrag.cmd prints runtime-config output before the MCP server starts, which can break stdio handshake"
        )
    if not launcher_cleanup_guard:
        issues.append("launch-devrag.cmd does not clean stale devrag processes before MCP startup")
    if devrag_processes["count"] is not None and devrag_processes["count"] > 3:
        issues.append("too many devrag-windows-x64 processes are currently running")
    if devrag_probe["status"] == "blocked_application_control_policy":
        issues.append("devrag executable is blocked by application control policy in this automation context")
    if devrag_probe["status"] == "blocked_devrag_runtime":
        issues.append("devrag executable reaches runtime but the embedder initialization fails")
    if not hook_prefers_local(hook_text):
        issues.append("global hook no longer prefers the local workspace pre_prompt_cycle.bat")
    if not hook_targets_expected_paths(hook_text, repo_root_text):
        issues.append("global hook path wiring does not match the expected CIDLS root and installer paths")
    if global_agents_missing_strings:
        issues.append("global AGENTS.md is missing required CIDLS wiring instructions")
    if resolved_mcp_command and Path(resolved_mcp_command) != launcher_path_expected:
        issues.append("repo .mcp.json devrag command does not point at the expected global launcher")
    if missing_runtime_patterns and not runtime_config_generated_on_demand:
        issues.append("runtime config is missing required CIDLS document patterns")
    for skill_report in skill_reports:
        if not skill_report["exists"]:
            issues.append(f"skill file is missing: {skill_report['name']}")
        elif skill_report["missing_required_strings"]:
            issues.append(f"skill file is missing required guidance: {skill_report['name']}")

    report = {
        "generated_at_utc": utc_now_iso(),
        "repo_root": str(repo_root),
        "resolved_codex_home": str(codex_home),
        "mcp_config_path": str(mcp_config_path),
        "mcp_command": mcp_command,
        "mcp_command_matches_expected_launcher": bool(resolved_mcp_command) and Path(resolved_mcp_command) == launcher_path_expected,
        "global_hook_path": str(global_hook_path),
        "global_hook_prefers_local_workspace_hook": hook_prefers_local(hook_text),
        "global_hook_targets_expected_paths": hook_targets_expected_paths(hook_text, repo_root_text),
        "global_agents_path": str(global_agents_path),
        "global_agents_mirror_contract": (
            "subset_required_strings: global AGENTS.md must carry the CIDLS hook, "
            "repo AGENTS source, and CIDLS skill pointers; byte identity with the "
            "repo AGENTS.md is not required because the global file may also contain "
            "Codex-wide guidance."
        ),
        "global_agents_repo_content_sha256": repo_agents_hash,
        "global_agents_content_sha256": global_agents_hash,
        "global_agents_byte_identical_to_repo": global_agents_byte_identical,
        "global_agents_missing_required_strings": global_agents_missing_strings,
        "global_mcp_root": str(global_mcp_root),
        "launcher_path": str(launcher_path) if mcp_command else "",
        "launcher_path_expected": str(launcher_path_expected),
        "launcher_writes_stdout_preamble": launcher_has_stdout_preamble,
        "launcher_has_devrag_cleanup_guard": launcher_cleanup_guard,
        "runtime_config_path": str(runtime_config_path),
        "runtime_config_generated_on_demand": runtime_config_generated_on_demand,
        "runtime_document_patterns": runtime_patterns,
        "runtime_missing_required_patterns": missing_runtime_patterns,
        "runtime_contains_bare_codex_home": runtime_has_bare_root,
        "runtime_config_has_write_deny_acl": runtime_acl["has_write_deny_acl"],
        "runtime_config_acl": runtime_acl["raw_output"],
        "runtime_db_path": str(runtime_db_path),
        "runtime_db_has_write_deny_acl": runtime_db_acl["has_write_deny_acl"],
        "runtime_db_acl": runtime_db_acl["raw_output"],
        "generator_path": str(generator_path),
        "generator_contains_bare_codex_home": generator_has_bare_root,
        "skills": skill_reports,
        "devrag_process_count": devrag_processes["count"],
        "devrag_process_count_probe_available": devrag_processes["available"],
        "devrag_executable_path": devrag_executable_path,
        "devrag_executable_status": devrag_probe["status"],
        "devrag_executable_returncode": devrag_probe["returncode"],
        "devrag_executable_error": devrag_probe["error"],
        "devrag_executable_stdout": devrag_probe["stdout"],
        "devrag_executable_stderr": devrag_probe["stderr"],
        "issues": issues,
    }
    return redact_mapping(report, repo_root=repo_root, codex_home=codex_home)
