# CIDLS Requirements Definition

## Phase1

```yaml
target: CIDLS global Codex maintenance loop with Windows 11 OCR/RPA pipeline
pain:
  as_is:
    - Source of truth, mirrors, docs, and runtime wiring can drift across runs.
    - The OCR path needs Windows GUI automation because Snipping Tool does not expose a stable Python API.
  root_cause:
    - Global wiring spans repo-local and `%CODEX_HOME%` assets, while the automation shell may leave `%CODEX_HOME%` empty.
    - GUI OCR is sensitive to focus, locale, scaling, and toolbar detection drift.
  data:
    - AGENTS.md
    - project_kanban.html
    - project.md
    - TODO.md
    - docs/*.md
    - state/autonomy_state.json
    - fixtures/web/ocr_test_target.html
    - src/cidls/ocr_pipeline/*
ideal:
  value:
    - One SoT drives board, mirrors, docs, and runtime checks without drift.
    - Global devrag stays constrained to CIDLS corpus plus explicit CIDLS Codex files.
    - The OCR path extracts text from web scenes or real Windows regions and converts it into structured RPAInput payloads.
  philosophy:
    - CAPDkA first
    - Horizontal sync
    - No silent drift
solution:
  purpose: Keep the CIDLS maintenance loop reproducible and observable.
  scope:
    - project_kanban.html ticketing and blocker tracking
    - mirror synchronization
    - AGENTS policy sync
    - global hook and devrag wiring checks
    - repo-local audit reporting for global Codex wiring
    - Snipping Tool OCR orchestration
    - PowerToys fallback OCR
    - Web OCR TDD fixtures and tests
  done_conditions:
    - pre_prompt_cycle.bat succeeds
    - AGENTS sync stays no-op when tickets are unchanged
    - new blockers become CIDLS-* tickets and flow into mirrors/docs
    - global wiring can be audited by absolute path even when `%CODEX_HOME%` is empty
    - representative OCR scenes convert into structured inputs
technology:
  stack:
    - HTML
    - JavaScript
    - Python
    - Batch
    - Playwright
    - pyautogui
  assets:
    - project_kanban.html
    - scripts/sync_agents_cidls_policy.py
    - scripts/sync_runtime_state.py
    - scripts/audit_global_cidls_wiring.py
    - src/cidls/codex_global_loop/*
    - src/cidls/ocr_pipeline/*
```

## Constraints

- Windows 11 / PowerShell / UTF-8
- `project_kanban.html` is the primary SoT
- `project.md` is the compact mirror
- `TODO.md` is the checklist mirror
- `pre_prompt_cycle.bat` and `installer.bat` are the Start Cycle entrypoints
- `devrag` must be used for CIDLS knowledge exploration
- Global wiring audits must work with explicit `%CODEX_HOME%` paths when the process environment does not populate the variable
- Python runtime scripts must not register schedulers or recurring jobs on their own

## Must

- Execute `cmd /c pre_prompt_cycle.bat`
- Keep review work out of `Done` until verified
- Register new blockers as `CIDLS-*` tickets in the board
- Sync board, mirrors, docs, QA, and scenarios when open work changes
- Use Snipping Tool as the primary GUI OCR adapter and PowerToys as the first fallback path

## Should

- Keep global devrag limited to CIDLS repo docs and explicit CIDLS Codex files
- Do not include bare `%CODEX_HOME%` as a devrag document root
- Record recurring run observations in concise mirrors
- Keep a repo-local audit trail for global hook/devrag drift
- Skip browser E2E with a typed reason when local policy blocks Playwright rather than misclassifying it as an OCR defect

## Traceability

| ID | Requirement | Implementation | Ticket |
|---|---|---|---|
| RQ-001 | Maintain one operating SoT | `project_kanban.html` | `CIDLS-101` |
| RQ-002 | Keep hook/runtime entrypoints healthy | `pre_prompt_cycle.bat`, `installer.bat`, `scripts/sync_runtime_state.py` | `CIDLS-113` |
| RQ-003 | Keep QA and scenarios visible | board QA/Scenario section | `CIDLS-109` |
| RQ-004 | Turn log intake into actionable outputs | `scripts/alaya_log_intake.py`, report | `CIDLS-110` |
| RQ-005 | Maintain the docs pack | `docs/*.md` | `CIDLS-115` |
| RQ-006 | Keep devrag markdown indexing available | devrag config / directory policy | `CIDLS-107`, `CIDLS-114` |
| RQ-007 | Keep global devrag corpus CIDLS-only after rebuilds | `%CODEX_HOME%\mcp\cidls_global\build-runtime-config.py`, `runtime-devrag-config.json`, `scripts/audit_global_cidls_wiring.py` | `CIDLS-119`, `CIDLS-120` |
| RQ-008 | Convert Windows OCR output into RPAInput payloads | `src/cidls/ocr_pipeline/*`, `fixtures/web/ocr_test_target.html` | `CIDLS-126` |
