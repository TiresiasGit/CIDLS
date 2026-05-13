"""
Integration tests for WinOCRAdapter.

Covers:
- is_available returns bool
- extract with winocr unavailable raises WinOCRUnavailableError
- extract with image_file mode calls _run_winocr with correct path
- extract with missing image_file raises AdapterActionError
- _normalize_lang maps "ja" -> "ja-JP", "en" -> "en-US", passthrough unknown
- supports() always returns True
- _capture_screen_region uses mss and PIL correctly
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from cidls.ocr_pipeline.adapters.winocr_adapter import WinOCRAdapter, WinOCRUnavailableError
from cidls.ocr_pipeline.exceptions import AdapterActionError
from cidls.ocr_pipeline.models import CaptureRequest, OCRRawResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_image_request(tmp_path) -> CaptureRequest:
    """Return a CaptureRequest in image_file mode pointing to a real PNG file."""
    img = tmp_path / "test_capture.png"
    img.write_bytes(
        bytes.fromhex(
            "89504E470D0A1A0A0000000D4948445200000001000000010802000000907753DE"
            "0000000C4944415408D763F8FFFF3F0005FE02FEA7A69D5B0000000049454E44AE426082"
        )
    )
    return CaptureRequest(
        source_mode="image_file",
        image_path=str(img),
        language_hint="ja-JP",
        idempotency_key="winocr-test",
    )


def _make_region_request() -> CaptureRequest:
    return CaptureRequest(
        source_mode="screen_region",
        region={"left": 0, "top": 0, "width": 100, "height": 50},
        language_hint="ja-JP",
        idempotency_key="winocr-region-test",
    )


class FakeEvidenceRun:
    def __init__(self):
        self.saved_capture = None
        self.saved_failure = None

    def save_capture_image(self, path: str):
        self.saved_capture = path

    def save_failure_screenshot(self, path: str):
        self.saved_failure = path


# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------

class TestIsAvailable:
    def test_returns_bool_when_available(self):
        adapter = WinOCRAdapter()
        with patch(
            "cidls.ocr_pipeline.adapters.winocr_adapter._check_winocr_available",
            return_value=True,
        ):
            adapter._available = None
            result = adapter.is_available()
        assert isinstance(result, bool)
        assert result is True

    def test_returns_bool_when_unavailable(self):
        adapter = WinOCRAdapter()
        with patch(
            "cidls.ocr_pipeline.adapters.winocr_adapter._check_winocr_available",
            return_value=False,
        ):
            adapter._available = None
            result = adapter.is_available()
        assert isinstance(result, bool)
        assert result is False

    def test_result_is_cached(self):
        adapter = WinOCRAdapter()
        with patch(
            "cidls.ocr_pipeline.adapters.winocr_adapter._check_winocr_available",
            return_value=True,
        ) as mock_check:
            adapter._available = None
            adapter.is_available()
            adapter.is_available()
            # Second call uses cached value; _check_winocr_available called only once
            mock_check.assert_called_once()

    def test_cached_false_not_rechecked(self):
        adapter = WinOCRAdapter()
        adapter._available = False
        with patch(
            "cidls.ocr_pipeline.adapters.winocr_adapter._check_winocr_available",
        ) as mock_check:
            result = adapter.is_available()
            mock_check.assert_not_called()
        assert result is False


# ---------------------------------------------------------------------------
# supports()
# ---------------------------------------------------------------------------

class TestSupports:
    def test_supports_always_returns_true_for_image_file(self, tmp_path):
        adapter = WinOCRAdapter()
        request = _make_image_request(tmp_path)
        assert adapter.supports(request) is True

    def test_supports_always_returns_true_for_screen_region(self):
        adapter = WinOCRAdapter()
        request = _make_region_request()
        assert adapter.supports(request) is True

    def test_supports_returns_bool(self, tmp_path):
        adapter = WinOCRAdapter()
        request = _make_image_request(tmp_path)
        result = adapter.supports(request)
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# extract: unavailable winocr
# ---------------------------------------------------------------------------

class TestExtractUnavailable:
    def test_raises_winocr_unavailable_error(self, tmp_path):
        adapter = WinOCRAdapter()
        request = _make_image_request(tmp_path)
        evidence = FakeEvidenceRun()
        with patch(
            "cidls.ocr_pipeline.adapters.winocr_adapter._check_winocr_available",
            return_value=False,
        ):
            adapter._available = None
            with pytest.raises(WinOCRUnavailableError):
                adapter.extract(request, evidence)

    def test_error_message_mentions_uv_add(self, tmp_path):
        adapter = WinOCRAdapter()
        request = _make_image_request(tmp_path)
        evidence = FakeEvidenceRun()
        with patch(
            "cidls.ocr_pipeline.adapters.winocr_adapter._check_winocr_available",
            return_value=False,
        ):
            adapter._available = None
            with pytest.raises(WinOCRUnavailableError, match="uv add winocr"):
                adapter.extract(request, evidence)


# ---------------------------------------------------------------------------
# extract: image_file mode
# ---------------------------------------------------------------------------

class TestExtractImageFile:
    def test_calls_run_winocr_with_correct_path(self, tmp_path):
        adapter = WinOCRAdapter()
        request = _make_image_request(tmp_path)
        evidence = FakeEvidenceRun()

        with patch(
            "cidls.ocr_pipeline.adapters.winocr_adapter._check_winocr_available",
            return_value=True,
        ):
            adapter._available = None
            with patch(
                "cidls.ocr_pipeline.adapters.winocr_adapter._run_winocr",
                return_value="extracted text",
            ) as mock_run:
                result = adapter.extract(request, evidence)
                mock_run.assert_called_once_with(request.image_path, "ja-JP")

    def test_returns_ocr_raw_result(self, tmp_path):
        adapter = WinOCRAdapter()
        request = _make_image_request(tmp_path)
        evidence = FakeEvidenceRun()

        with patch(
            "cidls.ocr_pipeline.adapters.winocr_adapter._check_winocr_available",
            return_value=True,
        ):
            adapter._available = None
            with patch(
                "cidls.ocr_pipeline.adapters.winocr_adapter._run_winocr",
                return_value="氏名: 山田",
            ):
                result = adapter.extract(request, evidence)

        assert isinstance(result, OCRRawResult)

    def test_result_adapter_name_is_winocr(self, tmp_path):
        adapter = WinOCRAdapter()
        request = _make_image_request(tmp_path)
        evidence = FakeEvidenceRun()

        with patch(
            "cidls.ocr_pipeline.adapters.winocr_adapter._check_winocr_available",
            return_value=True,
        ):
            adapter._available = None
            with patch(
                "cidls.ocr_pipeline.adapters.winocr_adapter._run_winocr",
                return_value="text",
            ):
                result = adapter.extract(request, evidence)

        assert result.adapter_name == "winocr"

    def test_result_raw_text_matches_run_winocr_output(self, tmp_path):
        adapter = WinOCRAdapter()
        request = _make_image_request(tmp_path)
        evidence = FakeEvidenceRun()

        with patch(
            "cidls.ocr_pipeline.adapters.winocr_adapter._check_winocr_available",
            return_value=True,
        ):
            adapter._available = None
            with patch(
                "cidls.ocr_pipeline.adapters.winocr_adapter._run_winocr",
                return_value="氏名: 山田 花子",
            ):
                result = adapter.extract(request, evidence)

        assert result.raw_text == "氏名: 山田 花子"

    def test_evidence_run_save_capture_image_called(self, tmp_path):
        adapter = WinOCRAdapter()
        request = _make_image_request(tmp_path)
        evidence = FakeEvidenceRun()

        with patch(
            "cidls.ocr_pipeline.adapters.winocr_adapter._check_winocr_available",
            return_value=True,
        ):
            adapter._available = None
            with patch(
                "cidls.ocr_pipeline.adapters.winocr_adapter._run_winocr",
                return_value="text",
            ):
                adapter.extract(request, evidence)

        assert evidence.saved_capture is not None

    def test_run_winocr_exception_raises_adapter_action_error(self, tmp_path):
        adapter = WinOCRAdapter()
        request = _make_image_request(tmp_path)
        evidence = FakeEvidenceRun()

        with patch(
            "cidls.ocr_pipeline.adapters.winocr_adapter._check_winocr_available",
            return_value=True,
        ):
            adapter._available = None
            with patch(
                "cidls.ocr_pipeline.adapters.winocr_adapter._run_winocr",
                side_effect=RuntimeError("engine failure"),
            ):
                with pytest.raises(AdapterActionError):
                    adapter.extract(request, evidence)


# ---------------------------------------------------------------------------
# extract: missing image_file raises AdapterActionError
# ---------------------------------------------------------------------------

class TestExtractMissingImageFile:
    def test_missing_image_raises_adapter_action_error(self, tmp_path):
        # Create request with image_path that no longer exists
        img = tmp_path / "gone.png"
        img.write_bytes(b"fake")
        request = CaptureRequest(
            source_mode="image_file",
            image_path=str(img),
            language_hint="ja-JP",
            idempotency_key="missing-file-test",
        )
        img.unlink()  # Delete after request creation

        adapter = WinOCRAdapter()
        evidence = FakeEvidenceRun()

        with patch(
            "cidls.ocr_pipeline.adapters.winocr_adapter._check_winocr_available",
            return_value=True,
        ):
            adapter._available = None
            with pytest.raises(AdapterActionError):
                adapter.extract(request, evidence)

    def test_empty_image_path_raises_adapter_action_error(self, tmp_path):
        # We need a valid path for CaptureRequest construction, then override it
        img = tmp_path / "placeholder.png"
        img.write_bytes(b"fake")
        request = CaptureRequest(
            source_mode="image_file",
            image_path=str(img),
            language_hint="ja-JP",
            idempotency_key="empty-path-test",
        )
        # Override image_path to empty after construction bypasses validate()
        request.image_path = ""

        adapter = WinOCRAdapter()
        evidence = FakeEvidenceRun()

        with patch(
            "cidls.ocr_pipeline.adapters.winocr_adapter._check_winocr_available",
            return_value=True,
        ):
            adapter._available = None
            with pytest.raises(AdapterActionError):
                adapter.extract(request, evidence)


# ---------------------------------------------------------------------------
# _normalize_lang
# ---------------------------------------------------------------------------

class TestNormalizeLang:
    def test_ja_maps_to_ja_jp(self):
        assert WinOCRAdapter._normalize_lang("ja") == "ja-JP"

    def test_ja_jp_lowercase_maps_to_ja_jp(self):
        assert WinOCRAdapter._normalize_lang("ja-jp") == "ja-JP"

    def test_ja_jp_uppercase_maps_to_ja_jp(self):
        assert WinOCRAdapter._normalize_lang("ja-JP") == "ja-JP"

    def test_en_maps_to_en_us(self):
        assert WinOCRAdapter._normalize_lang("en") == "en-US"

    def test_en_us_lowercase_maps_to_en_us(self):
        assert WinOCRAdapter._normalize_lang("en-us") == "en-US"

    def test_en_us_uppercase_passthrough_via_mapping(self):
        assert WinOCRAdapter._normalize_lang("en-US") == "en-US"

    def test_zh_maps_to_zh_hans_cn(self):
        assert WinOCRAdapter._normalize_lang("zh") == "zh-Hans-CN"

    def test_unknown_lang_passthrough(self):
        assert WinOCRAdapter._normalize_lang("fr-FR") == "fr-FR"

    def test_unknown_short_lang_passthrough(self):
        assert WinOCRAdapter._normalize_lang("ko") == "ko"

    def test_strips_whitespace(self):
        result = WinOCRAdapter._normalize_lang("  ja  ")
        assert result == "ja-JP"

    def test_return_type_is_string(self):
        result = WinOCRAdapter._normalize_lang("en")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _capture_screen_region
# ---------------------------------------------------------------------------

class TestCaptureScreenRegion:
    def test_uses_mss_to_grab_region(self):
        mock_mss_module = MagicMock()
        mock_sct = MagicMock()
        mock_screenshot = MagicMock()
        mock_screenshot.size = (100, 50)
        mock_screenshot.bgra = b"\x00" * (100 * 50 * 4)
        mock_sct.grab.return_value = mock_screenshot
        mock_mss_module.mss.return_value.__enter__ = MagicMock(return_value=mock_sct)
        mock_mss_module.mss.return_value.__exit__ = MagicMock(return_value=False)

        mock_image_module = MagicMock()
        mock_image_instance = MagicMock()
        mock_image_module.frombytes.return_value = mock_image_instance

        adapter = WinOCRAdapter(mss_module=mock_mss_module, pil_image_module=mock_image_module)
        region = {"left": 10, "top": 20, "width": 100, "height": 50}

        result = adapter._capture_screen_region(region)

        mock_sct.grab.assert_called_once()
        grab_arg = mock_sct.grab.call_args[0][0]
        assert grab_arg["left"] == 10
        assert grab_arg["top"] == 20
        assert grab_arg["width"] == 100
        assert grab_arg["height"] == 50

    def test_uses_pil_frombytes(self):
        mock_mss_module = MagicMock()
        mock_sct = MagicMock()
        mock_screenshot = MagicMock()
        mock_screenshot.size = (200, 100)
        mock_screenshot.bgra = b"\x00" * (200 * 100 * 4)
        mock_sct.grab.return_value = mock_screenshot
        mock_mss_module.mss.return_value.__enter__ = MagicMock(return_value=mock_sct)
        mock_mss_module.mss.return_value.__exit__ = MagicMock(return_value=False)

        mock_image_module = MagicMock()
        mock_image_instance = MagicMock()
        mock_image_module.frombytes.return_value = mock_image_instance

        adapter = WinOCRAdapter(mss_module=mock_mss_module, pil_image_module=mock_image_module)
        region = {"left": 0, "top": 0, "width": 200, "height": 100}
        adapter._capture_screen_region(region)

        mock_image_module.frombytes.assert_called_once_with(
            "RGB", mock_screenshot.size, mock_screenshot.bgra, "raw", "BGRX"
        )

    def test_saves_image_to_temp_file(self):
        mock_mss_module = MagicMock()
        mock_sct = MagicMock()
        mock_screenshot = MagicMock()
        mock_screenshot.size = (100, 50)
        mock_screenshot.bgra = b"\x00" * (100 * 50 * 4)
        mock_sct.grab.return_value = mock_screenshot
        mock_mss_module.mss.return_value.__enter__ = MagicMock(return_value=mock_sct)
        mock_mss_module.mss.return_value.__exit__ = MagicMock(return_value=False)

        mock_image_module = MagicMock()
        mock_image_instance = MagicMock()
        mock_image_module.frombytes.return_value = mock_image_instance

        adapter = WinOCRAdapter(mss_module=mock_mss_module, pil_image_module=mock_image_module)
        region = {"left": 0, "top": 0, "width": 100, "height": 50}
        result_path = adapter._capture_screen_region(region)

        mock_image_instance.save.assert_called_once_with(result_path)

    def test_returns_string_path(self):
        mock_mss_module = MagicMock()
        mock_sct = MagicMock()
        mock_screenshot = MagicMock()
        mock_screenshot.size = (100, 50)
        mock_screenshot.bgra = b"\x00" * (100 * 50 * 4)
        mock_sct.grab.return_value = mock_screenshot
        mock_mss_module.mss.return_value.__enter__ = MagicMock(return_value=mock_sct)
        mock_mss_module.mss.return_value.__exit__ = MagicMock(return_value=False)

        mock_image_module = MagicMock()
        mock_image_module.frombytes.return_value = MagicMock()

        adapter = WinOCRAdapter(mss_module=mock_mss_module, pil_image_module=mock_image_module)
        region = {"left": 0, "top": 0, "width": 100, "height": 50}
        result = adapter._capture_screen_region(region)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_temp_file_has_png_suffix(self):
        mock_mss_module = MagicMock()
        mock_sct = MagicMock()
        mock_screenshot = MagicMock()
        mock_screenshot.size = (100, 50)
        mock_screenshot.bgra = b"\x00" * (100 * 50 * 4)
        mock_sct.grab.return_value = mock_screenshot
        mock_mss_module.mss.return_value.__enter__ = MagicMock(return_value=mock_sct)
        mock_mss_module.mss.return_value.__exit__ = MagicMock(return_value=False)

        mock_image_module = MagicMock()
        mock_image_module.frombytes.return_value = MagicMock()

        adapter = WinOCRAdapter(mss_module=mock_mss_module, pil_image_module=mock_image_module)
        region = {"left": 0, "top": 0, "width": 100, "height": 50}
        result = adapter._capture_screen_region(region)

        assert result.endswith(".png")

    def test_adapter_name_is_winocr(self):
        adapter = WinOCRAdapter()
        assert adapter.name == "winocr"
