"""
generate_graph_project_mindmap.py
==================================
DA表エントリの追加 + マインドマップノードの更新を行うスクリプト。
CIDLS_PLATFORM_RESTORE.3 Step6 対応。

Usage:
    uv run python scripts/generate_graph_project_mindmap.py
    uv run python scripts/generate_graph_project_mindmap.py --add-entry
    uv run python scripts/generate_graph_project_mindmap.py --cycle N --summary "説明"

依存: 標準ライブラリのみ (外部パッケージ不要)
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
MINDMAP_HTML = REPO_ROOT / "graph_project_mindmap.html"

TODAY = datetime.now().strftime("%Y-%m-%d")


def read_html() -> str:
    if not MINDMAP_HTML.exists():
        print(f"[ERROR] {MINDMAP_HTML} が存在しません")
        sys.exit(1)
    return MINDMAP_HTML.read_text(encoding="utf-8")


def write_html(content: str) -> None:
    MINDMAP_HTML.write_text(content, encoding="utf-8")
    size_kb = round(len(content.encode("utf-8")) / 1024, 1)
    print(f"[SUCCESS] {MINDMAP_HTML.name} を更新しました ({size_kb} KB)")


def get_next_da_id(content: str) -> str:
    ids = re.findall(r'<td>DA-(\d{3})</td>', content)
    if not ids:
        return "DA-001"
    max_id = max(int(x) for x in ids)
    return f"DA-{max_id + 1:03d}"


def add_da_entry(
    content: str,
    cycle: int,
    summary: str,
    axis: str = "軸1 機能維持",
    source: str = "",
    priority: str = "P1",
) -> str:
    """DA表の末尾行の後に新エントリを挿入する"""
    da_id = get_next_da_id(content)
    source_text = source or f"CAPDkAサイクル実行 {TODAY} 第{cycle}回"
    new_row = (
        f'      <tr><td>{da_id}</td>'
        f'<td><span class="tag-f">F</span></td>'
        f'<td>{axis}</td>'
        f'<td>[DONE {TODAY}] {summary}</td>'
        f'<td>{source_text}</td>'
        f'<td>{priority}</td></tr>'
    )
    # 挿入: </tbody> の直前
    if '</tbody>' not in content:
        print("[WARN] </tbody> が見つかりません。末尾へ追記します。")
        return content + "\n" + new_row
    updated = content.replace(
        '    </tbody>\n  </table>',
        f'{new_row}\n    </tbody>\n  </table>',
        1,
    )
    print(f"[INFO] {da_id} エントリを追加しました")
    return updated


def update_mindmap_node_detail(content: str, node_name: str, new_detail: str) -> str:
    """マインドマップの特定ノードの detail を更新する"""
    pattern = re.compile(
        r"(\{ name: '" + re.escape(node_name) + r"'[^}]*detail: ')[^']*(')",
        re.DOTALL,
    )
    if not pattern.search(content):
        print(f"[WARN] ノード '{node_name}' が見つかりません。スキップします。")
        return content
    updated = pattern.sub(r"\g<1>" + new_detail + r"\g<2>", content, count=1)
    print(f"[INFO] ノード '{node_name}' の detail を更新しました")
    return updated


def update_header_date(content: str) -> str:
    """ヘッダーの last-updated 日付を今日に更新する"""
    pattern = re.compile(r'(Last Updated:?\s*)\d{4}-\d{2}-\d{2}')
    if pattern.search(content):
        updated = pattern.sub(r'\g<1>' + TODAY, content)
        print(f"[INFO] ヘッダー日付を {TODAY} に更新しました")
        return updated
    return content


def show_summary(content: str) -> None:
    """DA表のサマリを表示する"""
    ids = re.findall(r'<td>(DA-\d{3})</td>', content)
    done = len(re.findall(r'\[DONE', content))
    blocked = len(re.findall(r'\[BLOCKED', content))
    print(f"[SUMMARY] DA表: {len(ids)} 件 / DONE={done} / BLOCKED={blocked}")
    if ids:
        print(f"[SUMMARY] 最新ID: {ids[-1]}")
    nodes = re.findall(r"name: '([^']+)'", content)
    print(f"[SUMMARY] マインドマップノード数: {len(nodes)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="CIDLS graph_project_mindmap.html 更新ツール")
    parser.add_argument("--add-entry", action="store_true", help="DA表に新エントリを追加する")
    parser.add_argument("--cycle", type=int, default=0, help="CAPDkAサイクル回数")
    parser.add_argument("--summary", type=str, default="", help="DA表エントリの概要")
    parser.add_argument("--axis", type=str, default="軸1 機能維持", help="DA表の軸 (例: 軸2 運用持続)")
    parser.add_argument("--priority", type=str, default="P1", help="優先度 (P1/P2/P3)")
    parser.add_argument("--update-date", action="store_true", help="ヘッダー日付を今日に更新する")
    parser.add_argument("--show-summary", action="store_true", help="DA表サマリを表示して終了")
    args = parser.parse_args()

    content = read_html()

    if args.show_summary:
        show_summary(content)
        return

    modified = False

    if args.add_entry:
        if not args.summary:
            print("[ERROR] --summary オプションが必要です")
            sys.exit(1)
        content = add_da_entry(
            content,
            cycle=args.cycle,
            summary=args.summary,
            axis=args.axis,
            priority=args.priority,
        )
        modified = True

    if args.update_date:
        content = update_header_date(content)
        modified = True

    if modified:
        write_html(content)
    else:
        show_summary(content)
        print("[INFO] 変更なし。--add-entry / --update-date を指定してください。")


if __name__ == "__main__":
    main()
