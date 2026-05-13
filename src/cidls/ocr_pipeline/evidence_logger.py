import csv
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


def _utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class EvidenceRun:
    def __init__(self, root_dir, capture_request, adapter_name, secure_mode=False, mask_patterns=None):
        self.root_dir = Path(root_dir)
        self.capture_request = capture_request
        self.adapter_name = adapter_name
        self.secure_mode = bool(secure_mode)
        self.mask_patterns = list(mask_patterns or [])
        self.retry_events = []
        self.error_events = []
        self.started_at = _utc_now()
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.root_dir / "manifest.json"
        self._write_manifest("started")

    def _mask(self, text):
        if text is None:
            return ""
        value = str(text)
        for pattern in self.mask_patterns:
            value = re.sub(pattern, "[MASKED]", value)
        return value

    def _write_text(self, target_path, text):
        content = self._mask(text) if self.secure_mode else str(text or "")
        tmp_path = Path(f"{target_path}.tmp")
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(target_path)
        return str(target_path)

    def _write_json(self, target_path, payload):
        content = json.dumps(payload, ensure_ascii=False, indent=2)
        return self._write_text(target_path, content)

    def _write_manifest(self, status):
        manifest = {
            "status": status,
            "started_at_utc": self.started_at,
            "updated_at_utc": _utc_now(),
            "adapter_name": self.adapter_name,
            "secure_mode": self.secure_mode,
            "capture_request": self.capture_request.to_dict(),
            "retry_events": list(self.retry_events),
            "error_events": list(self.error_events),
        }
        self._write_json(self.manifest_path, manifest)

    def save_capture_image(self, image_path):
        image_path = Path(image_path)
        if not image_path.exists():
            return ""
        target_path = self.root_dir / "capture.png"
        shutil.copyfile(image_path, target_path)
        return str(target_path)

    def save_raw_text(self, raw_text):
        return self._write_text(self.root_dir / "ocr_raw.txt", raw_text)

    def save_structured(self, conversion_report):
        payload = conversion_report.to_dict()
        json_path = self.root_dir / "structured_input.json"
        self._write_json(json_path, payload)

        csv_path = self.root_dir / "structured_input.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["kind", "key", "value", "line_index", "row_index", "raw"])
            writer.writeheader()
            for index, item in enumerate(conversion_report.key_values):
                writer.writerow({
                    "kind": "key_value",
                    "key": self._mask(item.get("key", "")) if self.secure_mode else item.get("key", ""),
                    "value": self._mask(item.get("value", "")) if self.secure_mode else item.get("value", ""),
                    "line_index": item.get("line_index", ""),
                    "row_index": "",
                    "raw": self._mask(item.get("raw", "")) if self.secure_mode else item.get("raw", ""),
                })
            for index, item in enumerate(conversion_report.rows):
                writer.writerow({
                    "kind": "row",
                    "key": "",
                    "value": self._mask(" | ".join(item.get("cells", []))) if self.secure_mode else " | ".join(item.get("cells", [])),
                    "line_index": item.get("line_index", ""),
                    "row_index": index,
                    "raw": self._mask(item.get("raw", "")) if self.secure_mode else item.get("raw", ""),
                })
        return str(json_path), str(csv_path)

    def save_failure_screenshot(self, image_path):
        image_path = Path(image_path)
        if not image_path.exists():
            return ""
        target_path = self.root_dir / "failure.png"
        shutil.copyfile(image_path, target_path)
        return str(target_path)

    def record_retry(self, adapter_name, attempt_number, reason):
        self.retry_events.append({
            "adapter_name": adapter_name,
            "attempt_number": int(attempt_number),
            "reason": str(reason or ""),
            "at_utc": _utc_now(),
        })
        self._write_manifest("retrying")

    def record_error(self, adapter_name, error):
        self.error_events.append({
            "adapter_name": adapter_name,
            "error_type": error.__class__.__name__,
            "message": str(error),
            "at_utc": _utc_now(),
        })
        self._write_manifest("failed")

    def complete(self, status, extra_metadata=None):
        extra_metadata = dict(extra_metadata or {})
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["status"] = status
        manifest["updated_at_utc"] = _utc_now()
        manifest["result_metadata"] = extra_metadata
        self._write_json(self.manifest_path, manifest)


class EvidenceLogger:
    DEFAULT_MASK_PATTERNS = [
        r"\b\d{3}-\d{4}\b",
        r"\b\d{2,4}-\d{2,4}-\d{3,4}\b",
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    ]

    def __init__(self, root_dir="reports/ocr_pipeline", secure_mode=False, mask_patterns=None):
        self.root_dir = Path(root_dir)
        self.secure_mode = bool(secure_mode)
        self.mask_patterns = list(mask_patterns or self.DEFAULT_MASK_PATTERNS)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def start_run(self, capture_request, adapter_name):
        run_key = capture_request.idempotency_key or capture_request.fingerprint()
        return EvidenceRun(
            root_dir=self.root_dir / run_key,
            capture_request=capture_request,
            adapter_name=adapter_name,
            secure_mode=self.secure_mode or capture_request.secure_mode,
            mask_patterns=self.mask_patterns,
        )
