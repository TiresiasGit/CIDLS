"""
ocr_engine.py
=============
Windows 11 Snipping Tool の oneocr.dll を使った OCR エンジンラッパー。

必要ファイル (DLL_DIR に配置):
  oneocr.dll      Windows 11 最新 Snipping Tool から抽出
  OcrEngine.dll   同上 (依存 DLL)
  onnxruntime.dll 同上 (依存 DLL)

取得方法:
  最新の Snipping Tool (Microsoft Store 版) のインストールディレクトリから
  または rg-adguard 等の msixbundle ダウンローダーで取得する。

API 仕様 (コミュニティ調査によるリバースエンジニアリング結果):
  - OcrEngineCreate(lang: LPCWSTR) -> HANDLE
      lang: NULL=自動検出, "ja"=日本語, "en-US"=英語
  - OcrEngineProcess(engine, bgra_data, width, height, stride) -> RESULT*
      bgra_data: BGRA 形式のピクセルバイト列
      stride   : width * 4 (BGRA の場合)
  - OcrEngineGetText(result) -> LPCWSTR
  - OcrEngineDestroyResult(result) -> void
  - OcrEngineDestroy(engine) -> void

注意:
  本 API は非公開 (Microsoft 非公式) のため、Snipping Tool の更新で
  関数シグネチャが変わる可能性があります。
  動作確認済みバージョン: Snipping Tool 11.2405.x 系

参考:
  github.com/SionoiS/oneocr-python
"""

import ctypes
import os
from pathlib import Path

from PIL import Image


# ---------------------------------------------------------------------------
# カスタム例外
# ---------------------------------------------------------------------------

class OneocrInitError(RuntimeError):
    """DLL 初期化失敗"""


class OneocrProcessError(RuntimeError):
    """OCR 処理失敗"""


# ---------------------------------------------------------------------------
# エンジン
# ---------------------------------------------------------------------------

class OneocrEngine:
    """
    oneocr.dll を ctypes 経由で呼び出す OCR エンジン。

    使い方:
        engine = OneocrEngine(dll_dir="path/to/dlls")
        text = engine.recognize(pil_image)
        engine.close()

    または with 文で:
        with OneocrEngine("path/to/dlls") as engine:
            text = engine.recognize(pil_image)
    """

    def __init__(self, dll_dir: str, lang: str = None):
        """
        Args:
            dll_dir: oneocr.dll が置かれたディレクトリ
            lang   : 認識言語タグ (None=自動, "ja", "en-US" など)
        """
        self._dll_dir = Path(dll_dir).resolve()
        dll_path = self._dll_dir / "oneocr.dll"

        if not dll_path.exists():
            raise FileNotFoundError(
                f"oneocr.dll が見つかりません: {dll_path}\n"
                "Snipping Tool から oneocr.dll / OcrEngine.dll / onnxruntime.dll を取得してください。"
            )

        # 依存 DLL を同ディレクトリから解決するため add_dll_directory を使用
        # (os.add_dll_directory は Python 3.8+ / Windows 専用)
        os.add_dll_directory(str(self._dll_dir))
        self._lib = ctypes.CDLL(str(dll_path))
        self._setup_api()

        lang_ptr = lang  # None を渡すと自動検出
        self._handle = self._lib.OcrEngineCreate(lang_ptr)
        if not self._handle:
            raise OneocrInitError(
                f"OcrEngineCreate が失敗しました (lang={lang!r})\n"
                "DLL ファイルが正しいか、対応バージョンかを確認してください。"
            )

    # ------------------------------------------------------------------
    # API セットアップ
    # ------------------------------------------------------------------

    def _setup_api(self):
        lib = self._lib

        # OcrEngineCreate(lang: LPCWSTR) -> void*
        lib.OcrEngineCreate.restype = ctypes.c_void_p
        lib.OcrEngineCreate.argtypes = [ctypes.c_wchar_p]

        # OcrEngineProcess(engine, bgra, width, height, stride) -> void*
        lib.OcrEngineProcess.restype = ctypes.c_void_p
        lib.OcrEngineProcess.argtypes = [
            ctypes.c_void_p,  # engine handle
            ctypes.c_char_p,  # BGRA pixel bytes
            ctypes.c_uint32,  # width
            ctypes.c_uint32,  # height
            ctypes.c_uint32,  # stride (= width * 4)
        ]

        # OcrEngineGetText(result) -> LPCWSTR
        lib.OcrEngineGetText.restype = ctypes.c_wchar_p
        lib.OcrEngineGetText.argtypes = [ctypes.c_void_p]

        # OcrEngineDestroyResult(result) -> void
        lib.OcrEngineDestroyResult.restype = None
        lib.OcrEngineDestroyResult.argtypes = [ctypes.c_void_p]

        # OcrEngineDestroy(engine) -> void
        lib.OcrEngineDestroy.restype = None
        lib.OcrEngineDestroy.argtypes = [ctypes.c_void_p]

    # ------------------------------------------------------------------
    # 認識
    # ------------------------------------------------------------------

    def recognize(self, img: Image.Image) -> str:
        """
        PIL Image からテキストを抽出する。

        Args:
            img: 任意モードの PIL Image (内部で BGRA に変換)

        Returns:
            認識結果テキスト (改行区切り)

        Raises:
            OneocrProcessError: OCR 処理に失敗した場合
        """
        bgra = self._to_bgra(img)
        width, height = bgra.size
        stride = width * 4  # BGRA = 4 bytes/pixel
        pixel_bytes = bgra.tobytes()

        result_ptr = self._lib.OcrEngineProcess(
            self._handle,
            pixel_bytes,
            ctypes.c_uint32(width),
            ctypes.c_uint32(height),
            ctypes.c_uint32(stride),
        )
        if not result_ptr:
            raise OneocrProcessError("OcrEngineProcess が NULL を返しました")

        text = self._lib.OcrEngineGetText(result_ptr)
        if text is None:
            self._lib.OcrEngineDestroyResult(result_ptr)
            raise OneocrProcessError("OcrEngineGetText が NULL を返しました")

        result_text = str(text)  # LPCWSTR -> Python str
        self._lib.OcrEngineDestroyResult(result_ptr)
        return result_text

    def recognize_file(self, image_path: str) -> str:
        """
        画像ファイルパスからテキストを抽出する。

        Args:
            image_path: PNG / JPEG 等の画像ファイルパス

        Returns:
            認識結果テキスト
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"画像ファイルが見つかりません: {path}")
        img = Image.open(str(path))
        return self.recognize(img)

    # ------------------------------------------------------------------
    # 内部ユーティリティ
    # ------------------------------------------------------------------

    @staticmethod
    def _to_bgra(img: Image.Image) -> Image.Image:
        """PIL Image を BGRA 形式に変換する。"""
        rgba = img.convert("RGBA")
        r, g, b, a = rgba.split()
        return Image.merge("RGBA", (b, g, r, a))

    # ------------------------------------------------------------------
    # ライフタイム管理
    # ------------------------------------------------------------------

    def close(self):
        """エンジンリソースを解放する。"""
        if getattr(self, "_handle", None) and getattr(self, "_lib", None):
            self._lib.OcrEngineDestroy(self._handle)
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def __del__(self):
        self.close()


# ---------------------------------------------------------------------------
# CLI 簡易確認
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python ocr_engine.py <dll_dir> <image_path>")
        sys.exit(1)

    dll_dir_arg = sys.argv[1]
    image_path_arg = sys.argv[2]

    with OneocrEngine(dll_dir_arg) as eng:
        result = eng.recognize_file(image_path_arg)
        print("[OCR RESULT]")
        print(result)
