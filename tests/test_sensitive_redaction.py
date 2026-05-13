import json
from pathlib import Path
from unittest.mock import patch

from cidls.security_redaction import redact_sensitive_text
from cidls.codex_global_loop.wiring_audit import build_report

from tests.codex_global_loop.test_wiring_audit import make_path_map, patch_virtual_fs


def test_redact_sensitive_text_generalizes_local_paths_and_tokens():
    user_path = "C:" + r"\Users\local-user\.codex\mcp\cidls_global\vectors.db"
    repo_path = "C:" + r"\Github\CIDLS\AGENTS.md"
    tool_path = "C:" + r"\Github\local-product\devrag-bin\devrag-windows-x64.exe"
    sid_value = "S-1-5-" + "21-2884379361-2715710224-2714001500-1178472556"
    youtube_token = "QU" + "FFLUhqbEs2QXhTMExYUThaZEViTzJoR0hzY0lQRTY1QXxBQ3Jtc0Tu"
    google_key = "AI" + "zaSyDZNkyC-AtROwMBpLfevIvqYk-Gfi8ZOeo"
    secret_key = "sk-" + "ant-live-secret-value"
    source = (
        f"{user_path} "
        f"{repo_path} "
        f"{tool_path} "
        r"Username: WORKSTATION\local-user "
        f"{sid_value} "
        f'"TOKEN_FIELD":"{youtube_token}" '
        f'"apiKey":"{google_key}" '
        f"{secret_key}"
    )

    redacted = redact_sensitive_text(
        source,
        repo_root=Path("C:" + r"\Github\CIDLS"),
        codex_home=Path("C:" + r"\Users\local-user\.codex"),
    )

    assert "local-user" not in redacted
    assert "WORKSTATION" not in redacted
    assert "local-product" not in redacted
    assert "S-1-5-" + "21" not in redacted
    assert "QU" + "FFLU" not in redacted
    assert "AI" + "zaSy" not in redacted
    assert "sk-" + "ant" not in redacted
    assert "%CODEX_HOME%" in redacted
    assert "<CIDLS_REPO>" in redacted
    assert "<WINDOWS_ACCOUNT>" in redacted


def test_global_wiring_report_redacts_paths_and_acl_identity():
    repo_root = Path("E:/portable/CIDLS")
    codex_home = Path("D:/profiles/alice/.codex")
    path_map = make_path_map(repo_root, codex_home)
    fake_exists, fake_read_text, fake_load_json = patch_virtual_fs(path_map)
    acl_text = (
        r"D:\profiles\alice\.codex\mcp\cidls_global\vectors.db "
        r"WORKSTATION\alice:(F) "
        "S-1-5-" + "21-111111-222222-333333-4444:(M,DC)"
    )

    with patch("cidls.codex_global_loop.wiring_audit.file_exists", side_effect=fake_exists):
        with patch("cidls.codex_global_loop.wiring_audit.read_text", side_effect=fake_read_text):
            with patch("cidls.codex_global_loop.wiring_audit.load_json", side_effect=fake_load_json):
                with patch(
                    "cidls.codex_global_loop.wiring_audit.probe_runtime_acl",
                    return_value={
                        "available": True,
                        "has_write_deny_acl": False,
                        "raw_output": acl_text,
                    },
                ):
                    with patch(
                        "cidls.codex_global_loop.wiring_audit.probe_devrag_execution",
                        return_value={
                            "available": True,
                            "status": "ok",
                            "returncode": 0,
                            "stdout": "",
                            "stderr": "",
                            "error": "",
                        },
                    ):
                        with patch(
                            "cidls.codex_global_loop.wiring_audit.probe_devrag_process_count",
                            return_value={"available": True, "count": 1, "stderr": ""},
                        ):
                            report = build_report(repo_root=repo_root, codex_home=codex_home)

    serialized = json.dumps(report, ensure_ascii=False)
    assert "D:/profiles/alice" not in serialized
    assert "D:\\profiles\\alice" not in serialized
    assert "E:/portable/CIDLS" not in serialized
    assert "WORKSTATION" not in serialized
    assert "S-1-5-" + "21" not in serialized
    assert "%CODEX_HOME%" in serialized
    assert "<CIDLS_REPO>" in serialized
