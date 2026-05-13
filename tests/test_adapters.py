import pytest

from cidls.ocr_pipeline.adapters.fallback_ocr_adapter import PowerToysTextExtractorAdapter
from cidls.ocr_pipeline.adapters.snipping_tool_adapter import SnippingToolOCRAdapter
from cidls.ocr_pipeline.evidence_logger import EvidenceLogger
from cidls.ocr_pipeline.models import CaptureRequest


class FakeGUI:
    def __init__(self):
        self.events = []

    def hotkey(self, *keys):
        self.events.append(("hotkey", keys))

    def drag_region(self, region):
        self.events.append(("drag_region", dict(region)))

    def click(self, point):
        self.events.append(("click", point))

    def screenshot(self, target_path):
        with open(target_path, "wb") as handle:
            handle.write(b"fake")
        self.events.append(("screenshot", target_path))


class FakeClipboard:
    def __init__(self, next_text="氏名: 山田 花子", image_path=""):
        self.next_text = next_text
        self.image_path = image_path

    def get_text(self):
        return ""

    def wait_for_new_text(self, previous_text="", timeout_seconds=10):
        if isinstance(self.next_text, Exception):
            raise self.next_text
        return self.next_text

    def save_clipboard_image(self, target_path):
        if not self.image_path:
            return ""
        with open(target_path, "wb") as handle:
            handle.write(b"image")
        return target_path


class FakeWindow:
    def __init__(self):
        self.activated = False

    def activate(self):
        self.activated = True


class FakeWindowGateway:
    def __init__(self):
        self.window = FakeWindow()

    def wait_for_title(self, title_keywords, timeout_seconds=10):
        return self.window

    def activate(self, window):
        window.activate()


class FakeLocator:
    def __init__(self):
        self.calls = []

    def locate_first(self, template_names, timeout_seconds=8):
        self.calls.append(list(template_names))
        return (100, 120), "template.png"


def test_snipping_tool_adapter_clicks_templates_and_returns_text(tmp_path):
    adapter = SnippingToolOCRAdapter(
        assets_dir=tmp_path,
        gui_driver=FakeGUI(),
        clipboard=FakeClipboard(image_path="yes"),
        window_gateway=FakeWindowGateway(),
        template_locator=FakeLocator(),
    )
    evidence = EvidenceLogger(root_dir=tmp_path).start_run(
        CaptureRequest(
            source_mode="screen_region",
            region={"left": 5, "top": 10, "width": 120, "height": 60},
            idempotency_key="snip-unit",
        ),
        adapter_name="snipping_tool",
    )
    request = CaptureRequest(
        source_mode="screen_region",
        region={"left": 5, "top": 10, "width": 120, "height": 60},
        idempotency_key="snip-unit",
    )

    result = adapter.extract(request, evidence)

    assert result.adapter_name == "snipping_tool"
    assert "山田" in result.raw_text


def test_powertoys_adapter_uses_hotkey_and_region(tmp_path):
    gui = FakeGUI()
    adapter = PowerToysTextExtractorAdapter(gui_driver=gui, clipboard=FakeClipboard(next_text="金額: ¥128,000"))
    evidence = EvidenceLogger(root_dir=tmp_path).start_run(
        CaptureRequest(
            source_mode="screen_region",
            region={"left": 15, "top": 20, "width": 100, "height": 50},
            idempotency_key="powertoys-unit",
        ),
        adapter_name="powertoys_text_extractor",
    )
    request = CaptureRequest(
        source_mode="screen_region",
        region={"left": 15, "top": 20, "width": 100, "height": 50},
        idempotency_key="powertoys-unit",
    )

    result = adapter.extract(request, evidence)

    assert result.adapter_name == "powertoys_text_extractor"
    assert ("hotkey", ("win", "shift", "t")) in gui.events
    assert any(event[0] == "drag_region" for event in gui.events)


def test_screen_ocr_adapters_accept_image_preview_requests(tmp_path):
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"png")
    snipping = SnippingToolOCRAdapter(
        assets_dir=tmp_path,
        gui_driver=FakeGUI(),
        clipboard=FakeClipboard(),
        window_gateway=FakeWindowGateway(),
        template_locator=FakeLocator(),
    )
    powertoys = PowerToysTextExtractorAdapter(gui_driver=FakeGUI(), clipboard=FakeClipboard())
    request = CaptureRequest(
        source_mode="image_file",
        image_path=str(image_path),
        idempotency_key="image-preview-support",
    )
    request.preview_region = {"left": 30, "top": 40, "width": 200, "height": 120}

    assert snipping.supports(request) is True
    assert powertoys.supports(request) is True


def test_snipping_tool_adapter_saves_failure_screenshot_on_error(tmp_path):
    gui = FakeGUI()
    adapter = SnippingToolOCRAdapter(
        assets_dir=tmp_path,
        gui_driver=gui,
        clipboard=FakeClipboard(next_text=RuntimeError("clipboard timeout")),
        window_gateway=FakeWindowGateway(),
        template_locator=FakeLocator(),
    )
    evidence = EvidenceLogger(root_dir=tmp_path).start_run(
        CaptureRequest(
            source_mode="screen_region",
            region={"left": 1, "top": 1, "width": 100, "height": 40},
            idempotency_key="snip-fail",
        ),
        adapter_name="snipping_tool",
    )
    request = CaptureRequest(
        source_mode="screen_region",
        region={"left": 1, "top": 1, "width": 100, "height": 40},
        idempotency_key="snip-fail",
    )

    with pytest.raises(Exception):
        adapter.extract(request, evidence)

    failure_path = tmp_path / "snip-fail" / "failure.png"
    assert failure_path.exists()
