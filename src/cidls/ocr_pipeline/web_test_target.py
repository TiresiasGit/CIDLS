import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from urllib.parse import urlencode

from .exceptions import BrowserLaunchError


class OCRWebTargetSession:
    def __init__(
        self,
        scene="form",
        dataset="ja",
        browser_path="",
        target_html="fixtures/web/ocr_test_target.html",
        window_position=None,
        window_size=None,
        startup_wait_seconds=1.8,
    ):
        self.scene = str(scene or "form").strip()
        self.dataset = str(dataset or "ja").strip()
        self.browser_path = browser_path or self._discover_browser()
        self.target_html = Path(target_html).resolve()
        self.window_position = dict(window_position or {"left": 30, "top": 30})
        self.window_size = dict(window_size or {"width": 1500, "height": 980})
        self.startup_wait_seconds = float(startup_wait_seconds)
        self.process = None

    def build_url(self):
        query = urlencode({"scene": self.scene, "dataset": self.dataset})
        return f"{self.target_html.as_uri()}?{query}"

    def default_capture_region(self):
        return {
            "left": int(self.window_position["left"]) + 56,
            "top": int(self.window_position["top"]) + 196,
            "width": int(self.window_size["width"]) - 112,
            "height": int(self.window_size["height"]) - 268,
        }

    def launch(self):
        if not self.target_html.exists():
            raise BrowserLaunchError(f"web test target not found: {self.target_html}")
        command = [
            self.browser_path,
            "--new-window",
            f"--window-position={self.window_position['left']},{self.window_position['top']}",
            f"--window-size={self.window_size['width']},{self.window_size['height']}",
            self.build_url(),
        ]
        try:
            self.process = subprocess.Popen(command)
        except Exception as error:
            raise BrowserLaunchError(str(error)) from error
        time.sleep(self.startup_wait_seconds)
        return {
            "url": self.build_url(),
            "region": self.default_capture_region(),
            "browser_path": self.browser_path,
        }

    def close(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

    def __enter__(self):
        return self.launch()

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

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
        raise BrowserLaunchError("browser executable not found for web test target")


def build_parser():
    parser = argparse.ArgumentParser(description="Launch the CIDLS OCR web test target in a fixed browser window")
    parser.add_argument("--scene", default="form", choices=["form", "table", "cards", "labels"])
    parser.add_argument("--dataset", default="ja", choices=["ja", "mixed", "table_noise"])
    parser.add_argument("--browser-path", default="")
    parser.add_argument("--target-html", default="fixtures/web/ocr_test_target.html")
    parser.add_argument("--window-left", type=int, default=30)
    parser.add_argument("--window-top", type=int, default=30)
    parser.add_argument("--window-width", type=int, default=1500)
    parser.add_argument("--window-height", type=int, default=980)
    parser.add_argument("--startup-wait-seconds", type=float, default=1.8)
    parser.add_argument("--hold-seconds", type=float, default=0)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    session = OCRWebTargetSession(
        scene=args.scene,
        dataset=args.dataset,
        browser_path=args.browser_path,
        target_html=args.target_html,
        window_position={"left": args.window_left, "top": args.window_top},
        window_size={"width": args.window_width, "height": args.window_height},
        startup_wait_seconds=args.startup_wait_seconds,
    )
    with session as launched:
        print(json.dumps(launched, ensure_ascii=False, indent=2))
        if args.hold_seconds > 0:
            time.sleep(args.hold_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
