"""
generate_cidls_platform_overview.py
=====================================
cidls_platform_overview.html のメタデータ(バージョン・日付・成果物ステータス)を
最新状態に自動更新するスクリプト。
CIDLS_PLATFORM_RESTORE.3 Step4 対応。

Usage:
    uv run python scripts/generate_cidls_platform_overview.py
    uv run python scripts/generate_cidls_platform_overview.py --bump-minor
    uv run python scripts/generate_cidls_platform_overview.py --dry-run

依存: 標準ライブラリのみ
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
OVERVIEW_HTML = REPO_ROOT / "cidls_platform_overview.html"
REPORT_HTML = REPO_ROOT / "reports" / "cidls_pipeline_output" / "cidls_platform_overview.html"

TODAY = datetime.now().strftime("%Y-%m-%d")
NOW = datetime.now().strftime("%Y-%m-%d %H:%M")


ARTIFACT_FILES = [
    ("project_kanban.html",       "カンバンボード (SoT)"),
    ("cidls_platform_overview.html", "CIDLSプラットフォーム全体像"),
    ("graph_project_mindmap.html","グラフマインドマップ"),
    ("STORY.html",                "業務ストーリー (6登場人物)"),
    ("要求定義書.html",           "要求定義書 CIDLS-REQ-001"),
    ("コンセプトスライド.html",   "コンセプトスライド [SLIDE]"),
    ("LP.html",                   "販売LP ランディングページ (DISTSEC.3方法1/2)"),
    ("要求要件定義書.html",       "要求要件定義書 CIDLS-REQ-002 (シームレス5種)"),
    ("構成定義書 兼 運用保守手順書.html", "構成定義書兼運用保守手順書 CIDLS-OPS-002 (シームレス5種)"),
    ("テストシナリオ兼結果チェックリスト.html", "テストシナリオ兼結果チェックリスト CIDLS-TEST-001 (シームレス5種)"),
    ("ユーザーマニュアル.html",   "ユーザーマニュアル CIDLS-MAN-001 (シームレス5種)"),
    ("ドキュメント一覧.html",     "ドキュメント一覧 CIDLS-IDX-001 (シームレス5種)"),
]


def read_html(path: Path) -> str:
    if not path.exists():
        print(f"[ERROR] {path} が存在しません")
        sys.exit(1)
    return path.read_text(encoding="utf-8")


def write_html(path: Path, content: str, dry_run: bool = False) -> None:
    size_kb = round(len(content.encode("utf-8")) / 1024, 1)
    if dry_run:
        print(f"[DRY-RUN] {path.name} を更新予定 ({size_kb} KB)")
        return
    path.write_text(content, encoding="utf-8")
    print(f"[SUCCESS] {path.name} を更新しました ({size_kb} KB)")


def parse_version(content: str) -> tuple[int, int, int]:
    """schema vX.Y.Z を解析して (X, Y, Z) を返す"""
    m = re.search(r'schema[_\s]v?(\d+)\.(\d+)\.(\d+)', content, re.IGNORECASE)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    # <meta> タグのバージョン
    m2 = re.search(r'v(\d+)\.(\d+)\.(\d+)', content)
    if m2:
        return int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
    return (2, 2, 0)


def bump_version(content: str, major: bool = False, minor: bool = False, patch: bool = True) -> tuple[str, str]:
    """バージョンを更新して新しいコンテンツと新バージョン文字列を返す"""
    old_v = parse_version(content)
    if major:
        new_v = (old_v[0] + 1, 0, 0)
    elif minor:
        new_v = (old_v[0], old_v[1] + 1, 0)
    else:
        new_v = (old_v[0], old_v[1], old_v[2] + 1)
    old_str = f"v{old_v[0]}.{old_v[1]}.{old_v[2]}"
    new_str = f"v{new_v[0]}.{new_v[1]}.{new_v[2]}"
    updated = content.replace(old_str, new_str)
    print(f"[INFO] バージョン {old_str} -> {new_str}")
    return updated, new_str


def update_dates(content: str) -> str:
    """HTML内の生成日時を今日に更新する"""
    # generated-at パターン
    patterns = [
        (re.compile(r'(generated[_\-]?at["\s:=]+)(\d{4}-\d{2}-\d{2})'), r'\g<1>' + TODAY),
        (re.compile(r'(Generated:\s*)\d{4}-\d{2}-\d{2}'), r'\g<1>' + TODAY),
        (re.compile(r'(更新日時?[:\s]+)\d{4}-\d{2}-\d{2}'), r'\g<1>' + TODAY),
    ]
    for pat, repl in patterns:
        if pat.search(content):
            content = pat.sub(repl, content)
            print(f"[INFO] 日付パターンを {TODAY} に更新しました")
    return content


def check_artifact_status(repo_root: Path) -> list[tuple[str, str, str]]:
    """成果物の存在確認と更新日時を返す"""
    results = []
    for fname, label in ARTIFACT_FILES:
        fpath = repo_root / fname
        if fpath.exists():
            mtime = datetime.fromtimestamp(fpath.stat().st_mtime).strftime("%Y-%m-%d")
            results.append((fname, label, f"exists ({mtime})"))
        else:
            results.append((fname, label, "MISSING"))
    return results


def show_summary(repo_root: Path, content: str) -> None:
    v = parse_version(content)
    print(f"[SUMMARY] cidls_platform_overview.html バージョン: v{v[0]}.{v[1]}.{v[2]}")
    print(f"[SUMMARY] 成果物ステータス:")
    for fname, label, status in check_artifact_status(repo_root):
        icon = "[OK]" if "exists" in status else "[NG]"
        print(f"  {icon} {label}: {status}")


def main() -> None:
    parser = argparse.ArgumentParser(description="cidls_platform_overview.html 自動更新ツール")
    parser.add_argument("--bump-patch", action="store_true", default=True, help="パッチバージョンを上げる (デフォルト)")
    parser.add_argument("--bump-minor", action="store_true", help="マイナーバージョンを上げる")
    parser.add_argument("--bump-major", action="store_true", help="メジャーバージョンを上げる")
    parser.add_argument("--no-bump", action="store_true", help="バージョン更新をスキップ")
    parser.add_argument("--update-date", action="store_true", default=True, help="日付を更新する (デフォルト)")
    parser.add_argument("--sync-report", action="store_true", default=True, help="reports/ ディレクトリに同報する (デフォルト)")
    parser.add_argument("--dry-run", action="store_true", help="変更内容を表示するだけで書き込まない")
    parser.add_argument("--show-summary", action="store_true", help="サマリを表示して終了")
    args = parser.parse_args()

    content = read_html(OVERVIEW_HTML)

    if args.show_summary:
        show_summary(REPO_ROOT, content)
        return

    modified = False

    # バージョン更新
    if not args.no_bump:
        content, new_version = bump_version(
            content,
            major=args.bump_major,
            minor=args.bump_minor,
            patch=(not args.bump_major and not args.bump_minor),
        )
        modified = True

    # 日付更新
    if args.update_date:
        new_content = update_dates(content)
        if new_content != content:
            content = new_content
            modified = True

    if modified or args.dry_run:
        write_html(OVERVIEW_HTML, content, dry_run=args.dry_run)
        # reports/ への同報
        if args.sync_report and REPORT_HTML.parent.exists():
            write_html(REPORT_HTML, content, dry_run=args.dry_run)
            print(f"[INFO] reports/ への同報完了")
    else:
        show_summary(REPO_ROOT, content)
        print("[INFO] 変更なし")


if __name__ == "__main__":
    main()
