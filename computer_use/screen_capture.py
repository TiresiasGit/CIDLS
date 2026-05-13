"""
screen_capture.py
=================
PyAutoGUI + mss を使ったスクリーンキャプチャモジュール。

対応パターン:
  1. 全画面キャプチャ -> PIL Image
  2. 領域指定キャプチャ -> PIL Image
  3. タイムスタンプ付きファイル保存

依存:
  uv add pyautogui pillow mss pyperclip
"""

import os
from datetime import datetime
from pathlib import Path

import pyautogui
from PIL import Image


# ---------------------------------------------------------------------------
# キャプチャ
# ---------------------------------------------------------------------------

def capture_full() -> Image.Image:
    """画面全体をキャプチャして PIL Image を返す。"""
    return pyautogui.screenshot()


def capture_region(left: int, top: int, width: int, height: int) -> Image.Image:
    """
    指定領域をキャプチャして PIL Image を返す。

    Args:
        left  : 左端 X 座標 (px)
        top   : 上端 Y 座標 (px)
        width : 幅 (px)
        height: 高さ (px)
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"width/height は正の値が必要です: ({width}, {height})")
    return pyautogui.screenshot(region=(left, top, width, height))


# ---------------------------------------------------------------------------
# 保存
# ---------------------------------------------------------------------------

def save_timestamped(img: Image.Image, save_dir: str = "screenshots") -> Path:
    """
    タイムスタンプ付きファイル名で PNG 保存する。

    Args:
        img     : 保存する PIL Image
        save_dir: 保存ディレクトリ（存在しなければ作成）

    Returns:
        保存先の Path オブジェクト
    """
    dir_path = Path(save_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filepath = dir_path / f"screen_{ts}.png"
    img.save(str(filepath))
    return filepath


def save_to_path(img: Image.Image, filepath: str) -> Path:
    """
    指定パスに PNG 保存する（既存ファイルは上書き）。

    Args:
        img     : 保存する PIL Image
        filepath: 保存先パス

    Returns:
        保存先の Path オブジェクト
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path))
    return path


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def screen_size() -> tuple:
    """現在のスクリーン解像度を (width, height) で返す。"""
    return pyautogui.size()


# ---------------------------------------------------------------------------
# CLI 簡易確認
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"[INFO] screen size = {screen_size()}")

    img = capture_full()
    p = save_timestamped(img, "screenshots")
    print(f"[INFO] full capture saved -> {p}")

    img_r = capture_region(0, 0, 400, 300)
    p_r = save_timestamped(img_r, "screenshots")
    print(f"[INFO] region capture saved -> {p_r}")
