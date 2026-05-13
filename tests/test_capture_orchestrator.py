import contextlib

import pytest

from cidls.ocr_pipeline.capture_orchestrator import CaptureOrchestrator
from cidls.ocr_pipeline.evidence_logger import EvidenceLogger
from cidls.ocr_pipeline.models import CaptureRequest, OCRRawResult
from cidls.ocr_pipeline.ocr_result_parser import OCRResultParser
from cidls.ocr_pipeline.rpainput_converter import RPAInputConverter


class FakeAdapter:
    def __init__(self, name, responses):
        self.name = name
        self.responses = list(responses)
        self.calls = 0

    def supports(self, capture_request):
        return True

    def extract(self, capture_request, evidence_run):
        response = self.responses[self.calls]
        self.calls += 1
        if isinstance(response, Exception):
            raise response
        return response


def test_orchestrator_uses_fallback_after_primary_failure(tmp_path):
    primary = FakeAdapter("snipping_tool", [RuntimeError("template not found")])
    fallback = FakeAdapter("powertoys_text_extractor", [
        OCRRawResult(adapter_name="powertoys_text_extractor", raw_text="氏名: 山田 花子\n部署: 営業企画")
    ])

    orchestrator = CaptureOrchestrator(
        adapters=[primary, fallback],
        parser=OCRResultParser(),
        converter=RPAInputConverter(),
        evidence_logger=EvidenceLogger(root_dir=tmp_path),
    )
    request = CaptureRequest(
        source_mode="screen_region",
        region={"left": 10, "top": 20, "width": 240, "height": 180},
        preferred_adapter="snipping_tool",
        fallback_adapter="powertoys_text_extractor",
        idempotency_key="fallback-case",
        retry_count=0,
    )

    report = orchestrator.execute(request)

    assert report.to_dict()["structured_input"]["source"]["adapter"] == "powertoys_text_extractor"
    assert primary.calls == 1
    assert fallback.calls == 1


def test_orchestrator_retries_primary_then_succeeds(tmp_path):
    primary = FakeAdapter("snipping_tool", [
        RuntimeError("launch delay"),
        OCRRawResult(adapter_name="snipping_tool", raw_text="氏名: 山田 花子"),
    ])

    orchestrator = CaptureOrchestrator(
        adapters=[primary],
        parser=OCRResultParser(),
        converter=RPAInputConverter(),
        evidence_logger=EvidenceLogger(root_dir=tmp_path),
    )
    request = CaptureRequest(
        source_mode="screen_region",
        region={"left": 10, "top": 20, "width": 240, "height": 180},
        preferred_adapter="snipping_tool",
        fallback_adapter="",
        idempotency_key="retry-success",
        retry_count=1,
    )

    report = orchestrator.execute(request)

    assert report.to_dict()["structured_input"]["source"]["adapter"] == "snipping_tool"
    assert primary.calls == 2


def test_orchestrator_wraps_image_mode_with_preview(sample_png, tmp_path):
    adapter = FakeAdapter("snipping_tool", [
        OCRRawResult(adapter_name="snipping_tool", raw_text="項目: 画像入力")
    ])

    class FakePreviewSession:
        def __init__(self, capture_request):
            self.capture_request = capture_request

        def __enter__(self):
            self.capture_request.preview_region = {"left": 100, "top": 110, "width": 400, "height": 300}
            return self.capture_request

        def __exit__(self, exc_type, exc, tb):
            return False

    orchestrator = CaptureOrchestrator(
        adapters=[adapter],
        parser=OCRResultParser(),
        converter=RPAInputConverter(),
        evidence_logger=EvidenceLogger(root_dir=tmp_path),
        image_preview_session_factory=FakePreviewSession,
    )
    request = CaptureRequest(
        source_mode="image_file",
        image_path=str(sample_png),
        preferred_adapter="snipping_tool",
        fallback_adapter="",
        idempotency_key="image-preview",
        retry_count=0,
    )

    report = orchestrator.execute(request)

    assert report.to_dict()["structured_input"]["source"]["mode"] == "image_file"
    assert request.effective_region()["width"] == 400


def test_orchestrator_raises_after_retry_exhaustion(tmp_path):
    primary = FakeAdapter("snipping_tool", [RuntimeError("boom"), RuntimeError("boom-again")])
    orchestrator = CaptureOrchestrator(
        adapters=[primary],
        parser=OCRResultParser(),
        converter=RPAInputConverter(),
        evidence_logger=EvidenceLogger(root_dir=tmp_path),
    )
    request = CaptureRequest(
        source_mode="screen_region",
        region={"left": 10, "top": 10, "width": 200, "height": 120},
        preferred_adapter="snipping_tool",
        fallback_adapter="",
        idempotency_key="retry-case",
        retry_count=1,
    )

    with pytest.raises(Exception):
        orchestrator.execute(request)
