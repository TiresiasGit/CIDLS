import json
from pathlib import Path
from zipfile import ZipFile

from cidls.commercial_delivery.generator import build_commercial_delivery_package


ROOT = Path(__file__).resolve().parents[1]
CODEX_HOME = Path.home() / ".codex"


REQUIRED_TERMS = [
    "AI-DLC",
    "価値創造ゾーン",
    "問題定義",
    "全体設計",
    "テストとレビュー",
    "WBS",
    "クリティカルパス",
    "プロジェクトバッファ",
    "変更管理",
    "コンテキスト整備",
    "レビュー負荷",
    "意思決定",
    "iframeを使わない",
    "立体構造",
    "過剰な注意力",
    "ユーザーの脳",
    "思想や考えをそのまま文字にしてユーザーに見せない",
    "WebのUIの立体構成で伝える",
    "40年の歴史",
    "温故知新",
    "現行機能維持",
    "コンサルティングアセスメント",
    "将来リスク予測",
    "個人開発アプリ",
    "収益化",
    "ユーザー獲得",
    "課金意思",
    "継続率",
]


CHECK_TARGETS = [
    ROOT / "documents" / "ai-dlc-cidls-integration.md",
    ROOT / "src" / "cidls" / "commercial_delivery" / "generator.py",
    ROOT / "project_kanban.html",
    CODEX_HOME / "automations" / "agents-sw-cycle" / "automation.toml",
    CODEX_HOME / "skills" / "cidls-global-ops" / "SKILL.md",
    CODEX_HOME / "skills" / "cidls-devrag-rag" / "SKILL.md",
    ROOT / "documents" / "consulting-assessment-governance-risk.md",
    ROOT / "graph_project_mindmap.html",
]


def read_text(path):
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def read_workbook_text(path):
    with ZipFile(path) as archive:
        return "\n".join(
            archive.read(name).decode("utf-8")
            for name in archive.namelist()
            if name.endswith(".xml")
        )


def main():
    report = build_commercial_delivery_package(
        output_dir=ROOT / "reports" / "commercial_delivery",
        project_name="CIDLS商用請負納品パッケージ",
    )
    workbook_text = read_workbook_text(Path(report["workbook_path"]))
    target_texts = {str(path): read_text(path) for path in CHECK_TARGETS}
    target_texts[report["workbook_path"]] = workbook_text

    missing = []
    for term in REQUIRED_TERMS:
        if not any(term in text for text in target_texts.values()):
            missing.append(term)

    payload = {
        "ok": not missing,
        "checked_count": len(target_texts),
        "workbook_path": report["workbook_path"],
        "missing": missing,
        "targets": list(target_texts.keys()),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
