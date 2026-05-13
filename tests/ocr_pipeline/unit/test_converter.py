"""
Unit tests for RPAInputConverter.

Covers:
- convert with key_values produces correct payload
- convert with rows produces correct rows
- convert with empty result produces warnings
- to_dict output structure validation
- format_version is "cidls.rpainput.v1"
- None parsed_result raises ConversionError
"""

import pytest

from cidls.ocr_pipeline.exceptions import ConversionError
from cidls.ocr_pipeline.models import CaptureRequest, ConversionReport, OCRRawResult, StructuredInput
from cidls.ocr_pipeline.ocr_result_parser import OCRResultParser
from cidls.ocr_pipeline.rpainput_converter import RPAInputConverter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(
    source_mode="screen_region",
    region=None,
    image_path="",
    language_hint="ja-JP",
    idempotency_key="test-key",
):
    if source_mode == "screen_region":
        region = region or {"left": 0, "top": 0, "width": 100, "height": 50}
        return CaptureRequest(
            source_mode=source_mode,
            region=region,
            language_hint=language_hint,
            idempotency_key=idempotency_key,
        )
    return CaptureRequest(
        source_mode=source_mode,
        image_path=image_path,
        language_hint=language_hint,
        idempotency_key=idempotency_key,
    )


def _make_raw(text: str, adapter_name: str = "test_adapter", capture_image_path: str = "") -> OCRRawResult:
    return OCRRawResult(
        adapter_name=adapter_name,
        raw_text=text,
        capture_image_path=capture_image_path,
    )


def _parse(raw: OCRRawResult) -> dict:
    return OCRResultParser().parse(raw)


# ---------------------------------------------------------------------------
# Core conversion tests
# ---------------------------------------------------------------------------

class TestRPAInputConverterConvert:
    def setup_method(self):
        self.converter = RPAInputConverter()

    def test_returns_conversion_report_instance(self):
        request = _make_request()
        raw = _make_raw("name: Alice")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        assert isinstance(report, ConversionReport)

    def test_format_version_is_cidls_rpainput_v1(self):
        request = _make_request()
        raw = _make_raw("name: Alice")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        payload = report.to_dict()
        assert payload["structured_input"]["format_version"] == "cidls.rpainput.v1"

    def test_convert_with_key_values_produces_correct_payload(self):
        request = _make_request()
        raw = _make_raw("氏名: 山田 花子\n部署: 営業企画", adapter_name="snipping_tool")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        payload = report.to_dict()

        kv_list = payload["structured_input"]["inputs"]["key_values"]
        assert len(kv_list) == 2
        keys = [item["key"] for item in kv_list]
        assert "氏名" in keys
        assert "部署" in keys

    def test_key_values_value_correct(self):
        request = _make_request()
        raw = _make_raw("氏名: 山田 花子")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        payload = report.to_dict()
        kv = payload["structured_input"]["inputs"]["key_values"][0]
        assert kv["value"] == "山田 花子"

    def test_convert_with_rows_produces_correct_rows(self):
        request = _make_request()
        raw = _make_raw("項目 | 値 | 状態\n依頼区分 | 契約更新 | 進行中")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        payload = report.to_dict()

        rows = payload["structured_input"]["inputs"]["rows"]
        assert len(rows) == 2
        assert rows[0]["cells"] == ["項目", "値", "状態"]
        assert rows[1]["cells"] == ["依頼区分", "契約更新", "進行中"]

    def test_convert_with_empty_result_produces_warnings(self):
        request = _make_request()
        raw = _make_raw("   ")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        payload = report.to_dict()
        assert "ocr_result_empty" in payload["structured_input"]["metadata"]["warnings"]

    def test_structured_signal_low_warning_propagated(self):
        request = _make_request()
        raw = _make_raw("This is just plain prose with no structure.")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        payload = report.to_dict()
        assert "structured_signal_low" in payload["structured_input"]["metadata"]["warnings"]

    def test_none_parsed_result_raises_conversion_error(self):
        request = _make_request()
        raw = _make_raw("name: Alice")
        with pytest.raises(ConversionError):
            self.converter.convert(request, raw, None)

    def test_source_mode_recorded_in_payload(self):
        request = _make_request(source_mode="screen_region")
        raw = _make_raw("name: Alice")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        payload = report.to_dict()
        assert payload["structured_input"]["source"]["mode"] == "screen_region"

    def test_adapter_name_recorded_in_payload(self):
        request = _make_request()
        raw = _make_raw("name: Alice", adapter_name="winocr")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        payload = report.to_dict()
        assert payload["structured_input"]["source"]["adapter"] == "winocr"

    def test_language_hint_recorded_in_payload(self):
        request = _make_request(language_hint="en-US")
        raw = _make_raw("name: Alice")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        payload = report.to_dict()
        assert payload["structured_input"]["source"]["language_hint"] == "en-US"

    def test_capture_image_path_recorded_in_payload(self):
        request = _make_request()
        raw = _make_raw("name: Alice", capture_image_path="reports/capture.png")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        payload = report.to_dict()
        assert payload["structured_input"]["source"]["capture_image_path"] == "reports/capture.png"

    def test_lines_present_in_inputs(self):
        request = _make_request()
        raw = _make_raw("name: Alice\ncity: Tokyo")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        payload = report.to_dict()
        lines = payload["structured_input"]["inputs"]["lines"]
        assert len(lines) == 2
        assert all("line_index" in line and "text" in line for line in lines)

    def test_lines_line_index_sequential(self):
        request = _make_request()
        raw = _make_raw("a: b\nc: d\ne: f")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        payload = report.to_dict()
        indices = [line["line_index"] for line in payload["structured_input"]["inputs"]["lines"]]
        assert indices == [0, 1, 2]

    def test_request_fingerprint_present_in_metadata(self):
        request = _make_request()
        raw = _make_raw("name: Alice")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        payload = report.to_dict()
        assert "request_fingerprint" in payload["structured_input"]["metadata"]
        assert isinstance(payload["structured_input"]["metadata"]["request_fingerprint"], str)
        assert len(payload["structured_input"]["metadata"]["request_fingerprint"]) > 0

    def test_ocr_attempts_recorded_in_metadata(self):
        request = _make_request()
        raw = OCRRawResult(adapter_name="test", raw_text="name: Alice", attempts=3)
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        payload = report.to_dict()
        assert payload["structured_input"]["metadata"]["ocr_attempts"] == 3

    def test_ocr_blocks_from_raw_result_included(self):
        request = _make_request()
        blocks = [{"text": "block1", "bbox": [0, 0, 100, 20]}]
        raw = OCRRawResult(adapter_name="test", raw_text="name: Alice", blocks=blocks)
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        payload = report.to_dict()
        assert payload["structured_input"]["inputs"]["ocr_blocks"] == blocks


