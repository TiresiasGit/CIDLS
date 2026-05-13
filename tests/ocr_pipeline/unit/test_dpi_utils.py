"""
Unit tests for dpi_utils.

Covers:
- scale_region with explicit scale factor 1.0, 1.25, 1.5
- scale_region edge cases (zero coordinate values, zero size values not tested as that is
  invalid region — tested values are zero left/top with positive width/height)
- get_scale_factor returns float >= 1.0 (mocked ctypes)
- set_dpi_aware returns bool
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from cidls.ocr_pipeline.dpi_utils import get_scale_factor, scale_region, set_dpi_aware


# ---------------------------------------------------------------------------
# scale_region
# ---------------------------------------------------------------------------

class TestScaleRegion:
    def test_scale_1_0_identity(self):
        region = {"left": 10, "top": 20, "width": 300, "height": 150}
        result = scale_region(region, scale=1.0)
        assert result == {"left": 10, "top": 20, "width": 300, "height": 150}

    def test_scale_1_25(self):
        region = {"left": 100, "top": 200, "width": 400, "height": 300}
        result = scale_region(region, scale=1.25)
        assert result["left"] == 125
        assert result["top"] == 250
        assert result["width"] == 500
        assert result["height"] == 375

    def test_scale_1_5(self):
        region = {"left": 0, "top": 0, "width": 200, "height": 100}
        result = scale_region(region, scale=1.5)
        assert result["left"] == 0
        assert result["top"] == 0
        assert result["width"] == 300
        assert result["height"] == 150

    def test_scale_2_0(self):
        region = {"left": 50, "top": 75, "width": 100, "height": 80}
        result = scale_region(region, scale=2.0)
        assert result["left"] == 100
        assert result["top"] == 150
        assert result["width"] == 200
        assert result["height"] == 160

    def test_result_values_are_integers(self):
        region = {"left": 10, "top": 10, "width": 10, "height": 10}
        result = scale_region(region, scale=1.3)
        assert isinstance(result["left"], int)
        assert isinstance(result["top"], int)
        assert isinstance(result["width"], int)
        assert isinstance(result["height"], int)

    def test_zero_left_and_top_with_positive_dimensions(self):
        region = {"left": 0, "top": 0, "width": 100, "height": 50}
        result = scale_region(region, scale=1.25)
        assert result["left"] == 0
        assert result["top"] == 0
        assert result["width"] == 125
        assert result["height"] == 62

    def test_scale_does_not_modify_input_dict(self):
        region = {"left": 10, "top": 20, "width": 300, "height": 150}
        original = dict(region)
        scale_region(region, scale=1.5)
        assert region == original

    def test_returns_new_dict(self):
        region = {"left": 10, "top": 20, "width": 300, "height": 150}
        result = scale_region(region, scale=1.0)
        assert result is not region

    def test_all_zero_coordinates(self):
        region = {"left": 0, "top": 0, "width": 1, "height": 1}
        result = scale_region(region, scale=1.5)
        assert result["left"] == 0
        assert result["top"] == 0
        assert result["width"] == 1
        assert result["height"] == 1

    def test_large_region_scale_1_25(self):
        region = {"left": 1920, "top": 1080, "width": 3840, "height": 2160}
        result = scale_region(region, scale=1.25)
        assert result["left"] == 2400
        assert result["top"] == 1350
        assert result["width"] == 4800
        assert result["height"] == 2700

    def test_scale_calls_get_scale_factor_when_no_explicit_scale(self):
        region = {"left": 10, "top": 20, "width": 100, "height": 50}
        with patch("cidls.ocr_pipeline.dpi_utils.get_scale_factor", return_value=1.5) as mock_gsf:
            result = scale_region(region)
            mock_gsf.assert_called_once()
        assert result["width"] == 150
        assert result["height"] == 75


# ---------------------------------------------------------------------------
# get_scale_factor
# ---------------------------------------------------------------------------

class TestGetScaleFactor:
    def test_returns_float(self):
        with patch("cidls.ocr_pipeline.dpi_utils.sys") as mock_sys:
            mock_sys.platform = "win32"
            mock_windll = MagicMock()
            mock_windll.user32.GetDC.return_value = 1
            mock_windll.gdi32.GetDeviceCaps.return_value = 96
            mock_windll.user32.ReleaseDC.return_value = 1
            with patch("cidls.ocr_pipeline.dpi_utils.ctypes") as mock_ctypes:
                mock_ctypes.windll = mock_windll
                result = get_scale_factor()
            assert isinstance(result, float)

    def test_returns_1_0_for_96_dpi(self):
        with patch("cidls.ocr_pipeline.dpi_utils.sys") as mock_sys:
            mock_sys.platform = "win32"
            mock_windll = MagicMock()
            mock_windll.user32.GetDC.return_value = 1
            mock_windll.gdi32.GetDeviceCaps.return_value = 96
            mock_windll.user32.ReleaseDC.return_value = 1
            with patch("cidls.ocr_pipeline.dpi_utils.ctypes") as mock_ctypes:
                mock_ctypes.windll = mock_windll
                result = get_scale_factor()
            assert result == pytest.approx(1.0)

    def test_returns_1_25_for_120_dpi(self):
        with patch("cidls.ocr_pipeline.dpi_utils.sys") as mock_sys:
            mock_sys.platform = "win32"
            mock_windll = MagicMock()
            mock_windll.user32.GetDC.return_value = 1
            mock_windll.gdi32.GetDeviceCaps.return_value = 120
            mock_windll.user32.ReleaseDC.return_value = 1
            with patch("cidls.ocr_pipeline.dpi_utils.ctypes") as mock_ctypes:
                mock_ctypes.windll = mock_windll
                result = get_scale_factor()
            assert result == pytest.approx(1.25)

    def test_returns_1_5_for_144_dpi(self):
        with patch("cidls.ocr_pipeline.dpi_utils.sys") as mock_sys:
            mock_sys.platform = "win32"
            mock_windll = MagicMock()
            mock_windll.user32.GetDC.return_value = 1
            mock_windll.gdi32.GetDeviceCaps.return_value = 144
            mock_windll.user32.ReleaseDC.return_value = 1
            with patch("cidls.ocr_pipeline.dpi_utils.ctypes") as mock_ctypes:
                mock_ctypes.windll = mock_windll
                result = get_scale_factor()
            assert result == pytest.approx(1.5)

    def test_returns_float_gte_1_on_win32(self):
        with patch("cidls.ocr_pipeline.dpi_utils.sys") as mock_sys:
            mock_sys.platform = "win32"
            mock_windll = MagicMock()
            mock_windll.user32.GetDC.return_value = 1
            mock_windll.gdi32.GetDeviceCaps.return_value = 96
            mock_windll.user32.ReleaseDC.return_value = 1
            with patch("cidls.ocr_pipeline.dpi_utils.ctypes") as mock_ctypes:
                mock_ctypes.windll = mock_windll
                result = get_scale_factor()
            assert result >= 1.0

    def test_returns_1_0_on_non_win32(self):
        with patch("cidls.ocr_pipeline.dpi_utils.sys") as mock_sys:
            mock_sys.platform = "linux"
            result = get_scale_factor()
        assert result == 1.0

    def test_returns_1_0_on_error(self):
        with patch("cidls.ocr_pipeline.dpi_utils.sys") as mock_sys:
            mock_sys.platform = "win32"
            with patch("cidls.ocr_pipeline.dpi_utils.ctypes") as mock_ctypes:
                mock_ctypes.windll.user32.GetDC.side_effect = OSError("mock error")
                result = get_scale_factor()
            assert result == 1.0


# ---------------------------------------------------------------------------
# set_dpi_aware
# ---------------------------------------------------------------------------

class TestSetDpiAware:
    def test_returns_false_on_non_win32(self):
        with patch("cidls.ocr_pipeline.dpi_utils.sys") as mock_sys:
            mock_sys.platform = "linux"
            result = set_dpi_aware()
        assert result is False

    def test_returns_true_on_win32_with_shcore(self):
        with patch("cidls.ocr_pipeline.dpi_utils.sys") as mock_sys:
            mock_sys.platform = "win32"
            with patch("cidls.ocr_pipeline.dpi_utils.ctypes") as mock_ctypes:
                mock_ctypes.windll.shcore.SetProcessDpiAwareness.return_value = 0
                result = set_dpi_aware()
            assert result is True

    def test_returns_true_via_user32_fallback(self):
        with patch("cidls.ocr_pipeline.dpi_utils.sys") as mock_sys:
            mock_sys.platform = "win32"
            with patch("cidls.ocr_pipeline.dpi_utils.ctypes") as mock_ctypes:
                mock_ctypes.windll.shcore.SetProcessDpiAwareness.side_effect = OSError("not available")
                mock_ctypes.windll.user32.SetProcessDPIAware.return_value = 1
                result = set_dpi_aware()
            assert result is True

    def test_returns_false_when_all_fail(self):
        with patch("cidls.ocr_pipeline.dpi_utils.sys") as mock_sys:
            mock_sys.platform = "win32"
            with patch("cidls.ocr_pipeline.dpi_utils.ctypes") as mock_ctypes:
                mock_ctypes.windll.shcore.SetProcessDpiAwareness.side_effect = OSError("fail")
                mock_ctypes.windll.user32.SetProcessDPIAware.side_effect = OSError("fail")
                result = set_dpi_aware()
            assert result is False

    def test_return_type_is_bool(self):
        with patch("cidls.ocr_pipeline.dpi_utils.sys") as mock_sys:
            mock_sys.platform = "linux"
            result = set_dpi_aware()
        assert isinstance(result, bool)
