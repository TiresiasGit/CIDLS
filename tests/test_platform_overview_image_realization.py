from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_platform_overview_html_realizes_attached_image_flow():
    completed = subprocess.run(
        [sys.executable, "scripts/generate_cidls_platform_overview.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    html = (ROOT / "cidls_platform_overview.html").read_text(encoding="utf-8")
    report_html = (
        ROOT / "reports" / "cidls_pipeline_output" / "cidls_platform_overview.html"
    ).read_text(encoding="utf-8")

    for text in [html, report_html]:
        assert "CIDLS プラットフォーム全体像" in text
        assert "コンセプト入力" in text
        assert "ChatGPTが分析・構造化" in text
        assert "v0でアプリ生成・ドキュメント一式生成" in text
        assert "v0ビルダー（生成環境）" in text
        assert "SaaSホスティング" in text
        assert "v0SaaS ホスティングか、exe出力（アプリ出力）" in text
        assert "exe出力" in text
        assert "成果物ドキュメント一覧" in text
        assert "システムDA表" in text
        assert "PJグラフマインドマップ" in text
        assert "コンセプトスライド" in text
        assert "画面設計書" in text
        assert "注文票" in text
        assert "カンバンボード" in text
        assert "要求定義書" in text
        assert "DB設計書" in text
        assert "Excel出力" in text
        assert "AI-DLC" in text
        assert "Mob Elaboration" in text
        assert "AGENTS.md完全復元マニフェスト" in text
        assert "scripts/generate_cidls_platform_overview.py" in text
        assert "<iframe" not in text.lower()


def test_ai_dlc_document_contains_findy_specific_operational_points():
    text = (ROOT / "documents" / "ai-dlc-cidls-integration.md").read_text(
        encoding="utf-8"
    )

    for term in [
        "AI-Assisted",
        "AI-Driven",
        "10の設計原則",
        "Mob Elaboration",
        "Inception",
        "Construction",
        "Operation",
        "quick-cement",
        "レビュー疲れ",
        "認知負荷",
    ]:
        assert term in text
