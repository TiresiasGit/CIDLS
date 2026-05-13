import os

import pytest

from cidls.ocr_pipeline.adapters import PowerToysTextExtractorAdapter, SnippingToolOCRAdapter
from cidls.ocr_pipeline.capture_orchestrator import CaptureOrchestrator
from cidls.ocr_pipeline.evidence_logger import EvidenceLogger
from cidls.ocr_pipeline.models import CaptureRequest
from cidls.ocr_pipeline.ocr_result_parser import OCRResultParser
from cidls.ocr_pipeline.rpainput_converter import RPAInputConverter
from cidls.ocr_pipeline.web_test_target import OCRWebTargetSession


@pytest.mark.gui
def test_gui_smoke_screen_region():
    region_env = os.environ.get("CIDLS_GUI_CAPTURE_REGION", "")
    template_dir = os.environ.get("CIDLS_SNIPPING_TEMPLATE_DIR", "fixtures/templates/snipping_tool")
    web_scene = os.environ.get("CIDLS_GUI_WEB_SCENE", "")
    if not region_env and not web_scene:
        pytest.skip("CIDLS_GUI_CAPTURE_REGION or CIDLS_GUI_WEB_SCENE is not set")

    orchestrator = CaptureOrchestrator(
        adapters=[
            SnippingToolOCRAdapter(assets_dir=template_dir),
            PowerToysTextExtractorAdapter(),
        ],
        parser=OCRResultParser(),
        converter=RPAInputConverter(),
        evidence_logger=EvidenceLogger(root_dir="reports/ocr_pipeline_gui"),
    )

    expected_text = os.environ.get("CIDLS_GUI_EXPECT_TEXT", "").strip()
    if web_scene:
        web_dataset = os.environ.get("CIDLS_GUI_WEB_DATASET", "ja")
        with OCRWebTargetSession(scene=web_scene, dataset=web_dataset) as launched:
            region = launched["region"]
            request = CaptureRequest(
                source_mode="screen_region",
                region=region,
                preferred_adapter="snipping_tool",
                fallback_adapter="powertoys_text_extractor",
                timeout_seconds=25,
                retry_count=1,
                idempotency_key=f"gui-web-{web_scene}-{web_dataset}",
                metadata={"web_target_url": launched["url"]},
            )
            report = orchestrator.execute(request)
    else:
        left, top, width, height = [int(part) for part in region_env.split(",")]
        request = CaptureRequest(
            source_mode="screen_region",
            region={"left": left, "top": top, "width": width, "height": height},
            preferred_adapter="snipping_tool",
            fallback_adapter="powertoys_text_extractor",
            timeout_seconds=25,
            retry_count=1,
            idempotency_key="gui-smoke",
        )
        report = orchestrator.execute(request)

    normalized_text = report.to_dict()["normalized_text"]
    assert normalized_text
    if expected_text:
        assert expected_text in normalized_text
