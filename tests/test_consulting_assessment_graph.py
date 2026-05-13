from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODEX_HOME = Path.home() / ".codex"


def test_consulting_assessment_doc_and_graph_exist():
    doc = ROOT / "documents" / "consulting-assessment-governance-risk.md"
    graph = ROOT / "graph_project_mindmap.html"

    assert doc.exists()
    assert graph.exists()

    doc_text = doc.read_text(encoding="utf-8")
    graph_text = graph.read_text(encoding="utf-8")

    for term in [
        "40年の歴史",
        "温故知新",
        "現行機能維持",
        "ガバナンス",
        "コンプライアンス",
        "セキュリティ",
        "運用負荷",
        "属人性",
        "UX",
        "説明・理解容易性",
        "事実ベース",
        "コンサルティングアセスメント",
        "将来リスク予測",
        "段階的かつ実行可能",
        "今すぐ着手",
    ]:
        assert term in doc_text

    for term in [
        "DA表",
        "スイムレーン",
        "相互連関有向グラフ",
        "階層型グラフマインドマップ",
        "全面刷新に逃げない",
        "管理者低負荷",
        "ユーザー有用性",
    ]:
        assert term in graph_text


def test_indie_app_monetization_feedback_is_reflected():
    targets = [
        ROOT / "documents" / "consulting-assessment-governance-risk.md",
        ROOT / "src" / "cidls" / "commercial_delivery" / "generator.py",
        CODEX_HOME / "skills" / "cidls-global-ops" / "SKILL.md",
        CODEX_HOME / "automations" / "agents-sw-cycle" / "automation.toml",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in targets)

    for term in [
        "個人開発アプリ",
        "収益化",
        "元シリコンバレーCTO",
        "ユーザー獲得",
        "課金意思",
        "オンボーディング",
        "差別化",
        "継続率",
        "解約",
        "価格",
        "分析",
        "ユーザー投資",
        "努力・調査",
        "依存させない",
        "ロックイン禁止",
        "搾取的依存",
        "投資対効果",
    ]:
        assert term in combined
