"""
E2E Playwright tests for the CIDLS web OCR target.

These tests are environment-sensitive on Windows because Playwright needs
subprocess + named-pipe permissions that may be blocked by application control
policy in automation contexts. In that case the fixture skips instead of
producing false implementation failures.
"""

import subprocess
import sys
import time
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

WEB_PORT = 8765
WEB_URL = f"http://127.0.0.1:{WEB_PORT}"


def _write_tiny_png(path):
    path.write_bytes(
        bytes.fromhex(
            "89504E470D0A1A0A0000000D4948445200000001000000010802000000907753DE"
            "0000000C4944415408D763F8FFFF3F0005FE02FEA7A69D5B0000000049454E44AE426082"
        )
    )
    return path


@pytest.fixture(scope="session")
def web_server():
    server_script = Path(__file__).parents[3] / "fixtures" / "web" / "server.py"
    proc = subprocess.Popen(
        [sys.executable, str(server_script), "--port", str(WEB_PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2.0)
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def browser_context(web_server):
    if os.environ.get("CIDLS_ENABLE_PLAYWRIGHT_E2E", "") != "1":
        pytest.skip("Set CIDLS_ENABLE_PLAYWRIGHT_E2E=1 to run browser E2E in a desktop session")
    playwright = pytest.importorskip("playwright.sync_api")
    try:
        with playwright.sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                locale="ja-JP",
            )
            yield context
            context.close()
            browser.close()
    except PermissionError as error:
        pytest.skip(f"Playwright blocked by local policy: {error}")
    except OSError as error:
        pytest.skip(f"Playwright unavailable in this environment: {error}")


@pytest.fixture
def page(browser_context):
    pg = browser_context.new_page()
    yield pg
    pg.close()


def _screenshot_stage(page, scene, dataset, tmp_path):
    url = f"{WEB_URL}/?scene={scene}&dataset={dataset}"
    page.goto(url, wait_until="networkidle", timeout=15000)
    page.wait_for_selector("#stage", timeout=5000)
    page.wait_for_timeout(500)
    out = tmp_path / f"ocr_{scene}_{dataset}.png"
    page.locator("#stage").screenshot(path=str(out))
    return out


def _ocr_image(image_path):
    from cidls.ocr_pipeline.adapters.winocr_adapter import WinOCRAdapter
    from cidls.ocr_pipeline.models import CaptureRequest
    from cidls.ocr_pipeline.ocr_result_parser import OCRResultParser
    from cidls.ocr_pipeline.rpainput_converter import RPAInputConverter

    adapter = WinOCRAdapter()
    if not adapter.is_available():
        pytest.skip("winocr not available on this system")

    request = CaptureRequest(
        source_mode="image_file",
        image_path=str(image_path),
        language_hint="ja-JP",
        preferred_adapter="winocr",
        fallback_adapter="",
    )

    class FakeRun:
        def save_capture_image(self, path):
            return path

        def save_failure_screenshot(self, path):
            return path

    raw = adapter.extract(request, FakeRun())
    parsed = OCRResultParser().parse(raw)
    return RPAInputConverter().convert(request, raw, parsed).to_dict()


class TestFormScene:
    def test_page_renders_form_scene(self, page):
        page.goto(f"{WEB_URL}/?scene=form&dataset=ja", wait_until="networkidle")
        page.wait_for_selector("#stage", timeout=5000)
        assert len(page.locator("#stage").inner_text()) > 0

    def test_form_screenshot_is_non_empty(self, page, tmp_path):
        image_path = _screenshot_stage(page, "form", "ja", tmp_path)
        assert image_path.exists()
        assert image_path.stat().st_size > 500

    def test_form_ocr_produces_key_values(self, page, tmp_path):
        image_path = _screenshot_stage(page, "form", "ja", tmp_path)
        report = _ocr_image(image_path)
        assert isinstance(report["key_values"], list)
        assert len(report["key_values"]) >= 1


class TestTableScene:
    def test_table_screenshot_exists(self, page, tmp_path):
        image_path = _screenshot_stage(page, "table", "table_noise", tmp_path)
        assert image_path.exists()
        assert image_path.stat().st_size > 500

    def test_table_ocr_produces_rows(self, page, tmp_path):
        image_path = _screenshot_stage(page, "table", "table_noise", tmp_path)
        report = _ocr_image(image_path)
        assert isinstance(report["rows"], list)
        assert len(report["rows"]) >= 1


class TestMixedScene:
    def test_mixed_screenshot_exists(self, page, tmp_path):
        image_path = _screenshot_stage(page, "mixed", "mixed", tmp_path)
        assert image_path.exists()

    def test_mixed_ocr_returns_text(self, page, tmp_path):
        image_path = _screenshot_stage(page, "mixed", "mixed", tmp_path)
        report = _ocr_image(image_path)
        assert len(report["normalized_text"]) >= 3


class TestOCREdgeCases:
    def test_ocr_result_empty_produces_warning(self):
        from cidls.ocr_pipeline.models import OCRRawResult
        from cidls.ocr_pipeline.ocr_result_parser import OCRResultParser

        result = OCRResultParser().parse(OCRRawResult(adapter_name="winocr", raw_text=""))
        assert "ocr_result_empty" in result["warnings"]

    def test_structured_signal_low_warning_on_plain_lines(self):
        from cidls.ocr_pipeline.models import OCRRawResult
        from cidls.ocr_pipeline.ocr_result_parser import OCRResultParser

        result = OCRResultParser().parse(
            OCRRawResult(adapter_name="winocr", raw_text="hello world\nfoo bar\nbaz")
        )
        assert "structured_signal_low" in result["warnings"]

    def test_conversion_report_format_version(self):
        from cidls.ocr_pipeline.models import CaptureRequest, OCRRawResult
        from cidls.ocr_pipeline.ocr_result_parser import OCRResultParser
        from cidls.ocr_pipeline.rpainput_converter import RPAInputConverter

        request = CaptureRequest(
            source_mode="screen_region",
            region={"left": 0, "top": 0, "width": 100, "height": 40},
            preferred_adapter="snipping_tool",
            fallback_adapter="powertoys_text_extractor",
        )
        raw = OCRRawResult(adapter_name="winocr", raw_text="Case ID: AP-2026-0417")
        report = RPAInputConverter().convert(request, raw, OCRResultParser().parse(raw))
        assert report.to_dict()["structured_input"]["format_version"] == "cidls.rpainput.v1"

    def test_fallback_adapter_selected_when_preferred_fails(self, tmp_path):
        from unittest.mock import MagicMock

        from cidls.ocr_pipeline.capture_orchestrator import CaptureOrchestrator
        from cidls.ocr_pipeline.exceptions import AdapterActionError
        from cidls.ocr_pipeline.models import CaptureRequest, OCRRawResult
        from cidls.ocr_pipeline.ocr_result_parser import OCRResultParser
        from cidls.ocr_pipeline.rpainput_converter import RPAInputConverter

        failing_adapter = MagicMock()
        failing_adapter.name = "snipping_tool"
        failing_adapter.supports.return_value = True
        failing_adapter.extract.side_effect = AdapterActionError("GUI not available")

        fallback_adapter = MagicMock()
        fallback_adapter.name = "powertoys_text_extractor"
        fallback_adapter.supports.return_value = True
        fallback_adapter.extract.return_value = OCRRawResult(
            adapter_name="powertoys_text_extractor",
            raw_text="Case ID: AP-2026-0417",
        )

        class FakeEvidenceRun:
            def save_raw_text(self, text):
                return text

            def save_structured(self, report):
                return report

            def complete(self, status, payload):
                return status, payload

            def record_error(self, adapter_name, error):
                return adapter_name, error

            def record_retry(self, adapter_name, attempt_number, reason):
                return adapter_name, attempt_number, reason

        class FakeEvidenceLogger:
            def start_run(self, capture_request, adapter_name):
                return FakeEvidenceRun()

        orchestrator = CaptureOrchestrator(
            adapters=[failing_adapter, fallback_adapter],
            parser=OCRResultParser(),
            converter=RPAInputConverter(),
            evidence_logger=FakeEvidenceLogger(),
        )
        request = CaptureRequest(
            source_mode="screen_region",
            region={"left": 0, "top": 0, "width": 100, "height": 100},
            preferred_adapter="snipping_tool",
            fallback_adapter="powertoys_text_extractor",
            retry_count=0,
        )
        report = orchestrator.execute(request)
        assert "Case ID" in report.normalized_text

    def test_gui_snipping_tool_smoke(self, tmp_path):
        pytest.importorskip("pyautogui")
        from cidls.ocr_pipeline.adapters.snipping_tool_adapter import SnippingToolOCRAdapter
        from cidls.ocr_pipeline.models import CaptureRequest

        adapter = SnippingToolOCRAdapter(assets_dir=str(tmp_path))

        request_screen = CaptureRequest(
            source_mode="screen_region",
            region={"left": 0, "top": 0, "width": 200, "height": 200},
        )
        request_file = type("RequestFile", (), {"can_use_screen_ocr": lambda self: False})()
        assert adapter.supports(request_screen) is True
        assert adapter.supports(request_file) is False
