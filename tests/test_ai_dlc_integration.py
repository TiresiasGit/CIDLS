import json
import subprocess
import sys
import zipfile
from pathlib import Path

from cidls.commercial_delivery.generator import build_commercial_delivery_package


ROOT = Path(__file__).resolve().parents[1]
CODEX_HOME = Path.home() / ".codex"


def workbook_text(path):
    with zipfile.ZipFile(path) as archive:
        return "\n".join(
            archive.read(name).decode("utf-8")
            for name in archive.namelist()
            if name.endswith(".xml")
        )


def test_ai_dlc_sources_are_reflected_in_excel_pack(tmp_path):
    package = build_commercial_delivery_package(
        output_dir=tmp_path,
        project_name="CIDLS AI-DLC統合検証",
    )
    text = workbook_text(Path(package["workbook_path"]))

    assert "33_AI-DLC統合" in text
    assert "価値創造ゾーン" in text
    assert "問題定義" in text
    assert "全体設計" in text
    assert "テストとレビュー" in text
    assert "WBS" in text
    assert "クリティカルパス" in text
    assert "プロジェクトバッファ" in text
    assert "変更管理" in text
    assert "AI-DLC" in text
    assert "Inception" in text
    assert "コンテキスト整備" in text
    assert "レビュー負荷" in text
    assert "Qiita" in text
    assert "Findy Team+" in text


def test_ui_spatial_cognitive_principle_is_expanded_to_skills_and_docs():
    targets = [
        ROOT / "documents" / "ai-dlc-cidls-integration.md",
        ROOT / "src" / "cidls" / "commercial_delivery" / "generator.py",
        CODEX_HOME / "skills" / "cidls-global-ops" / "SKILL.md",
        CODEX_HOME / "skills" / "cidls-devrag-rag" / "SKILL.md",
        CODEX_HOME / "automations" / "agents-sw-cycle" / "automation.toml",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in targets)

    assert "iframeを使わない" in combined
    assert "立体構造" in combined
    assert "過剰な注意力" in combined
    assert "ユーザーの脳" in combined
    assert "思想や考えをそのまま文字にしてユーザーに見せない" in combined
    assert "WebのUIの立体構成で伝える" in combined


def test_ai_dlc_integration_audit_passes():
    completed = subprocess.run(
        [sys.executable, "scripts/audit_ai_dlc_integration.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert completed.returncode == 0, (completed.stdout or "") + (completed.stderr or "")
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["checked_count"] >= 6
    assert not payload["missing"]
