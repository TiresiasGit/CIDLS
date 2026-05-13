# CIDLS Test Scenarios

## 1. Summary

- TS-FUNC-001: board selection and focus flow
- TS-OPS-002: root hook execution
- TS-AUTO-003: recurring automation observation
- TS-LOG-004: log intake report generation
- TS-DOC-005: docs pack navigation
- TS-NFR-009: global devrag generator scope guard
- TS-OCR-010: web OCR conversion path
- TS-OPS-011: maintenance loop installer retry

## 2. Functional

| Item | Given | When | Then | Result |
|---|---|---|---|---|
| TS-FUNC-001 | `project_kanban.html` is open | A stage is selected | Detail and kanban focus stay linked | Pending |
| TS-OPS-002 | `pre_prompt_cycle.bat` exists | The command is executed | `state/autonomy_state.json` and `kanban_project.html` refresh | Pass |
| TS-LOG-004 | Log intake script exists | The script is executed | `logs/alaya_intake_report.json` is produced | Pass |
| TS-OCR-010 | OCR web fixture is available | A scene screenshot is passed through OCR conversion | Structured key-values or rows are returned | Pass |
| TS-OCR-012 | Parser receives representative OCR text | Single label, multiline form, Japanese, symbols, table, linebreak, and typo cases are parsed | Key-values, rows, warnings, and normalized text match expected payloads | Pass |
| TS-OCR-013 | Snipping Tool primary path is unavailable or delayed | Adapter returns empty text, misses clipboard update, or exhausts template detection | Retry history and typed failure evidence are recorded before PowerToys path is attempted | Pass |
| TS-OPS-014 | Global devrag refresh wrapper imports audit wiring | `python scripts\refresh_global_cidls_devrag.py` is executed | The wrapper returns `already_current`, `refreshed`, or typed blocked status without import failure | Pass |

## 3. Non-Functional

| Item | Given | When | Then | Result |
|---|---|---|---|---|
| TS-NFR-006 | devrag is available | Markdown indexing is rebuilt | `%CODEX_HOME%\AGENTS.md` can be indexed when `%CODEX_HOME%` is configured | Pass |
| TS-AUTO-003 | automation is active | A recurring run completes | Board and mirrors remain stable and sync report is `unchanged` | Pass |
| TS-NFR-009 | global devrag generator can be inspected | `python scripts\audit_global_cidls_wiring.py` is executed | The report shows both bare-root flags as false and rebuilds do not spill outside CIDLS | Pass |
| TS-OPS-011 | `pre_prompt_cycle.bat` initially reports missing runtime | `installer.bat` is run once and `pre_prompt_cycle.bat` is retried | The second hook attempt succeeds or produces a typed failure record | Pass |

## 4. UI / UX

| Item | Given | When | Then | Result |
|---|---|---|---|---|
| TS-UI-007 | desktop browser | The board is opened | Main information remains readable in three panels | Pending |
| TS-UI-008 | mobile viewport | The board is opened | One-column reading stays usable | Pending |

## 5. Data / Docs

| Item | Given | When | Then | Result |
|---|---|---|---|---|
| TS-DOC-005 | docs pack exists | The docs section is opened | Requirements, QA, scenarios, and runbook are reachable | Pass |