# ---------------------------------------------------------------------------
# ConversionReport structure validation
# ---------------------------------------------------------------------------

class TestConversionReportStructure:
    def setup_method(self):
        self.converter = RPAInputConverter()

    def test_to_dict_has_required_top_level_keys(self):
        request = _make_request()
        raw = _make_raw("name: Alice\nA | B")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        result = report.to_dict()

        required_keys = {"structured_input", "normalized_text", "key_values", "rows", "warnings", "metadata"}
        assert required_keys.issubset(result.keys())

    def test_normalized_text_matches_parser_output(self):
        request = _make_request()
        raw = _make_raw("name: Alice")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        result = report.to_dict()
        assert result["normalized_text"] == parsed["normalized_text"]

    def test_key_values_list_matches_parser_output(self):
        request = _make_request()
        raw = _make_raw("name: Alice")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        result = report.to_dict()
        assert result["key_values"] == parsed["key_values"]

    def test_rows_list_matches_parser_output(self):
        request = _make_request()
        raw = _make_raw("A | B | C")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        result = report.to_dict()
        assert result["rows"] == parsed["rows"]

    def test_warnings_list_matches_parser_output(self):
        request = _make_request()
        raw = _make_raw("   ")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        result = report.to_dict()
        assert result["warnings"] == parsed["warnings"]

    def test_metadata_matches_parser_output(self):
        request = _make_request()
        raw = _make_raw("name: Alice")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        result = report.to_dict()
        assert result["metadata"] == parsed["metadata"]

    def test_structured_input_is_dict(self):
        request = _make_request()
        raw = _make_raw("name: Alice")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        result = report.to_dict()
        assert isinstance(result["structured_input"], dict)

    def test_structured_input_has_required_sections(self):
        request = _make_request()
        raw = _make_raw("name: Alice")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        si = report.to_dict()["structured_input"]
        assert "format_version" in si
        assert "source" in si
        assert "inputs" in si
        assert "metadata" in si

    def test_inputs_section_has_required_keys(self):
        request = _make_request()
        raw = _make_raw("name: Alice")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        inputs = report.to_dict()["structured_input"]["inputs"]
        assert "lines" in inputs
        assert "key_values" in inputs
        assert "rows" in inputs
        assert "ocr_blocks" in inputs

    def test_structured_input_is_structured_input_instance(self):
        request = _make_request()
        raw = _make_raw("name: Alice")
        parsed = _parse(raw)
        report = self.converter.convert(request, raw, parsed)
        assert isinstance(report.structured_input, StructuredInput)
