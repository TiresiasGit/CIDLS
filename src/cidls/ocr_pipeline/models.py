import hashlib
import json
from pathlib import Path

from .exceptions import ConversionError, UnsupportedCaptureModeError


def _normalize_region(region):
    if not region:
        return {}
    keys = ["left", "top", "width", "height"]
    normalized = {}
    for key in keys:
        if key not in region:
            raise ConversionError("region must include left, top, width, height")
        value = int(region[key])
        if value < 0:
            raise ConversionError("region values must be zero or positive")
        normalized[key] = value
    if normalized["width"] <= 0 or normalized["height"] <= 0:
        raise ConversionError("region width and height must be positive")
    return normalized


class CaptureRequest:
    VALID_SOURCE_MODES = {"screen_region", "image_file"}
    VALID_OUTPUT_FORMATS = {"json", "csv", "dto"}

    def __init__(
        self,
        source_mode,
        region=None,
        image_path="",
        output_format="json",
        language_hint="ja-JP",
        idempotency_key="",
        preferred_adapter="snipping_tool",
        fallback_adapter="powertoys_text_extractor",
        secure_mode=False,
        metadata=None,
        retry_count=2,
        timeout_seconds=20,
    ):
        self.source_mode = str(source_mode or "").strip()
        self.region = _normalize_region(region)
        self.image_path = str(image_path or "").strip()
        self.output_format = str(output_format or "json").strip()
        self.language_hint = str(language_hint or "ja-JP").strip()
        self.idempotency_key = str(idempotency_key or "").strip()
        self.preferred_adapter = str(preferred_adapter or "snipping_tool").strip()
        self.fallback_adapter = str(fallback_adapter or "powertoys_text_extractor").strip()
        self.secure_mode = bool(secure_mode)
        self.metadata = dict(metadata or {})
        self.retry_count = int(retry_count)
        self.timeout_seconds = int(timeout_seconds)
        self.preview_region = {}
        self.validate()

    def validate(self):
        if self.source_mode not in self.VALID_SOURCE_MODES:
            raise UnsupportedCaptureModeError("source_mode must be screen_region or image_file")
        if self.output_format not in self.VALID_OUTPUT_FORMATS:
            raise ConversionError("output_format must be json, csv, or dto")
        if self.source_mode == "screen_region" and not self.region:
            raise ConversionError("screen_region mode requires region")
        if self.source_mode == "image_file":
            if not self.image_path:
                raise ConversionError("image_file mode requires image_path")
            if not Path(self.image_path).exists():
                raise ConversionError(f"image file does not exist: {self.image_path}")
        if self.retry_count < 0:
            raise ConversionError("retry_count must be zero or positive")
        if self.timeout_seconds <= 0:
            raise ConversionError("timeout_seconds must be positive")
        return self

    def effective_region(self):
        if self.preview_region:
            return dict(self.preview_region)
        return dict(self.region)

    def has_effective_region(self):
        return bool(self.effective_region())

    def can_use_screen_ocr(self):
        return self.has_effective_region()

    def to_dict(self):
        return {
            "source_mode": self.source_mode,
            "region": dict(self.region),
            "image_path": self.image_path,
            "output_format": self.output_format,
            "language_hint": self.language_hint,
            "idempotency_key": self.idempotency_key,
            "preferred_adapter": self.preferred_adapter,
            "fallback_adapter": self.fallback_adapter,
            "secure_mode": self.secure_mode,
            "metadata": dict(self.metadata),
            "retry_count": self.retry_count,
            "timeout_seconds": self.timeout_seconds,
        }

    def fingerprint(self):
        payload = self.to_dict()
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha1(encoded).hexdigest()[:16]


class OCRRawResult:
    def __init__(
        self,
        adapter_name,
        raw_text,
        capture_image_path="",
        clipboard_text="",
        blocks=None,
        metadata=None,
        attempts=1,
    ):
        self.adapter_name = str(adapter_name or "").strip()
        self.raw_text = str(raw_text or "")
        self.capture_image_path = str(capture_image_path or "")
        self.clipboard_text = str(clipboard_text or "")
        self.blocks = list(blocks or [])
        self.metadata = dict(metadata or {})
        self.attempts = int(attempts)

    def to_dict(self):
        return {
            "adapter_name": self.adapter_name,
            "raw_text": self.raw_text,
            "capture_image_path": self.capture_image_path,
            "clipboard_text": self.clipboard_text,
            "blocks": list(self.blocks),
            "metadata": dict(self.metadata),
            "attempts": self.attempts,
        }


class StructuredInput:
    def __init__(self, payload):
        self.payload = dict(payload or {})

    def to_dict(self):
        return dict(self.payload)


class ConversionReport:
    def __init__(self, structured_input, normalized_text, key_values, rows, warnings=None, metadata=None):
        self.structured_input = structured_input
        self.normalized_text = str(normalized_text or "")
        self.key_values = list(key_values or [])
        self.rows = list(rows or [])
        self.warnings = list(warnings or [])
        self.metadata = dict(metadata or {})

    def to_dict(self):
        return {
            "structured_input": self.structured_input.to_dict(),
            "normalized_text": self.normalized_text,
            "key_values": list(self.key_values),
            "rows": list(self.rows),
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }
