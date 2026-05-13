"""
DPI awareness utilities for Windows 11 screen coordinate correction.
Must be called before any pyautogui screen operations.
"""
import ctypes
import sys


def set_dpi_aware() -> bool:
    """
    Set DPI awareness to Per-Monitor v2 to prevent coordinate scaling issues
    on 125%/150%/200% displays. Call once at process start.
    Returns True if awareness was set successfully.
    """
    if sys.platform != "win32":
        return False
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return True
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
        return True
    except (AttributeError, OSError):
        pass
    return False


def get_scale_factor() -> float:
    """
    Returns the primary monitor DPI scale factor (1.0 = 100%, 1.25 = 125%, etc.).
    Returns 1.0 if detection fails.
    """
    if sys.platform != "win32":
        return 1.0
    try:
        hdc = ctypes.windll.user32.GetDC(0)
        dpi_x = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
        ctypes.windll.user32.ReleaseDC(0, hdc)
        return dpi_x / 96.0
    except (AttributeError, OSError):
        return 1.0


def logical_to_physical(x: int, y: int) -> tuple[int, int]:
    """
    Convert logical coordinates to physical pixels when DPI aware is set.
    Under Per-Monitor DPI awareness the OS handles this, but for legacy
    pyautogui that reads logical pixels, physical correction may be needed.
    """
    scale = get_scale_factor()
    return int(x * scale), int(y * scale)


def scale_region(region: dict, scale: float | None = None) -> dict:
    """
    Scale a region dict (left/top/width/height) by the DPI scale factor.
    """
    if scale is None:
        scale = get_scale_factor()
    return {
        "left": int(region["left"] * scale),
        "top": int(region["top"] * scale),
        "width": int(region["width"] * scale),
        "height": int(region["height"] * scale),
    }
