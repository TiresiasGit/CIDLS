import contextlib
import os
import subprocess
import tempfile
import time
from pathlib import Path

from .exceptions import BrowserLaunchError, RetryExhaustedError


class ImagePreviewSession:
    def __init__(
        self,
        capture_request,
        browser_path="",
        window_position=None,
        window_size=None,
        startup_wait_seconds=1.8,
    ):
        self.capture_request = capture_request
        self.browser_path = browser_path or self._discover_browser()
        self.window_position = window_position or {"left": 30, "top": 30}
        self.window_size = window_size or {"width": 1500, "height": 980}
        self.startup_wait_seconds = float(startup_wait_seconds)
        self.process = None
        self.preview_path = ""

    def __enter__(self):
        self.preview_path = self._write_preview_file()
        command = [
            self.browser_path,
            "--new-window",
            f"--window-position={self.window_position['left']},{self.window_position['top']}",
            f"--window-size={self.window_size['width']},{self.window_size['height']}",
            Path(self.preview_path).as_uri(),
        ]
        try:
            self.process = subprocess.Popen(command)
        except Exception as error:
            raise BrowserLaunchError(str(error)) from error
        time.sleep(self.startup_wait_seconds)
        self.capture_request.preview_region = {
            "left": self.window_position["left"] + 72,
            "top": self.window_position["top"] + 110,
            "width": self.window_size["width"] - 144,
            "height": self.window_size["height"] - 182,
        }
        return self.capture_request

    def __exit__(self, exc_type, exc, tb):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        if self.preview_path:
            Path(self.preview_path).unlink(missing_ok=True)

    def _write_preview_file(self):
        handle, preview_path = tempfile.mkstemp(prefix="cidls_ocr_preview_", suffix=".html")
        os.close(handle)
        image_uri = Path(self.capture_request.image_path).resolve().as_uri()
        html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>CIDLS OCR Preview</title>
  <style>
    html, body {{
      margin: 0;
      height: 100%;
      background: #e9eef5;
      font-family: "Segoe UI", "Yu Gothic UI", sans-serif;
    }}
    .stage {{
      box-sizing: border-box;
      width: calc(100vw - 48px);
      height: calc(100vh - 96px);
      margin: 72px 24px 24px;
      border-radius: 20px;
      border: 1px solid #cdd7e5;
      background: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }}
    img {{
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      image-rendering: auto;
    }}
    .header {{
      position: fixed;
      left: 24px;
      top: 20px;
      font-size: 24px;
      font-weight: 700;
      color: #243043;
    }}
  </style>
</head>
<body>
  <div class="header">CIDLS OCR Preview</div>
  <div class="stage"><img alt="ocr-source" src="{image_uri}"></div>
</body>
</html>
"""
        Path(preview_path).write_text(html, encoding="utf-8")
        return preview_path

    def _discover_browser(self):
        candidates = [
            os.environ.get("CIDLS_BROWSER_PATH", ""),
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return candidate
        raise BrowserLaunchError("browser executable not found for image preview")


class CaptureOrchestrator:
    def __init__(self, adapters, parser, converter, evidence_logger, image_preview_session_factory=None):
        self.adapters = {adapter.name: adapter for adapter in adapters}
        self.parser = parser
        self.converter = converter
        self.evidence_logger = evidence_logger
        self.image_preview_session_factory = image_preview_session_factory or ImagePreviewSession

    def execute(self, capture_request):
        adapter_names = [capture_request.preferred_adapter]
        if capture_request.fallback_adapter and capture_request.fallback_adapter not in adapter_names:
            adapter_names.append(capture_request.fallback_adapter)

        evidence_run = self.evidence_logger.start_run(capture_request, capture_request.preferred_adapter)
        last_error = None

        with self._prepare_request(capture_request):
            for adapter_name in adapter_names:
                adapter = self.adapters.get(adapter_name)
                if not adapter:
                    continue
                if not adapter.supports(capture_request):
                    continue
                for attempt_number in range(1, capture_request.retry_count + 2):
                    try:
                        raw_result = adapter.extract(capture_request, evidence_run)
                        if not raw_result.raw_text.strip():
                            raise RetryExhaustedError(f"{adapter.name} returned empty OCR text")
                        evidence_run.save_raw_text(raw_result.raw_text)
                        parsed_result = self.parser.parse(raw_result)
                        conversion_report = self.converter.convert(capture_request, raw_result, parsed_result)
                        evidence_run.save_structured(conversion_report)
                        evidence_run.complete("success", {
                            "final_adapter": adapter.name,
                            "attempt_number": attempt_number,
                        })
                        return conversion_report
                    except Exception as error:
                        last_error = error
                        evidence_run.record_error(adapter.name, error)
                        if attempt_number <= capture_request.retry_count:
                            evidence_run.record_retry(adapter.name, attempt_number, str(error))
                            time.sleep(0.6)
                            continue
                        break

        evidence_run.complete("failed", {
            "final_error": str(last_error) if last_error else "unknown",
        })
        raise RetryExhaustedError(str(last_error) if last_error else "OCR pipeline failed")

    def _prepare_request(self, capture_request):
        if capture_request.source_mode == "image_file":
            return self.image_preview_session_factory(capture_request)
        return contextlib.nullcontext(capture_request)
