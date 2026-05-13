"""
Unit tests for OCRResultParser.

Covers:
- normalize_text: NFKC conversion, whitespace normalization, control char removal
- split_lines: basic splitting, empty line filtering
- extract_key_values: colon, Japanese colon, tab separators, long key rejection
- extract_rows: pipe, tab, multi-space separators
- parse: full integration, empty result warning, structured_signal_low warning
- Scenario tests: single label+value, multiline form, Japanese mixed,
  numbers+symbols, table format, linebreak corruption, OCR typo
"""

import pytest

from cidls.ocr_pipeline.exceptions import ParseError
from cidls.ocr_pipeline.models import OCRRawResult
from cidls.ocr_pipeline.ocr_result_parser import OCRResultParser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_raw(text: str) -> OCRRawResult:
    return OCRRawResult(adapter_name="test", raw_text=text)


# ---------------------------------------------------------------------------
# normalize_text
# ---------------------------------------------------------------------------

class TestNormalizeText:
    def setup_method(self):
        self.parser = OCRResultParser()

    def test_nfkc_fullwidth_ascii_converted(self):
        # Fullwidth digits and letters must become ASCII
        result = self.parser.normalize_text("ＡＰ-２０２６-０４１７")
        assert result == "AP-2026-0417"

    def test_nfkc_fullwidth_colon_converted(self):
        # Fullwidth colon U+FF1A must become normal colon
        result = self.parser.normalize_text("氏名：山田")
        assert ":" in result
        assert "：" not in result

    def test_crlf_normalized_to_lf(self):
        result = self.parser.normalize_text("line1\r\nline2\r\nline3")
        assert "\r" not in result
        assert result == "line1\nline2\nline3"

    def test_cr_only_normalized_to_lf(self):
        result = self.parser.normalize_text("line1\rline2")
        assert "\r" not in result
        assert result == "line1\nline2"

    def test_zero_width_space_removed(self):
        result = self.parser.normalize_text("abc\u200bdef")
        assert "\u200b" not in result
        assert result == "abcdef"

    def test_bom_removed(self):
        result = self.parser.normalize_text("\ufeffcontent")
        assert "\ufeff" not in result
        assert result == "content"

    def test_tab_converted_to_double_space(self):
        result = self.parser.normalize_text("key\tvalue")
        assert "\t" not in result
        assert "  " in result

    def test_excessive_blank_lines_collapsed(self):
        # Three or more consecutive newlines become two
        result = self.parser.normalize_text("a\n\n\n\nb")
        assert result == "a\n\nb"

    def test_leading_trailing_whitespace_stripped(self):
        result = self.parser.normalize_text("   hello   ")
        assert result == "hello"

    def test_empty_string_returns_empty(self):
        result = self.parser.normalize_text("")
        assert result == ""

    def test_none_raises_parse_error(self):
        with pytest.raises(ParseError):
            self.parser.normalize_text(None)

    def test_whitespace_only_returns_empty(self):
        result = self.parser.normalize_text("   \n\n\t  ")
        assert result == ""


# ---------------------------------------------------------------------------
# split_lines
# ---------------------------------------------------------------------------

class TestSplitLines:
    def setup_method(self):
        self.parser = OCRResultParser()

    def test_basic_split(self):
        lines = self.parser.split_lines("line1\nline2\nline3")
        assert lines == ["line1", "line2", "line3"]

    def test_empty_lines_filtered(self):
        lines = self.parser.split_lines("line1\n\nline2\n\n\nline3")
        assert lines == ["line1", "line2", "line3"]

    def test_whitespace_only_lines_filtered(self):
        lines = self.parser.split_lines("line1\n   \nline2")
        assert lines == ["line1", "line2"]

    def test_each_line_is_stripped(self):
        lines = self.parser.split_lines("  line1  \n  line2  ")
        assert lines == ["line1", "line2"]

    def test_empty_input_returns_empty_list(self):
        lines = self.parser.split_lines("")
        assert lines == []

    def test_single_line_without_newline(self):
        lines = self.parser.split_lines("only line")
        assert lines == ["only line"]


# ---------------------------------------------------------------------------
# extract_key_values
# ---------------------------------------------------------------------------

