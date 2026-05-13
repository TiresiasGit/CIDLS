import os
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODEX_HOME = Path.home() / ".codex"


def workbook_text(path):
    with zipfile.ZipFile(path) as archive:
        return "\n".join(
            archive.read(name).decode("utf-8")
            for name in archive.namelist()
            if name.endswith(".xml")
        )


def test_agents_contains_pray_computeuse_a5m2_and_daily_loop():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    for term in [
        "[PRAY_APP_FACTORY]",
        "祈り入力から商用成果物群を生成するCIDLS運用",
        "[ORTHO_COMPRESS]",
        "AGENTS直交圧縮.md",
        "[A5M2_TABLE_OUTPUT]",
        "外部キー(PK)タブ",
        "RDBMS固有情報",
        "SQLソース",
        "[COMPUTE_USE_EVOLUTION]",
        "ComputeUse",
        "Computer Use",
        "[DAILY_COMPOUND_EVOLUTION]",
        "[DESTRUCTIVE_CHANGE_PREFERENCE]",
        "破壊的変更選好",
        "ロールバック方針",
        "CIDLSパイプラインコンセプトイメージ.pngを実現するようにパイプラインコンセプトイメージに基づき複利的自己進化させて",
    ]:
        assert term in text


def test_orthogonal_compression_artifact_is_generated():
    completed = subprocess.run(
        [sys.executable, "scripts/generate_agents_orthogonal_compression.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    text = (ROOT / "AGENTS直交圧縮.md").read_text(encoding="utf-8")
    for term in [
        "PRAY_APP_FACTORY",
        "COMPUTE_USE",
        "CU_EVOLVE",
        "A5M2_TABLE",
        "DESTRUCTIVE",
        "日次10:00",
        "AGENTS要点まとめ.md",
    ]:
        assert term in text


def test_commercial_excel_contains_pray_computeuse_and_a5m2_detail(tmp_path):
    from cidls.commercial_delivery.generator import build_commercial_delivery_package

    package = build_commercial_delivery_package(
        output_dir=tmp_path,
        project_name="CIDLS祈り入力商用アプリ生成",
    )
    text = workbook_text(Path(package["workbook_path"]))

    for term in [
        "祈り入力アプリ工場",
        "ComputeUse自律進化",
        "日次10時複利進化",
        "外部キー(PK)タブ",
        "RDBMS固有情報",
        "SQLソース",
        "OpenAI: Codex for almost everything",
        "AI総合研究所: Codex Computer Use",
    ]:
        assert term in text


def test_daily_automation_runs_at_10_and_contains_compound_prompt():
    text = (
        CODEX_HOME / "automations" / "agents-sw-cycle" / "automation.toml"
    ).read_text(encoding="utf-8")

    assert 'rrule = "FREQ=DAILY;BYHOUR=10;BYMINUTE=0;BYSECOND=0"' in text
    assert "CIDLSパイプラインコンセプトイメージ.pngを実現するようにパイプラインコンセプトイメージに基づき複利的自己進化させて" in text
    assert "ComputeUse" in text
    assert "A5:SQL Mk-2" in text
    assert "AGENTS直交圧縮" in text
    assert "DESTRUCTIVE_CHANGE_PREFERENCE" in text
    assert "破壊的変更" in text
