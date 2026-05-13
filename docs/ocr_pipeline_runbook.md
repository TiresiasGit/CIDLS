# CIDLS OCR Pipeline Runbook

## Setup
1. `cd <CIDLS_REPO>`
2. `uv venv`
3. `.venv\Scripts\python -m pip --version` is not used. Install through uv only.
4. `uv sync --extra dev --extra e2e`
5. In automation contexts, route uv cache writes into the workspace before any
   `uv run`: `set UV_CACHE_DIR=%CD%\.uv-cache`.

## Core Commands
- Screen region capture:
  - `uv run cidls-ocr-pipeline --source-mode screen_region --left 120 --top 220 --width 780 --height 420 --idempotency-key sample-screen`
- Image-file preview capture:
  - `uv run cidls-ocr-pipeline --source-mode image_file --image-path C:\path\to\sample.png --idempotency-key sample-image`
- Launch the fixed web OCR target and print its capture region:
  - `uv run cidls-ocr-web-target --scene form --dataset ja --hold-seconds 20`
- Run the CIDLS maintenance loop:
  - `uv run cidls-codex-maintenance run-loop`
- Run the CIDLS maintenance loop with devrag evidence and a CIDLS ticket update:
  - `uv run cidls-codex-maintenance run-loop --devrag-query "Snipping Tool OCR" --ticket-title "Track OCR wiring audit" --ticket-copy "Keep the board aligned with the expanded global wiring audit." --ticket-asis "The loop did not persist OCR wiring follow-up in the board." --ticket-tobe "The loop can emit devrag evidence and update a CIDLS ticket in one run." --ticket-evidence "Use the run-loop JSON output as evidence." --ticket-trace "CIDLS,OCR,Global-Wiring"`
- Search the CIDLS devrag corpus before updating docs or wiring:
  - `uv run cidls-codex-maintenance search-devrag "Snipping Tool OCR" --top-k 5`

## Tests
- Pure/unit and browser tests:
  - `set UV_CACHE_DIR=%CD%\.uv-cache`
  - `uv run python -m pytest tests/codex_global_loop tests/ocr_pipeline/unit tests/ocr_pipeline/integration -q`
- Browser fixture and OCR E2E:
  - `uv run python -m pytest tests/ocr_pipeline/e2e -q`
- Interactive GUI smoke:
  - `set CIDLS_GUI_CAPTURE_REGION=120,220,780,420`
  - `set CIDLS_SNIPPING_TEMPLATE_DIR=<CIDLS_REPO>\fixtures\templates\snipping_tool`
  - `uv run python -m pytest --run-gui -m gui`
- Interactive GUI smoke against the fixed web target:
  - `set CIDLS_GUI_WEB_SCENE=form`
  - `set CIDLS_GUI_WEB_DATASET=ja`
  - `set CIDLS_GUI_EXPECT_TEXT=申請番号`
  - `set CIDLS_SNIPPING_TEMPLATE_DIR=<CIDLS_REPO>\fixtures\templates\snipping_tool`
  - `uv run python -m pytest --run-gui -m gui`

## Operational Notes
- Put environment-specific Snipping Tool toolbar templates under `fixtures/templates/snipping_tool/`.
- Use `secure_mode` when OCR output may contain personal data; masked logs are written to `reports/ocr_pipeline/<idempotency_key>/`.
- If Snipping Tool OCR fails because `Text actions` or `Copy all text` cannot be detected, the orchestrator retries and then falls back to PowerToys Text Extractor.
- `image_file` mode and the web GUI smoke both rely on a fixed browser preview window so that the region is deterministic across reruns.
- `pytest.exe` can be blocked by local policy in this workspace; use `python -m pytest`.
- If Playwright is blocked by named-pipe policy, the browser E2E fixture skips with an explicit reason instead of masking the OCR implementation state.
- `python scripts\\audit_global_cidls_wiring.py` now fails the audit when `%CODEX_HOME%\\AGENTS.md`, the CIDLS skill mirrors, or required runtime document patterns drift from the expected SoT wiring.

## Evidence Paths
- `manifest.json`: request, retry history, adapter used, final status
- `ocr_raw.txt`: OCR raw output
- `structured_input.json`: normalized RPAInput payload
- `structured_input.csv`: flattened export for spreadsheet verification
- `failure.png`: last-known screen on failure
