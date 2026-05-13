import re
import unicodedata

from .exceptions import ParseError


class OCRResultParser:
    KEY_VALUE_SEPARATORS = [":", "：", "-", "−", "="]

    def normalize_text(self, raw_text):
        if raw_text is None:
            raise ParseError("raw_text must not be None")
        value = unicodedata.normalize("NFKC", str(raw_text))
        value = value.replace("\r\n", "\n").replace("\r", "\n")
        value = value.replace("\u200b", "").replace("\ufeff", "")
        value = value.replace("\t", "  ")
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value.strip()

    def split_lines(self, normalized_text):
        return [line.strip() for line in normalized_text.split("\n") if line.strip()]

    def extract_key_values(self, lines):
        items = []
        for line_index, line in enumerate(lines):
            for separator in self.KEY_VALUE_SEPARATORS:
                if separator not in line:
                    continue
                key, value = line.split(separator, 1)
                key = key.strip(" |")
                value = value.strip(" |")
                if len(key) < 1 or len(value) < 1:
                    continue
                if len(key) > 40:
                    continue
                items.append({
                    "key": key,
                    "value": value,
                    "line_index": line_index,
                    "separator": separator,
                    "raw": line,
                })
                break
        return items

    def extract_rows(self, lines):
        rows = []
        for line_index, line in enumerate(lines):
            if "|" in line:
                cells = [cell.strip() for cell in line.split("|") if cell.strip()]
            elif "\t" in line:
                cells = [cell.strip() for cell in line.split("\t") if cell.strip()]
            else:
                cells = [cell.strip() for cell in re.split(r"\s{2,}", line) if cell.strip()]
            if len(cells) >= 2:
                rows.append({
                    "line_index": line_index,
                    "cells": cells,
                    "raw": line,
                })
        return rows

    def parse(self, ocr_raw_result):
        normalized_text = self.normalize_text(ocr_raw_result.raw_text)
        lines = self.split_lines(normalized_text)
        key_values = self.extract_key_values(lines)
        rows = self.extract_rows(lines)
        warnings = []
        if not normalized_text:
            warnings.append("ocr_result_empty")
        if not key_values and not rows and lines:
            warnings.append("structured_signal_low")
        return {
            "normalized_text": normalized_text,
            "lines": lines,
            "key_values": key_values,
            "rows": rows,
            "warnings": warnings,
            "metadata": {
                "line_count": len(lines),
                "key_value_count": len(key_values),
                "row_count": len(rows),
            },
        }
