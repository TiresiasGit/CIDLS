from cidls.ocr_pipeline.models import OCRRawResult
from cidls.ocr_pipeline.ocr_result_parser import OCRResultParser


def test_normalize_and_extract_key_values():
    parser = OCRResultParser()
    raw = OCRRawResult(
        adapter_name="fake",
        raw_text="申請番号：ＡＰ-２０２６-０４１７\r\n氏名 : 山田 花子\r\n金額  ¥128,000\r\n備考: 週次イベント費用",
    )

    parsed = parser.parse(raw)

    assert parsed["normalized_text"].startswith("申請番号:AP-2026-0417")
    assert parsed["key_values"][0]["key"] == "申請番号"
    assert parsed["key_values"][0]["value"] == "AP-2026-0417"
    assert parsed["key_values"][1]["key"] == "氏名"
    assert parsed["key_values"][1]["value"] == "山田 花子"


def test_extract_rows_from_pipe_and_space_delimited_text():
    parser = OCRResultParser()
    raw = OCRRawResult(
        adapter_name="fake",
        raw_text="項目 | 値 | 状態\n依頼区分 | 契約更新 | 進行中\n担当  田中  要連絡",
    )

    parsed = parser.parse(raw)

    assert len(parsed["rows"]) == 3
    assert parsed["rows"][0]["cells"] == ["項目", "値", "状態"]
    assert parsed["rows"][2]["cells"] == ["担当", "田中", "要連絡"]


def test_empty_result_emits_warning():
    parser = OCRResultParser()
    raw = OCRRawResult(adapter_name="fake", raw_text="   ")
    parsed = parser.parse(raw)
    assert "ocr_result_empty" in parsed["warnings"]