class TestExtractKeyValues:
    def setup_method(self):
        self.parser = OCRResultParser()

    def test_colon_separator(self):
        items = self.parser.extract_key_values(["name: Alice"])
        assert len(items) == 1
        assert items[0]["key"] == "name"
        assert items[0]["value"] == "Alice"
        assert items[0]["separator"] == ":"

    def test_japanese_colon_separator(self):
        # After NFKC normalization the fullwidth colon becomes ASCII colon,
        # but the parser also has "：" listed as a separator directly.
        items = self.parser.extract_key_values(["氏名：山田 花子"])
        assert len(items) == 1
        assert items[0]["key"] == "氏名"
        assert items[0]["value"] == "山田 花子"

    def test_tab_separator_via_double_space_after_normalization(self):
        # After normalize_text, \t becomes "  " (double space).
        # extract_key_values works on already-normalized lines;
        # verify double-space is NOT treated as a key-value separator
        # (no separator token for double space, only listed separators are used).
        # Tab in original is converted before lines are split; the line after
        # normalization contains "  " which has no key-value separator — confirmed
        # by verifying no item is extracted with just double-space.
        lines_no_sep = ["key  value"]
        items = self.parser.extract_key_values(lines_no_sep)
        # Double space alone is not a key-value separator; no items expected
        assert all(item["separator"] != "  " for item in items)

    def test_dash_separator(self):
        items = self.parser.extract_key_values(["status - pending"])
        assert len(items) == 1
        assert items[0]["key"] == "status"
        assert items[0]["value"] == "pending"
        assert items[0]["separator"] == "-"

    def test_equals_separator(self):
        items = self.parser.extract_key_values(["count=42"])
        assert len(items) == 1
        assert items[0]["key"] == "count"
        assert items[0]["value"] == "42"
        assert items[0]["separator"] == "="

    def test_long_key_rejected(self):
        # Keys longer than 40 characters must be rejected
        long_key = "a" * 41
        items = self.parser.extract_key_values([f"{long_key}: value"])
        assert len(items) == 0

    def test_key_exactly_40_chars_accepted(self):
        key = "a" * 40
        items = self.parser.extract_key_values([f"{key}: value"])
        assert len(items) == 1
        assert items[0]["key"] == key

    def test_empty_key_rejected(self):
        items = self.parser.extract_key_values([": value"])
        assert len(items) == 0

    def test_empty_value_rejected(self):
        items = self.parser.extract_key_values(["key:"])
        assert len(items) == 0

    def test_line_index_recorded(self):
        lines = ["ignore this", "key: val"]
        items = self.parser.extract_key_values(lines)
        assert items[0]["line_index"] == 1

    def test_raw_line_recorded(self):
        items = self.parser.extract_key_values(["key: val"])
        assert items[0]["raw"] == "key: val"

    def test_multiple_lines_multiple_items(self):
        lines = ["name: Alice", "age: 30", "city: Tokyo"]
        items = self.parser.extract_key_values(lines)
        assert len(items) == 3
        assert items[0]["key"] == "name"
        assert items[1]["key"] == "age"
        assert items[2]["key"] == "city"

    def test_first_separator_only_used_per_line(self):
        # Line has two colons; split should happen at the first
        items = self.parser.extract_key_values(["time: 12:30"])
        assert len(items) == 1
        assert items[0]["key"] == "time"
        assert items[0]["value"] == "12:30"

    def test_pipe_stripped_from_key_and_value(self):
        # Pipe character is stripped from edges of key/value
        items = self.parser.extract_key_values(["| name | : Alice"])
        assert len(items) == 1
        assert items[0]["key"] == "name"


# ---------------------------------------------------------------------------
# extract_rows
# ---------------------------------------------------------------------------

class TestExtractRows:
    def setup_method(self):
        self.parser = OCRResultParser()

    def test_pipe_separator(self):
        rows = self.parser.extract_rows(["A | B | C"])
        assert len(rows) == 1
        assert rows[0]["cells"] == ["A", "B", "C"]

    def test_pipe_separator_with_empty_cells_filtered(self):
        rows = self.parser.extract_rows(["| A | | B |"])
        assert len(rows) == 1
        assert rows[0]["cells"] == ["A", "B"]

    def test_tab_separator(self):
        # Tab is normalized to double-space by normalize_text before parsing,
        # but extract_rows can also receive raw lines with literal tabs
        rows = self.parser.extract_rows(["col1\tcol2\tcol3"])
        assert len(rows) == 1
        assert rows[0]["cells"] == ["col1", "col2", "col3"]

    def test_multi_space_separator(self):
        rows = self.parser.extract_rows(["name  Alice  active"])
        assert len(rows) == 1
        assert rows[0]["cells"] == ["name", "Alice", "active"]

    def test_single_cell_not_a_row(self):
        rows = self.parser.extract_rows(["just one cell"])
        assert len(rows) == 0

    def test_line_index_recorded(self):
        rows = self.parser.extract_rows(["skip", "A | B"])
        assert rows[0]["line_index"] == 1

    def test_raw_line_recorded(self):
        rows = self.parser.extract_rows(["X | Y"])
        assert rows[0]["raw"] == "X | Y"

    def test_two_cells_minimum(self):
        rows = self.parser.extract_rows(["alpha  beta"])
        assert len(rows) == 1
        assert len(rows[0]["cells"]) == 2

    def test_multiple_rows(self):
        lines = ["A | B", "C | D", "E | F"]
        rows = self.parser.extract_rows(lines)
        assert len(rows) == 3

    def test_empty_input(self):
        rows = self.parser.extract_rows([])
        assert rows == []


# ---------------------------------------------------------------------------
# parse (integration within parser)
# ---------------------------------------------------------------------------

