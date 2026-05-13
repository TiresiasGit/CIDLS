import json
import zipfile
from pathlib import Path

from scripts.audit_distribution_security import build_report, main


def test_distribution_audit_passes_clean_prompt_package(tmp_path):
    package = tmp_path / "prompt_package"
    package.mkdir()
    (package / "README.md").write_text(
        "Prompt package uses user-owned LLM keys and contains no operator secrets.",
        encoding="utf-8",
    )
    (package / "license_public.key").write_text("public-key-material", encoding="utf-8")

    report = build_report([package])

    assert report["ok"] is True
    assert report["finding_count"] == 0


def test_distribution_audit_detects_secret_files_and_tokens(tmp_path):
    package = tmp_path / "dist"
    package.mkdir()
    (package / ".env").write_text("STRIPE_SECRET_KEY=sk_live_1234567890abcdef\n", encoding="utf-8")
    (package / "client.js").write_text(
        "const name = 'NEXT_PUBLIC_WEBHOOK_SECRET';\n",
        encoding="utf-8",
    )

    report = build_report([package])
    codes = {finding["code"] for finding in report["findings"]}

    assert report["ok"] is False
    assert "SECRET_FILENAME" in codes
    assert "STRIPE_SECRET_KEY" in codes
    assert "NEXT_PUBLIC_SECRET_NAME" in codes


def test_distribution_audit_detects_zip_secret_material(tmp_path):
    archive_path = tmp_path / "release.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(".env", "WEBHOOK_SECRET=whsec_1234567890abcdef")
        archive.writestr("private.key", "-----BEGIN PRIVATE KEY-----")

    report = build_report([archive_path])
    codes = {finding["code"] for finding in report["findings"]}

    assert report["ok"] is False
    assert "ZIP_SECRET_FILE" in codes
    assert "ZIP_PRIVATE_KEY" in codes


def test_distribution_audit_cli_writes_report(tmp_path):
    target = tmp_path / "clean"
    target.mkdir()
    (target / "README.md").write_text("local-only exe package", encoding="utf-8")
    report_path = tmp_path / "report.json"

    exit_code = main([str(target), "--report", str(report_path)])
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert report["ok"] is True
