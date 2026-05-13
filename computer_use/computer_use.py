"""
computer_use.py
===============
PyAutoGUI + oneocr.dll による Computer Use 実装。

「見る」(スクリーンショット + OCR) と「操作する」(クリック/入力/スクロール)
を単一クラスで提供する。

依存:
  uv add pyautogui pillow pyperclip
  oneocr.dll 系 DLL (ocr_engine.py の README 参照)

使い方:
    from computer_use import ComputerUse

    cu = ComputerUse(dll_dir="path/to/dlls")
    img, text = cu.see()
    print(text)

    if "OK" in text:
        cu.click(500, 300)

    cu.type_text("hello world")
    cu.close()

または with 文:
    with ComputerUse("path/to/dlls") as cu:
        img, text = cu.see()
        cu.click(500, 300)
"""

import time
from pathlib import Path

import pyautogui
import pyperclip
from PIL import Image

from ocr_engine import OneocrEngine
from screen_capture import capture_full, capture_region, save_timestamped


# ---------------------------------------------------------------------------
# 設定定数
# ---------------------------------------------------------------------------

# pyautogui フェイルセーフ: マウスを左上隅に移動で即停止
FAILSAFE = True

# 操作間の最小待機時間 (秒)
OP_PAUSE = 0.1

# マウス移動時間 (秒)
MOVE_DURATION = 0.25


# ---------------------------------------------------------------------------
# Computer Use クラス
# ---------------------------------------------------------------------------

