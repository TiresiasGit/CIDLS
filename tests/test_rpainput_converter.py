from cidls.ocr_pipeline.models import CaptureRequest, OCRRawResult
from cidls.ocr_pipeline.ocr_result_parser import OCRResultParser
from cidls.ocr_pipeline.rpainput_converter import RPAInputConverter


def test_converter_builds_rpainput_payload():
    capture_request = CaptureRequest(
        source_mode="screen_region",
        region={"left": 10, "top": 20, "width": 300, "height": 160},
    )
    raw_result = OCRRawResult(
        adapter_name="snipping_tool",
        raw_text="氏名: 山田 花子\n部署: 営業企画\n項目 | 値\n金額 | ¥128,000",
        capture_image_path="reports/capture.png",
    )

    parser = OCRResultParser()
    parsed = parser.parse(raw_result)
    report = RPAInputConverter().convert(capture_request, raw_result, parsed)
    payload = report.to_dict()

    assert payload["structured_input"]["format_version"] == "cidls.rpainput.v1"
    assert payload["structured_input"]["source"]["adapter"] == "snipping_tool"
    assert payload["structured_input"]["inputs"]["key_values"][0]["key"] == "氏名"
    assert payload["structured_input"]["inputs"]["rows"][0]["cells"] == ["項目", "値"]
