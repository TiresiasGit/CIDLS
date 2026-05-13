import json

from cidls.ocr_pipeline.evidence_logger import EvidenceLogger
from cidls.ocr_pipeline.models import CaptureRequest, ConversionReport, StructuredInput


def test_evidence_logger_writes_masked_outputs(tmp_path):
    request = CaptureRequest(
        source_mode="screen_region",
        region={"left": 1, "top": 2, "width": 300, "height": 200},
        idempotency_key="masked-case",
        secure_mode=True,
    )
    logger = EvidenceLogger(root_dir=tmp_path, secure_mode=True)
    run = logger.start_run(request, "snipping_tool")

    run.save_raw_text("mail: cidls.user@example.com\nphone: 03-1234-5678")
    report = ConversionReport(
        structured_input=StructuredInput({"sample": True}),
        normalized_text="masked",
        key_values=[{"key": "mail", "value": "cidls.user@example.com", "line_index": 0, "raw": "mail: cidls.user@example.com"}],
        rows=[],
    )
    run.save_structured(report)
    run.complete("success", {"final_adapter": "snipping_tool"})

    raw_text = (tmp_path / "masked-case" / "ocr_raw.txt").read_text(encoding="utf-8")
    manifest = json.loads((tmp_path / "masked-case" / "manifest.json").read_text(encoding="utf-8"))

    assert "[MASKED]" in raw_text
    assert manifest["status"] == "success"
