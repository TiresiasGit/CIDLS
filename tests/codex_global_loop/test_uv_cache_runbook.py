from pathlib import Path


def test_automation_runbook_routes_uv_cache_to_workspace():
    repo = Path(__file__).resolve().parents[2]
    runbook = (repo / "docs" / "ocr_pipeline_runbook.md").read_text(
        encoding="utf-8"
    )

    assert "set UV_CACHE_DIR=%CD%\\.uv-cache" in runbook
    assert "uv run python -m pytest" in runbook
