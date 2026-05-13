import time
from pathlib import Path

from ..exceptions import AdapterActionError
from ..interfaces import OCRAdapter
from ..models import OCRRawResult
from .gui_common import ClipboardGateway, GUIAutomationDriver, ensure_temp_png


class PowerToysTextExtractorAdapter(OCRAdapter):
    name = "powertoys_text_extractor"

    def __init__(self, gui_driver=None, clipboard=None, hotkey=None):
        self.gui_driver = gui_driver or GUIAutomationDriver()
        self.clipboard = clipboard or ClipboardGateway()
        self.hotkey = tuple(hotkey or ("win", "shift", "t"))

    def supports(self, capture_request):
        return capture_request.can_use_screen_ocr()

    def extract(self, capture_request, evidence_run):
        if not self.supports(capture_request):
            raise AdapterActionError("PowerToys Text Extractor requires an effective screen region")

        previous_text = self.clipboard.get_text()
        failure_image_path = ensure_temp_png("cidls_powertoys_fail_")
        try:
            self.gui_driver.hotkey(*self.hotkey)
            time.sleep(0.35)
            self.gui_driver.drag_region(capture_request.effective_region())
            raw_text = self.clipboard.wait_for_new_text(
                previous_text=previous_text,
                timeout_seconds=capture_request.timeout_seconds,
            )
            return OCRRawResult(
                adapter_name=self.name,
                raw_text=raw_text,
                capture_image_path="",
                clipboard_text=raw_text,
                blocks=[],
                metadata={"hotkey": list(self.hotkey)},
            )
        except Exception:
            self.gui_driver.screenshot(failure_image_path)
            evidence_run.save_failure_screenshot(failure_image_path)
            raise
        finally:
            candidate = Path(failure_image_path)
            if candidate.exists():
                candidate.unlink(missing_ok=True)
