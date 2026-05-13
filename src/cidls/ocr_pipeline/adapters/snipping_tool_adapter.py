import time
from pathlib import Path

from ..exceptions import AdapterActionError
from ..interfaces import OCRAdapter
from ..models import OCRRawResult
from .gui_common import ClipboardGateway, GUIAutomationDriver, TemplateLocator, WindowGateway, ensure_temp_png


class SnippingToolOCRAdapter(OCRAdapter):
    name = "snipping_tool"

    def __init__(
        self,
        assets_dir="fixtures/templates/snipping_tool",
        gui_driver=None,
        clipboard=None,
        window_gateway=None,
        template_locator=None,
        window_titles=None,
        action_timeout_seconds=10,
    ):
        self.assets_dir = Path(assets_dir)
        self.gui_driver = gui_driver or GUIAutomationDriver()
        self.clipboard = clipboard or ClipboardGateway()
        self.window_gateway = window_gateway or WindowGateway()
        self.template_locator = template_locator or TemplateLocator(self.assets_dir, gui_driver=self.gui_driver)
        self.window_titles = list(window_titles or ["snipping tool", "切り取り", "snip"])
        self.action_timeout_seconds = int(action_timeout_seconds)

    def supports(self, capture_request):
        return capture_request.can_use_screen_ocr()

    def extract(self, capture_request, evidence_run):
        if not self.supports(capture_request):
            raise AdapterActionError("Snipping Tool adapter requires an effective screen region")

        previous_text = self.clipboard.get_text()
        capture_image_path = ensure_temp_png("cidls_snip_")
        failure_image_path = ensure_temp_png("cidls_snip_fail_")

        try:
            self.gui_driver.hotkey("win", "shift", "s")
            time.sleep(0.45)
            self.gui_driver.drag_region(capture_request.effective_region())

            window = self.window_gateway.wait_for_title(
                self.window_titles,
                timeout_seconds=capture_request.timeout_seconds,
            )
            self.window_gateway.activate(window)
            time.sleep(0.6)

            saved_capture_path = self.clipboard.save_clipboard_image(capture_image_path)
            if saved_capture_path:
                evidence_run.save_capture_image(saved_capture_path)

            self._click_template(
                capture_request.metadata.get("snipping_text_actions_templates", [
                    "text_actions.png",
                    "text_actions_ja.png",
                ]),
                timeout_seconds=self.action_timeout_seconds,
            )
            time.sleep(0.4)

            self._click_template(
                capture_request.metadata.get("snipping_copy_templates", [
                    "copy_all_text.png",
                    "copy_text.png",
                    "copy_all_text_ja.png",
                ]),
                timeout_seconds=self.action_timeout_seconds,
            )

            raw_text = self.clipboard.wait_for_new_text(
                previous_text=previous_text,
                timeout_seconds=capture_request.timeout_seconds,
            )
            return OCRRawResult(
                adapter_name=self.name,
                raw_text=raw_text,
                capture_image_path=saved_capture_path,
                clipboard_text=raw_text,
                blocks=[],
                metadata={
                    "templates_root": str(self.assets_dir),
                    "window_titles": list(self.window_titles),
                },
            )
        except Exception:
            self.gui_driver.screenshot(failure_image_path)
            evidence_run.save_failure_screenshot(failure_image_path)
            raise
        finally:
            for temp_path in [capture_image_path, failure_image_path]:
                candidate = Path(temp_path)
                if candidate.exists():
                    candidate.unlink(missing_ok=True)

    def _click_template(self, template_names, timeout_seconds):
        point, _ = self.template_locator.locate_first(template_names, timeout_seconds=timeout_seconds)
        self.gui_driver.click(point)
