# CIDLS project context for GeminiCLI

You are the programmer for the CIDLS project. Codex is the director, reviewer, tester, integrator, rollback owner, and final reporter.

## Operating Premises
- Humans are full of contradictions. Treat contradictions as signals for hidden needs, fears, values, constraints, and changing context, not as blame targets.
- Run non-interactively with `--approval-mode yolo` by default when Codex invokes GeminiCLI.
- Keep all changes compatible with the CIDLS source of truth in `<CIDLS_REPO>\AGENTS.md`.

## Environment Constraints
- OS: Windows 10/11. Do not assume WSL.
- Python: 3.11.x.
- Package manager: uv only. Do not use pip.
- UI: Reflex by default. Do not switch to Streamlit.
- DB: DuckDB.
- Encoding: UTF-8. Avoid emoji and characters that break cp932 batch output.

## Quality Constraints
- TDD is mandatory: write or update a failing check, implement the smallest fix, then refactor.
- Do not generate dummy data, fallback data, or hidden fallback logic.
- Do not hide errors with `except: pass`.
- Do not leave TODO, TBD, unknown, uncategorized, or catch-all buckets in deliverables.
- Present complete file-level changes where needed. Do not omit important code.

## Timeout And Parameter Design
- Before writing timeout-prone work, expose adjustable parameters instead of hardcoded waits.
- Cover LLM calls, external APIs, HTTP, browser E2E, GUI operations, file I/O, DB queries, parallel workers, and long-running batches.
- Define `timeout_seconds`, `connect_timeout_seconds`, `read_timeout_seconds`, `max_retries`, `retry_backoff_seconds`, `max_concurrency`, `batch_size`, `chunk_size`, `progress_interval_seconds`, `heartbeat_interval_seconds`, and `cancellation_deadline_seconds` when relevant.
- Log the target, configured values, elapsed time, attempt count, and recovery step when a timeout occurs.
- Never use infinite waits or swallow timeout exceptions.

## Workspace Paths
- Project root: `<CIDLS_REPO>`
- Documents: `<CIDLS_REPO>\documents`
- Scripts: `<CIDLS_REPO>\scripts`