class ComputerUse:
    """
    Windows 11 画面を「見て・操作する」ためのクラス。

    Attributes:
        dll_dir       : oneocr.dll が置かれたディレクトリ
        screenshot_dir: スクリーンショット保存先ディレクトリ
    """

    def __init__(self, dll_dir: str, screenshot_dir: str = "screenshots"):
        """
        Args:
            dll_dir       : oneocr.dll を含むディレクトリ
            screenshot_dir: スクリーンショットの保存先
        """
        self._ocr = OneocrEngine(dll_dir)
        self._screenshot_dir = screenshot_dir

        pyautogui.FAILSAFE = FAILSAFE
        pyautogui.PAUSE = OP_PAUSE

    # ------------------------------------------------------------------
    # 知覚 (Perception)
    # ------------------------------------------------------------------

    def see(self) -> tuple:
        """
        画面全体をキャプチャして OCR を実行する。

        Returns:
            (Image.Image, str): 画像オブジェクトと認識テキスト
        """
        img = capture_full()
        saved = save_timestamped(img, self._screenshot_dir)
        text = self._ocr.recognize_file(str(saved))
        return img, text

    def see_region(self, left: int, top: int, width: int, height: int) -> tuple:
        """
        指定領域をキャプチャして OCR を実行する。

        Args:
            left, top    : 左上座標 (px)
            width, height: サイズ (px)

        Returns:
            (Image.Image, str): 画像オブジェクトと認識テキスト
        """
        img = capture_region(left, top, width, height)
        saved = save_timestamped(img, self._screenshot_dir)
        text = self._ocr.recognize_file(str(saved))
        return img, text

    def see_image(self, img: Image.Image) -> str:
        """
        既存の PIL Image に対して OCR を実行する。

        Args:
            img: PIL Image オブジェクト

        Returns:
            認識テキスト
        """
        return self._ocr.recognize(img)

    # ------------------------------------------------------------------
    # クリック操作
    # ------------------------------------------------------------------

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1):
        """
        座標をクリックする。

        Args:
            x, y   : クリック座標 (px)
            button : "left" | "right" | "middle"
            clicks : クリック回数
        """
        pyautogui.click(x, y, button=button, clicks=clicks)

    def double_click(self, x: int, y: int):
        """座標をダブルクリックする。"""
        pyautogui.doubleClick(x, y)

    def right_click(self, x: int, y: int):
        """座標を右クリックする。"""
        pyautogui.rightClick(x, y)

    def middle_click(self, x: int, y: int):
        """座標をミドルクリックする。"""
        pyautogui.middleClick(x, y)

    # ------------------------------------------------------------------
    # マウス移動
    # ------------------------------------------------------------------

    def move_to(self, x: int, y: int, duration: float = MOVE_DURATION):
        """
        マウスを指定座標に移動する。

        Args:
            x, y    : 移動先座標 (px)
            duration: 移動にかける時間 (秒)
        """
        pyautogui.moveTo(x, y, duration=duration)

    def drag_to(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 0.5,
        button: str = "left",
    ):
        """
        指定座標からドラッグする。

        Args:
            start_x, start_y: ドラッグ開始座標
            end_x, end_y    : ドラッグ終了座標
            duration        : ドラッグ時間 (秒)
            button          : "left" | "right"
        """
        pyautogui.moveTo(start_x, start_y, duration=MOVE_DURATION)
        pyautogui.dragTo(end_x, end_y, duration=duration, button=button)

    # ------------------------------------------------------------------
    # キーボード操作
    # ------------------------------------------------------------------

    def type_text(self, text: str, use_clipboard: bool = True):
        """
        テキストを入力する。

        日本語など ASCII 外の文字はクリップボード経由で貼り付ける。

        Args:
            text          : 入力するテキスト
            use_clipboard : True=クリップボード経由 (日本語対応), False=直接入力
        """
        if use_clipboard:
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
        else:
            pyautogui.typewrite(text, interval=0.05)

    def press(self, *keys: str):
        """
        キーを押す。複数指定でホットキー。

        例:
            cu.press("enter")
            cu.press("ctrl", "c")
            cu.press("alt", "f4")
        """
        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            pyautogui.hotkey(*keys)

    def key_down(self, key: str):
        """キーを押しっぱなしにする。key_up() とペアで使う。"""
        pyautogui.keyDown(key)

    def key_up(self, key: str):
        """key_down() で押したキーを離す。"""
        pyautogui.keyUp(key)

    # ------------------------------------------------------------------
    # スクロール
    # ------------------------------------------------------------------

    def scroll(self, x: int, y: int, clicks: int):
        """
        指定座標でスクロールする。

        Args:
            x, y  : スクロール位置 (px)
            clicks: スクロール量 (正=上方向, 負=下方向)
        """
        pyautogui.scroll(clicks, x=x, y=y)

    # ------------------------------------------------------------------
    # 待機
    # ------------------------------------------------------------------

    def wait(self, seconds: float):
        """指定秒数待機する。"""
        time.sleep(seconds)

    def wait_for_text(
        self,
        target_text: str,
        timeout: float = 10.0,
        interval: float = 0.5,
        region: tuple = None,
    ) -> bool:
        """
        画面上に指定テキストが現れるまで待機する。

        Args:
            target_text: 待機対象のテキスト (部分一致)
            timeout    : 最大待機時間 (秒)
            interval   : チェック間隔 (秒)
            region     : (left, top, width, height) を指定すると領域限定で判定

        Returns:
            True=テキスト検出, False=タイムアウト
        """
        elapsed = 0.0
        while elapsed < timeout:
            if region:
                _, text = self.see_region(*region)
            else:
                _, text = self.see()

            if target_text in text:
                return True

            time.sleep(interval)
            elapsed += interval

        return False

    # ------------------------------------------------------------------
    # 画面情報
    # ------------------------------------------------------------------

    def screen_size(self) -> tuple:
        """スクリーン解像度を (width, height) で返す。"""
        return pyautogui.size()

    def cursor_pos(self) -> tuple:
        """現在のカーソル位置を (x, y) で返す。"""
        return pyautogui.position()

    # ------------------------------------------------------------------
    # ライフタイム管理
    # ------------------------------------------------------------------

    def close(self):
        """OCR エンジンのリソースを解放する。"""
        if hasattr(self, "_ocr") and self._ocr:
            self._ocr.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def __del__(self):
        self.close()


# ---------------------------------------------------------------------------
# 動作確認用のデモ
# ---------------------------------------------------------------------------

def _demo(dll_dir: str):
    """
    ComputerUse の基本動作を確認するデモ。

    1. 画面全体をキャプチャして OCR
    2. 結果を表示
    3. 現在のマウス位置を表示
    """
    print("[PROCESS_START] computer_use demo")

    with ComputerUse(dll_dir) as cu:
        w, h = cu.screen_size()
        print(f"[INFO] screen size = {w}x{h}")

        print("[STEP] 画面全体をキャプチャして OCR ...")
        img, text = cu.see()
        print(f"[INFO] image size = {img.size}")
        print(f"[INFO] OCR text (先頭200字):\n{text[:200]}")

        cx, cy = cu.cursor_pos()
        print(f"[INFO] cursor pos = ({cx}, {cy})")

    print("[PROCESS_END] demo completed")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python computer_use.py <dll_dir>")
        sys.exit(1)

    _demo(sys.argv[1])
