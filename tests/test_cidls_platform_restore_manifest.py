from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CODEX_HOME = Path.home() / ".codex"


def test_agents_contains_cidls_platform_restore_manifest():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    required_terms = [
        "[CIDLS_PLATFORM_RESTORE]",
        "CIDLSプラットフォーム完全復元マニフェスト",
        "CIDLSパイプラインコンセプトイメージ.png",
        "cidls_platform_overview.html",
        "reports/cidls_pipeline_output/cidls_platform_overview.html",
        "scripts\\generate_cidls_platform_overview.py",
        "scripts\\generate_commercial_delivery_pack.py",
        "scripts\\generate_graph_project_mindmap.py",
        "project_kanban.html",
        "devrag",
        "uv run python -m pytest -q",
        "コンセプト入力",
        "ChatGPTが分析・構造化",
        "v0でアプリ生成・ドキュメント一式生成",
        "v0SaaS ホスティングか、exe出力（アプリ出力）",
        "成果物（納品ドキュメント一式）",
        "システムDA表",
        "PJグラフマインドマップ",
        "コンセプトスライド",
        "画面設計図",
        "画面設計書",
        "画面状態遷移図",
        "注文票",
        "カンバンボード",
        "要求定義書",
        "要求仕様書",
        "システム要件定義書",
        "基本設計書",
        "詳細設計書",
        "DB設計書",
        "外部設計書",
        "結合テスト仕様書",
        "運用設計書",
        "運用手順書",
        "移行計画書",
        "保守運用計画書",
        "リリースノート",
        "Webドキュメント",
        "画像出力",
        "Excel出力",
        "アプリ出力",
        "AI-DLC",
        "Mob Elaboration",
        "quick-cement",
    ]

    for term in required_terms:
        assert term in text


def test_platform_overview_has_restore_manifest_and_no_iframe():
    completed = subprocess.run(
        [sys.executable, "scripts/generate_cidls_platform_overview.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    text = (ROOT / "cidls_platform_overview.html").read_text(encoding="utf-8")

    for term in [
        "AGENTS.md完全復元マニフェスト",
        "scripts/generate_cidls_platform_overview.py",
        "TDD",
        "水平展開",
        "devrag再索引",
        "AGENTS同期",
        "セキュリティ監査",
    ]:
        assert term in text

    assert "<iframe" not in text.lower()


def test_global_codex_surfaces_reference_restore_manifest():
    targets = [
        CODEX_HOME / "skills" / "cidls-global-ops" / "SKILL.md",
        CODEX_HOME / "skills" / "cidls-devrag-rag" / "SKILL.md",
        CODEX_HOME / "automations" / "agents-sw-cycle" / "automation.toml",
    ]

    combined = "\n".join(path.read_text(encoding="utf-8") for path in targets)

    assert "CIDLS_PLATFORM_RESTORE" in combined
    assert "cidls_platform_overview" in combined
    assert "AGENTS.md" in combined
    assert "完全復元" in combined
