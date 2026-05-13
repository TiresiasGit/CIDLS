import argparse
import json
import sys

from .adapters import (
    PowerToysTextExtractorAdapter,
    SnippingToolOCRAdapter,
    WinOCRAdapter,
    build_default_pipeline,
    list_available_adapters,
)
from .capture_orchestrator import CaptureOrchestrator
from .dpi_utils import set_dpi_aware
from .evidence_logger import EvidenceLogger
from .models import CaptureRequest
from .ocr_result_parser import OCRResultParser
from .rpainput_converter import RPAInputConverter

VALID_ADAPTERS = ["winocr", "snipping_tool", "powertoys_text_extractor"]


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "CIDLS OCR pipeline: Windows 11 screen capture -> OCR -> RPAInput conversion.\n"
            "Adapters: snipping_tool (GUI primary) | powertoys_text_extractor (GUI fallback) | winocr (native fallback)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    run_cmd = sub.add_parser("run", help="Run OCR pipeline on a region or image file")
    run_cmd.add_argument("--source-mode", choices=["screen_region", "image_file"], required=True)
    run_cmd.add_argument("--left", type=int, default=0)
    run_cmd.add_argument("--top", type=int, default=0)
    run_cmd.add_argument("--width", type=int, default=0)
    run_cmd.add_argument("--height", type=int, default=0)
    run_cmd.add_argument("--image-path", default="")
    run_cmd.add_argument("--output-format", choices=["json", "csv", "dto"], default="json")
    run_cmd.add_argument("--language-hint", default="ja-JP")
    run_cmd.add_argument("--idempotency-key", default="")
    run_cmd.add_argument(
        "--preferred-adapter",
        choices=VALID_ADAPTERS,
        default="snipping_tool",
        help="Primary OCR adapter (default: snipping_tool)",
    )
    run_cmd.add_argument(
        "--fallback-adapter",
        choices=VALID_ADAPTERS + [""],
        default="powertoys_text_extractor",
        help="Fallback adapter if primary fails",
    )
    run_cmd.add_argument("--retry-count", type=int, default=2)
    run_cmd.add_argument("--timeout-seconds", type=int, default=20)
    run_cmd.add_argument("--evidence-root", default="reports/ocr_pipeline")
    run_cmd.add_argument("--secure-mode", action="store_true", help="Mask PII in evidence logs")
    run_cmd.add_argument(
        "--template-dir",
        default="fixtures/templates/snipping_tool",
        help="Dir with Snipping Tool button reference images",
    )
    run_cmd.add_argument(
        "--no-dpi-fix",
        action="store_true",
        help="Skip DPI awareness setup (use if already set externally)",
    )

    list_cmd = sub.add_parser("list-adapters", help="List available OCR adapters and their status")

    return parser


def _run_pipeline(args) -> int:
    if not args.no_dpi_fix:
        set_dpi_aware()

    region = {}
    if args.source_mode == "screen_region":
        region = {
            "left": args.left,
            "top": args.top,
            "width": args.width,
            "height": args.height,
        }

    capture_request = CaptureRequest(
        source_mode=args.source_mode,
        region=region,
        image_path=args.image_path,
        output_format=args.output_format,
        language_hint=args.language_hint,
        idempotency_key=args.idempotency_key,
        preferred_adapter=args.preferred_adapter,
        fallback_adapter=args.fallback_adapter,
        secure_mode=args.secure_mode,
        retry_count=args.retry_count,
        timeout_seconds=args.timeout_seconds,
    )

    evidence_logger = EvidenceLogger(root_dir=args.evidence_root, secure_mode=args.secure_mode)
    adapters = build_default_pipeline(
        preferred=args.preferred_adapter,
        fallback=args.fallback_adapter,
        template_dir=args.template_dir,
    )
    orchestrator = CaptureOrchestrator(
        adapters=adapters,
        parser=OCRResultParser(),
        converter=RPAInputConverter(),
        evidence_logger=evidence_logger,
    )
    report = orchestrator.execute(capture_request)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return _run_pipeline(args)

    if args.command == "list-adapters":
        results = list_available_adapters()
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
