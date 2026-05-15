"""
scripts/tile_concept_images.py

コンセプト画像タイル分割スクリプト
------------------------------------
AI が view_image で読み込めないサイズの PNG/JPG を
タイル(分割画像)に切り出し、tiles/ フォルダに保存する。

用途:
  - 圧縮による画質劣化を避けながら、大型コンセプト画像の全体像を把握する
  - 分割後の全タイルを view_image で順番に読み取ることで元画像を再構成できる

仕様:
  - デフォルト分割: 縦2 x 横2 = 4タイル
  - 長辺が 2048px を超える場合: 縦3 x 横3 = 9タイル に自動昇格
  - 長辺が 4096px を超える場合: 縦4 x 横4 = 16タイル に自動昇格
  - 圧縮は行わない (lossless PNG として出力)
  - 出力先: <ROOT>/tiles/<元ファイル名(拡張子なし)>/tile_r{行}_c{列}.png

使用方法:
  python scripts/tile_concept_images.py               # カレントディレクトリの PNG/JPG
  python scripts/tile_concept_images.py --dir refs    # refs/ 配下を対象
  python scripts/tile_concept_images.py --rows 3 --cols 3  # 分割数を明示指定

AGENTS.md [CIDLS_PLATFORM_RESTORE.3] Step0 / [CY] C実行 S0 から自動生成・実行される。
"""

from __future__ import annotations

import argparse
import pathlib
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("[ERROR] Pillow is not installed. Run: uv pip install Pillow")


ROOT = pathlib.Path(__file__).parent.parent


def _auto_grid(width: int, height: int) -> tuple[int, int]:
    """画像サイズに応じて最適な分割数 (rows, cols) を返す。"""
    long_edge = max(width, height)
    if long_edge > 4096:
        return 4, 4
    if long_edge > 2048:
        return 3, 3
    return 2, 2


def tile_image(
    src: pathlib.Path,
    out_dir: pathlib.Path,
    rows: int | None = None,
    cols: int | None = None,
) -> list[pathlib.Path]:
    """1枚の画像をタイルに分割して out_dir に保存する。

    Parameters
    ----------
    src:
        分割対象画像ファイルパス。
    out_dir:
        タイル出力ディレクトリ。存在しない場合は作成する。
    rows, cols:
        分割数。None の場合は画像サイズから自動決定。

    Returns
    -------
    list[pathlib.Path]
        生成されたタイルファイルのパスリスト (左上→右下の読取順)。
    """
    img = Image.open(src)
    w, h = img.size

    r, c = rows or _auto_grid(w, h)[0], cols or _auto_grid(w, h)[1]
    tw, th = w // c, h // r  # tile width / height

    out_dir.mkdir(parents=True, exist_ok=True)
    tiles: list[pathlib.Path] = []

    for ri in range(r):
        for ci in range(c):
            left   = ci * tw
            upper  = ri * th
            right  = left + tw  if ci < c - 1 else w
            lower  = upper + th if ri < r - 1 else h
            tile   = img.crop((left, upper, right, lower))
            out_path = out_dir / f"tile_r{ri}_c{ci}.png"
            tile.save(out_path, format="PNG", optimize=False)
            tiles.append(out_path)
            print(f"  [{ri},{ci}] {out_path.name}  ({right-left}x{lower-upper}px)")

    return tiles


def find_concept_images(directory: pathlib.Path) -> list[pathlib.Path]:
    """ディレクトリ配下の PNG/JPG/JPEG を再帰検索して返す。"""
    exts = {".png", ".jpg", ".jpeg"}
    return sorted(
        p for p in directory.rglob("*")
        if p.suffix.lower() in exts
        and "tiles" not in p.parts  # 既存タイルを対象外にする
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="コンセプト画像をタイル分割して AI 読み取り可能なサイズに分割する"
    )
    parser.add_argument(
        "--dir",
        type=pathlib.Path,
        default=ROOT,
        help="検索対象ディレクトリ (デフォルト: プロジェクトルート)",
    )
    parser.add_argument(
        "--rows", type=int, default=None,
        help="縦方向の分割数 (デフォルト: 自動)",
    )
    parser.add_argument(
        "--cols", type=int, default=None,
        help="横方向の分割数 (デフォルト: 自動)",
    )
    parser.add_argument(
        "--out-base",
        type=pathlib.Path,
        default=ROOT / "tiles",
        help="タイル出力ベースディレクトリ (デフォルト: <ROOT>/tiles)",
    )
    args = parser.parse_args()

    images = find_concept_images(args.dir)
    if not images:
        print(f"[INFO] 対象画像が見つかりませんでした: {args.dir}")
        return

    total_tiles = 0
    for img_path in images:
        print(f"\n[分割] {img_path.name}")
        out_dir = args.out_base / img_path.stem
        tiles = tile_image(img_path, out_dir, rows=args.rows, cols=args.cols)
        total_tiles += len(tiles)
        print(f"  => {len(tiles)} タイルを {out_dir} に保存")

    print(f"\n完了: {len(images)} 画像 / {total_tiles} タイル生成")
    print(f"読取順: 各サブフォルダ内の tile_r0_c0, tile_r0_c1, ... の順に view_image で読み取ること")


if __name__ == "__main__":
    main()
