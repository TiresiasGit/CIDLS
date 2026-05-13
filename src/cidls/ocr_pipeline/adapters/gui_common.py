import os
import tempfile
import time
from pathlib import Path

from ..exceptions import AdapterActionError, ClipboardTimeoutError, WindowActivationError


def _import_pyautogui():
    import pyautogui

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
    return pyautogui


class GUIAutomationDriver:
    def __init__(self, pyautogui_module=None):
        self.pyautogui = pyautogui_module or _import_pyautogui()

    def hotkey(self, *keys):
        self.pyautogui.hotkey(*keys)

    def press(self, key, presses=1, interval=0.1):
        self.pyautogui.press(key, presses=presses, interval=interval)

    def click(self, point):
        self.pyautogui.click(point[0], point[1])

    def drag_region(self, region):
        start_x = int(region["left"])
        start_y = int(region["top"])
        end_x = int(region["left"] + region["width"])
        end_y = int(region["top"] + region["height"])
        self.pyautogui.moveTo(start_x, start_y)
        self.pyautogui.mouseDown()
        self.pyautogui.moveTo(end_x, end_y, duration=0.18)
        self.pyautogui.mouseUp()

    def locate_center(self, image_path, confidence=0.88, grayscale=True):
        point = self.pyautogui.locateCenterOnScreen(str(image_path), confidence=confidence, grayscale=grayscale)
        if not point:
            return None
        return (int(point.x), int(point.y))

    def screenshot(self, target_path):
        image = self.pyautogui.screenshot()
        image.save(target_path)
        return str(target_path)


class ClipboardGateway:
    def __init__(self, pyperclip_module=None, image_grab_module=None):
        if pyperclip_module is None:
            import pyperclip as pyperclip_module
        self.pyperclip = pyperclip_module
        if image_grab_module is None:
            from PIL import ImageGrab as image_grab_module
        self.image_grab = image_grab_module

    def get_text(self):
        return self.pyperclip.paste()

    def set_text(self, value):
        self.pyperclip.copy(value)

    def wait_for_new_text(self, previous_text="", timeout_seconds=10, poll_interval=0.2):
        deadline = time.monotonic() + float(timeout_seconds)
        while time.monotonic() < deadline:
            current_text = self.get_text()
            if current_text and current_text != previous_text:
                return current_text
            time.sleep(poll_interval)
        raise ClipboardTimeoutError("clipboard text was not updated in time")

    def save_clipboard_image(self, target_path):
        image = self.image_grab.grabclipboard()
        if image is None:
            return ""
        image.save(target_path)
        return str(target_path)


class WindowGateway:
    def __init__(self, pygetwindow_module=None):
        if pygetwindow_module is None:
            import pygetwindow as pygetwindow_module
        self.pygetwindow = pygetwindow_module

    def wait_for_title(self, title_keywords, timeout_seconds=10, poll_interval=0.25):
        deadline = time.monotonic() + float(timeout_seconds)
        title_keywords = [keyword.lower() for keyword in title_keywords]
        while time.monotonic() < deadline:
            for window in self.pygetwindow.getAllWindows():
                title = str(getattr(window, "title", "") or "")
                lowered = title.lower()
                if any(keyword in lowered for keyword in title_keywords):
                    return window
            time.sleep(poll_interval)
        raise WindowActivationError(f"window not found for keywords: {title_keywords}")

    def activate(self, window):
        try:
            window.activate()
        except Exception as error:
            raise WindowActivationError(str(error)) from error
        self.wait_until_active(window)

    def wait_until_active(self, window, timeout_seconds=3, poll_interval=0.1):
        deadline = time.monotonic() + float(timeout_seconds)
        expected_title = str(getattr(window, "title", "") or "")
        while time.monotonic() < deadline:
            try:
                active_window = self.pygetwindow.getActiveWindow()
            except Exception as error:
                raise WindowActivationError(str(error)) from error
            active_title = str(getattr(active_window, "title", "") or "")
            if expected_title and expected_title == active_title:
                return window
            time.sleep(poll_interval)
        raise WindowActivationError(f"window was not activated: {expected_title}")


class TemplateLocator:
    def __init__(self, assets_dir, gui_driver=None, confidence=0.9, poll_interval=0.25):
        self.assets_dir = Path(assets_dir)
        self.gui_driver = gui_driver or GUIAutomationDriver()
        self.confidence = float(confidence)
        self.poll_interval = float(poll_interval)

    def locate_first(self, template_names, timeout_seconds=8):
        deadline = time.monotonic() + float(timeout_seconds)
        template_names = list(template_names)
        while time.monotonic() < deadline:
            for name in template_names:
                candidate = self.assets_dir / name
                if not candidate.exists():
                    continue
                point = self.gui_driver.locate_center(candidate, confidence=self.confidence)
                if point:
                    return point, str(candidate)
            time.sleep(self.poll_interval)
        raise AdapterActionError(f"template not found on screen: {template_names}")


def ensure_temp_png(prefix):
    handle, temp_path = tempfile.mkstemp(prefix=prefix, suffix=".png")
    os.close(handle)
    return temp_path
