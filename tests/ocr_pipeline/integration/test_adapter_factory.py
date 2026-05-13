"""
Integration tests for the adapter factory.

Covers:
- build_adapter("winocr") returns WinOCRAdapter instance
- build_adapter("snipping_tool") returns SnippingToolOCRAdapter instance
- build_adapter("powertoys_text_extractor") returns PowerToysTextExtractorAdapter instance
- build_adapter with unknown name raises AdapterNotFoundError
- build_default_pipeline returns list of adapters
- list_available_adapters returns list of dicts with "name" and "available" keys

Note: SnippingToolOCRAdapter and PowerToysTextExtractorAdapter eagerly import
pyautogui, pyperclip, PIL.ImageGrab, and pygetwindow on instantiation via
gui_common helper classes. Tests that instantiate those adapters patch the
relevant import helpers at the gui_common module level.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from cidls.ocr_pipeline.adapters.factory import (
    AdapterNotFoundError,
    build_adapter,
    build_default_pipeline,
    list_available_adapters,
)
from cidls.ocr_pipeline.adapters.fallback_ocr_adapter import PowerToysTextExtractorAdapter
from cidls.ocr_pipeline.adapters.snipping_tool_adapter import SnippingToolOCRAdapter
from cidls.ocr_pipeline.adapters.winocr_adapter import WinOCRAdapter
from cidls.ocr_pipeline.interfaces import OCRAdapter


# ---------------------------------------------------------------------------
# Helpers: stub GUI dependencies that are eagerly imported on adapter init
# ---------------------------------------------------------------------------

def _gui_stubs():
    """
    Return a context manager stack that patches all eagerly-imported GUI
    dependencies so SnippingToolOCRAdapter and PowerToysTextExtractorAdapter
    can be instantiated without pyautogui/pyperclip/pygetwindow installed.
    """
    fake_pyautogui = MagicMock()
    fake_pyautogui.FAILSAFE = True
    fake_pyautogui.PAUSE = 0.1

    fake_pyperclip = MagicMock()
    fake_imagegrab = MagicMock()
    fake_pygetwindow = MagicMock()

    return [
        patch("cidls.ocr_pipeline.adapters.gui_common._import_pyautogui", return_value=fake_pyautogui),
        patch.dict(
            sys.modules,
            {
                "pyperclip": fake_pyperclip,
                "pygetwindow": fake_pygetwindow,
            },
        ),
        patch("cidls.ocr_pipeline.adapters.gui_common.ClipboardGateway.__init__", return_value=None),
        patch("cidls.ocr_pipeline.adapters.gui_common.WindowGateway.__init__", return_value=None),
        patch("cidls.ocr_pipeline.adapters.gui_common.TemplateLocator.__init__", return_value=None),
    ]


from contextlib import ExitStack


def with_gui_stubs(func):
    """Decorator that wraps a test method in all GUI stubs."""
    def wrapper(*args, **kwargs):
        with ExitStack() as stack:
            for ctx in _gui_stubs():
                stack.enter_context(ctx)
            return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


# ---------------------------------------------------------------------------
# build_adapter
# ---------------------------------------------------------------------------

class TestBuildAdapter:
    def test_build_winocr_returns_winocr_adapter(self):
        adapter = build_adapter("winocr")
        assert isinstance(adapter, WinOCRAdapter)

    def test_build_snipping_tool_returns_snipping_tool_adapter(self):
        with ExitStack() as stack:
            for ctx in _gui_stubs():
                stack.enter_context(ctx)
            adapter = build_adapter("snipping_tool")
        assert isinstance(adapter, SnippingToolOCRAdapter)

    def test_build_powertoys_returns_powertoys_adapter(self):
        with ExitStack() as stack:
            for ctx in _gui_stubs():
                stack.enter_context(ctx)
            adapter = build_adapter("powertoys_text_extractor")
        assert isinstance(adapter, PowerToysTextExtractorAdapter)

    def test_build_unknown_raises_adapter_not_found_error(self):
        with pytest.raises(AdapterNotFoundError):
            build_adapter("nonexistent_adapter")

    def test_build_unknown_error_message_mentions_name(self):
        with pytest.raises(AdapterNotFoundError, match="unknown_xyz"):
            build_adapter("unknown_xyz")

    def test_built_adapter_is_ocr_adapter_subclass(self):
        adapter = build_adapter("winocr")
        assert isinstance(adapter, OCRAdapter)

    def test_built_snipping_adapter_is_ocr_adapter_subclass(self):
        with ExitStack() as stack:
            for ctx in _gui_stubs():
                stack.enter_context(ctx)
            adapter = build_adapter("snipping_tool")
        assert isinstance(adapter, OCRAdapter)

    def test_built_powertoys_adapter_is_ocr_adapter_subclass(self):
        with ExitStack() as stack:
            for ctx in _gui_stubs():
                stack.enter_context(ctx)
            adapter = build_adapter("powertoys_text_extractor")
        assert isinstance(adapter, OCRAdapter)

    def test_build_adapter_kwargs_passed_to_constructor(self):
        # WinOCRAdapter accepts mss_module and pil_image_module kwargs
        fake_mss = object()
        adapter = build_adapter("winocr", mss_module=fake_mss)
        assert isinstance(adapter, WinOCRAdapter)
        assert adapter._mss is fake_mss

    def test_each_call_returns_new_instance(self):
        adapter1 = build_adapter("winocr")
        adapter2 = build_adapter("winocr")
        assert adapter1 is not adapter2

    def test_empty_string_raises_adapter_not_found_error(self):
        with pytest.raises(AdapterNotFoundError):
            build_adapter("")

    def test_wrong_case_raises_adapter_not_found_error(self):
        with pytest.raises(AdapterNotFoundError):
            build_adapter("WinOCR")


# ---------------------------------------------------------------------------
# build_default_pipeline
# ---------------------------------------------------------------------------

class TestBuildDefaultPipeline:
    def test_returns_list(self):
        with ExitStack() as stack:
            for ctx in _gui_stubs():
                stack.enter_context(ctx)
            result = build_default_pipeline()
        assert isinstance(result, list)

    def test_returns_non_empty_list(self):
        with ExitStack() as stack:
            for ctx in _gui_stubs():
                stack.enter_context(ctx)
            result = build_default_pipeline()
        assert len(result) > 0

    def test_all_elements_are_ocr_adapters(self):
        with ExitStack() as stack:
            for ctx in _gui_stubs():
                stack.enter_context(ctx)
            result = build_default_pipeline()
        for adapter in result:
            assert isinstance(adapter, OCRAdapter)

    def test_default_preferred_is_snipping_tool(self):
        with ExitStack() as stack:
            for ctx in _gui_stubs():
                stack.enter_context(ctx)
            result = build_default_pipeline()
        names = [adapter.name for adapter in result]
        assert "snipping_tool" in names

    def test_default_fallback_is_powertoys(self):
        with ExitStack() as stack:
            for ctx in _gui_stubs():
                stack.enter_context(ctx)
            result = build_default_pipeline()
        names = [adapter.name for adapter in result]
        assert "powertoys_text_extractor" in names

    def test_preferred_and_fallback_respected(self):
        with ExitStack() as stack:
            for ctx in _gui_stubs():
                stack.enter_context(ctx)
            result = build_default_pipeline(preferred="winocr", fallback="powertoys_text_extractor")
        names = [adapter.name for adapter in result]
        assert "winocr" in names
        assert "powertoys_text_extractor" in names

    def test_empty_fallback_skipped(self):
        # winocr only — no GUI deps needed
        result = build_default_pipeline(preferred="winocr", fallback="")
        names = [adapter.name for adapter in result]
        assert "winocr" in names
        assert len(result) == 1

    def test_two_adapters_by_default(self):
        with ExitStack() as stack:
            for ctx in _gui_stubs():
                stack.enter_context(ctx)
            result = build_default_pipeline()
        assert len(result) == 2

    def test_snipping_tool_is_first_by_default(self):
        with ExitStack() as stack:
            for ctx in _gui_stubs():
                stack.enter_context(ctx)
            result = build_default_pipeline()
        assert result[0].name == "snipping_tool"


# ---------------------------------------------------------------------------
# list_available_adapters
# ---------------------------------------------------------------------------

class TestListAvailableAdapters:
    def test_returns_list(self):
        result = list_available_adapters()
        assert isinstance(result, list)

    def test_all_entries_have_name_key(self):
        result = list_available_adapters()
        for entry in result:
            assert "name" in entry

    def test_all_entries_have_available_key(self):
        result = list_available_adapters()
        for entry in result:
            assert "available" in entry

    def test_available_value_is_bool(self):
        result = list_available_adapters()
        for entry in result:
            assert isinstance(entry["available"], bool)

    def test_name_value_is_string(self):
        result = list_available_adapters()
        for entry in result:
            assert isinstance(entry["name"], str)

    def test_all_registered_adapters_present(self):
        result = list_available_adapters()
        names = {entry["name"] for entry in result}
        assert "winocr" in names
        assert "snipping_tool" in names
        assert "powertoys_text_extractor" in names

    def test_returns_three_or_more_entries(self):
        result = list_available_adapters()
        assert len(result) >= 3

    def test_no_duplicate_names(self):
        result = list_available_adapters()
        names = [entry["name"] for entry in result]
        assert len(names) == len(set(names))
