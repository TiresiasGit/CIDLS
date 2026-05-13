# CIDLS OCR Pipeline Requirements

## Purpose
- Integrate `pyautogui -> Snipping Tool -> OCR -> RPAInput converter` into CIDLS as a reusable Windows 11 feature.
- Support both live screen capture and image-file driven verification through a single orchestrator.
- Preserve evidence for cause tracing, retry history, and secure-mode masking.

## Known Technical Constraints
- Windows 11 Snipping Tool exposes OCR via GUI `Text actions`, not a stable Python API.
- GUI automation is sensitive to OS language, display scaling, focus stealing, and toolbar layout changes.
- OCR quality varies by language pack, font weight, capture resolution, and background contrast.

## Stable Architecture
- `src/cidls/ocr_pipeline/capture_orchestrator.py`
- `src/cidls/ocr_pipeline/adapters/snipping_tool_adapter.py`
- `src/cidls/ocr_pipeline/adapters/fallback_ocr_adapter.py`
- `src/cidls/ocr_pipeline/web_test_target.py`
- `src/cidls/ocr_pipeline/ocr_result_parser.py`
- `src/cidls/ocr_pipeline/rpainput_converter.py`
- `src/cidls/ocr_pipeline/evidence_logger.py`
- `src/cidls/codex_global_loop/maintenance.py`
- `src/cidls/codex_global_loop/devrag_bridge.py`
- `src/cidls/codex_global_loop/kanban_ticket_store.py`
- `fixtures/web/ocr_test_target.html`

## Runtime Decisions
- `screen_region` and `image_file` both converge on an effective screen region so the same GUI-driven OCR adapters can be reused.
- `image_file` mode launches a fixed browser preview and then captures the preview stage through the same Snipping Tool or PowerToys path.
- Web-screen TDD is executed against `fixtures/web/ocr_test_target.html`, optionally launched through `cidls-ocr-web-target`.
- The default adapter chain is `snipping_tool -> powertoys_text_extractor`; `winocr` remains an explicit native fallback.
- The global maintenance path is callable through `cidls-codex-maintenance` so hook execution, AGENTS sync, wiring audit, devrag search, and ticket updates stay idempotent.
- The wiring audit now validates `%CODEX_HOME%\\AGENTS.md`, the global hook, the devrag launcher/config, and both CIDLS skill mirrors so SoT drift is detected before runtime usage.

## Completion Criteria
- Representative web scenes pass OCR parsing and RPAInput conversion in tests.
- At least one interactive Windows GUI smoke case can be executed via `pytest --run-gui`.
- Fallback adapter is exercised when primary OCR fails.
- Evidence directory contains manifest, raw OCR text, structured output, and failure screenshot on error.
- `python scripts\audit_global_cidls_wiring.py` reports zero wiring issues before operational rollout.
