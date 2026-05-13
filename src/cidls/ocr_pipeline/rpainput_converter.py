from .exceptions import ConversionError
from .models import ConversionReport, StructuredInput


class RPAInputConverter:
    def convert(self, capture_request, ocr_raw_result, parsed_result):
        if parsed_result is None:
            raise ConversionError("parsed_result must not be None")
        payload = {
            "format_version": "cidls.rpainput.v1",
            "source": {
                "mode": capture_request.source_mode,
                "adapter": ocr_raw_result.adapter_name,
                "language_hint": capture_request.language_hint,
                "capture_image_path": ocr_raw_result.capture_image_path,
            },
            "inputs": {
                "lines": [
                    {
                        "line_index": index,
                        "text": line,
                    }
                    for index, line in enumerate(parsed_result.get("lines", []))
                ],
                "key_values": list(parsed_result.get("key_values", [])),
                "rows": list(parsed_result.get("rows", [])),
                "ocr_blocks": list(ocr_raw_result.blocks or []),
            },
            "metadata": {
                "warnings": list(parsed_result.get("warnings", [])),
                "ocr_attempts": ocr_raw_result.attempts,
                "request_fingerprint": capture_request.fingerprint(),
            },
        }
        structured = StructuredInput(payload)
        return ConversionReport(
            structured_input=structured,
            normalized_text=parsed_result.get("normalized_text", ""),
            key_values=parsed_result.get("key_values", []),
            rows=parsed_result.get("rows", []),
            warnings=parsed_result.get("warnings", []),
            metadata=parsed_result.get("metadata", {}),
        )
