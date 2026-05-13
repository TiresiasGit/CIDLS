"""
WinOCR adapter: wraps Windows.Media.OcrEngine via winocr package.
Same OCR engine as Snipping Tool, no GUI automation required.
Install: uv add winocr
"""
import asyncio
import tempfile
import os
from pathlib import Path

from ..exceptions import AdapterActionError, OCRPipelineError
from ..interfaces import OCRAdapter
from ..models import OCRRawResult


class WinOCRUnavailableError(OCRPipelineError):
    pass


def _check_winocr_available():
    try:
        import winocr  # noqa: F401
        return True
    except ImportError:
        return False


def _run_winocr(image_path: str, lang: str) -> str:
    import winocr

    async def _recognize():
        result = await winocr.recognize_from_file(image_path, lang=lang)
        if result is None:
            return ""
        lines = []
        for line in result.lines:
            words = [word.text for word in line.words]
            lines.append(" ".join(words))
        return "\n".join(lines)

    return asyncio.run(_recognize())


class WinOCRAdapter(OCRAdapter):
    """
    Direct Windows OCR API adapter via winocr.
    Does not require GUI automation. Uses Windows.Media.OcrEngine (Win10+).
    Requires: uv add winocr, mss
    """
    name = "winocr"

    def __init__(self, mss_module=None, pil_image_module=None):
        self._mss = mss_module
        self._pil_image = pil_image_module
        self._available: bool | None = None

    def _get_mss(self):
        if self._mss is None:
            import mss
            self._mss = mss
        return self._mss

    def _get_pil_image(self):
        if self._pil_image is None:
            from PIL import Image
            self._pil_image = Image
        return self._pil_image

    def supports(self, capture_request) -> bool:
        return True

    def is_available(self) -> bool:
        if self._available is None:
            self._available = _check_winocr_available()
        return self._available

    def extract(self, capture_request, evidence_run) -> OCRRawResult:
        if not self.is_available():
            raise WinOCRUnavailableError(
                "winocr is not installed. Run: uv add winocr"
            )

        image_path = self._resolve_image_path(capture_request)
        evidence_run.save_capture_image(image_path)

        try:
            lang = self._normalize_lang(capture_request.language_hint)
            raw_text = _run_winocr(image_path, lang)
        except Exception as error:
            raise AdapterActionError(f"WinOCR extraction failed: {error}") from error

        return OCRRawResult(
            adapter_name=self.name,
            raw_text=raw_text,
            capture_image_path=image_path,
            clipboard_text="",
            blocks=[],
            metadata={"lang": lang, "source": capture_request.source_mode},
        )

    def _resolve_image_path(self, capture_request) -> str:
        if capture_request.source_mode == "image_file":
            image_path = capture_request.image_path
            if not image_path or not Path(image_path).exists():
                raise AdapterActionError(f"image_file not found: {image_path}")
            return image_path
        return self._capture_screen_region(capture_request.effective_region())

    def _capture_screen_region(self, region: dict) -> str:
        mss = self._get_mss()
        Image = self._get_pil_image()
        handle, temp_path = tempfile.mkstemp(prefix="cidls_winocr_", suffix=".png")
        os.close(handle)
        monitor = {
            "left": region["left"],
            "top": region["top"],
            "width": region["width"],
            "height": region["height"],
        }
        with mss.mss() as sct:
            screenshot = sct.grab(monitor)
        image = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        image.save(temp_path)
        return temp_path

    @staticmethod
    def _normalize_lang(language_hint: str) -> str:
        mapping = {
            "ja": "ja-JP",
            "ja-jp": "ja-JP",
            "en": "en-US",
            "en-us": "en-US",
            "zh": "zh-Hans-CN",
        }
        normalized = language_hint.strip().lower()
        return mapping.get(normalized, language_hint)