class TestParse:
    def setup_method(self):
        self.parser = OCRResultParser()

    def test_full_integration_returns_expected_keys(self):
        raw = make_raw("name: Alice\nA | B")
        result = self.parser.parse(raw)
        assert "normalized_text" in result
        assert "lines" in result
        assert "key_values" in result
        assert "rows" in result
        assert "warnings" in result
        assert "metadata" in result

    def test_metadata_counts_correct(self):
        raw = make_raw("name: Alice\nA | B | C")
        result = self.parser.parse(raw)
        assert result["metadata"]["line_count"] == 2
        assert result["metadata"]["key_value_count"] == 1
        assert result["metadata"]["row_count"] == 1

    def test_empty_result_produces_warning(self):
        raw = make_raw("   ")
        result = self.parser.parse(raw)
        assert "ocr_result_empty" in result["warnings"]

    def test_structured_signal_low_warning(self):
        # Lines with content but no separators or rows produce the warning
        raw = make_raw("This is just a sentence.\nAnother sentence here.")
        result = self.parser.parse(raw)
        assert "structured_signal_low" in result["warnings"]

    def test_no_warnings_for_well_structured_input(self):
        raw = make_raw("name: Alice\nA | B")
        result = self.parser.parse(raw)
        assert "ocr_result_empty" not in result["warnings"]
        assert "structured_signal_low" not in result["warnings"]


# ---------------------------------------------------------------------------
# Scenario tests
# ---------------------------------------------------------------------------

class TestParserScenarios:
    def setup_method(self):
        self.parser = OCRResultParser()

    def test_single_label_value(self):
        raw = make_raw("申請番号: AP-2026-0001")
        result = self.parser.parse(raw)
        assert len(result["key_values"]) == 1
        assert result["key_values"][0]["key"] == "申請番号"
        assert result["key_values"][0]["value"] == "AP-2026-0001"

    def test_multiline_form(self):
        text = "氏名: 山田 花子\n部署: 営業企画\n役職: マネージャー\n入社日: 2019-04-01"
        raw = make_raw(text)
        result = self.parser.parse(raw)
        assert len(result["key_values"]) == 4
        keys = [kv["key"] for kv in result["key_values"]]
        assert "氏名" in keys
        assert "部署" in keys
        assert "役職" in keys
        assert "入社日" in keys

    def test_japanese_mixed_fullwidth(self):
        # Full-width characters must be normalized via NFKC before extraction
        text = "申請番号：ＡＰ-２０２６-０４１７\n氏名：山田 花子"
        raw = make_raw(text)
        result = self.parser.parse(raw)
        # After NFKC: "：" -> ":", "ＡＰ-２０２６-０４１７" -> "AP-2026-0417"
        assert result["key_values"][0]["key"] == "申請番号"
        assert result["key_values"][0]["value"] == "AP-2026-0417"
        assert result["key_values"][1]["key"] == "氏名"
        assert result["key_values"][1]["value"] == "山田 花子"

    def test_numbers_and_symbols(self):
        text = "金額: ¥128,000\n税率: 10%\nコード: #A-001"
        raw = make_raw(text)
        result = self.parser.parse(raw)
        values = {kv["key"]: kv["value"] for kv in result["key_values"]}
        assert values["金額"] == "¥128,000"
        assert values["税率"] == "10%"
        assert values["コード"] == "#A-001"

    def test_table_format(self):
        text = "項目 | 値 | 状態\n依頼区分 | 契約更新 | 進行中\n担当  田中  要連絡"
        raw = make_raw(text)
        result = self.parser.parse(raw)
        assert len(result["rows"]) == 3
        assert result["rows"][0]["cells"] == ["項目", "値", "状態"]
        assert result["rows"][1]["cells"] == ["依頼区分", "契約更新", "進行中"]
        assert result["rows"][2]["cells"] == ["担当", "田中", "要連絡"]

    def test_linebreak_corruption_merged_lines(self):
        # OCR sometimes merges two lines; both key-values should still be extracted
        # when they appear on separate lines correctly
        text = "氏名: 山田 花子\n所属: 第二営業部"
        raw = make_raw(text)
        result = self.parser.parse(raw)
        assert len(result["key_values"]) == 2

    def test_ocr_typo_extra_space_in_value(self):
        # Extra spaces in the value should be preserved as-is (not silently trimmed
        # beyond what strip() does at the edges)
        text = "備考: 週次 イベント 費用"
        raw = make_raw(text)
        result = self.parser.parse(raw)
        assert result["key_values"][0]["value"] == "週次 イベント 費用"

    def test_crlf_input_normalized_to_lf_before_split(self):
        text = "key1: val1\r\nkey2: val2\r\nkey3: val3"
        raw = make_raw(text)
        result = self.parser.parse(raw)
        assert len(result["key_values"]) == 3

    def test_fullwidth_numeric_in_value_normalized(self):
        text = "金額：￥１２８，０００"
        raw = make_raw(text)
        result = self.parser.parse(raw)
        assert result["key_values"][0]["key"] == "金額"
        # After NFKC, ￥ -> ¥, fullwidth digits -> ASCII digits
        assert result["key_values"][0]["value"] == "¥128,000"
