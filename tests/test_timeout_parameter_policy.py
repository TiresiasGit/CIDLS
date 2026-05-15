from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_agents_requires_timeout_parameter_design():
    text = read("AGENTS.md")

    assert "### T3.2.1 タイムアウト事前設計(必須)" in text
    assert "調整可能パラメータ" in text
    assert "timeout_seconds" in text
    assert "max_retries" in text
    assert "retry_backoff_seconds" in text
    assert "max_concurrency" in text
    assert "batch_size" in text
    assert "heartbeat_interval_seconds" in text
    assert "無期限待機" in text
    assert "タイムアウト例外の握りつぶし" in text


def test_gemini_context_inherits_timeout_parameter_design():
    text = read(".gemini/GEMINI.md")

    assert "## Timeout And Parameter Design" in text
    assert "timeout-prone work" in text
    assert "`timeout_seconds`" in text
    assert "`max_retries`" in text
    assert "`retry_backoff_seconds`" in text
    assert "`max_concurrency`" in text
    assert "`cancellation_deadline_seconds`" in text
    assert "Never use infinite waits" in text


def test_orthogonal_summary_records_timeout_parameter_design():
    text = read("AGENTS要点まとめ.md")
    generator = read("scripts/generate_agents_orthogonal_compression.py")

    assert "TIMEOUT:事前設計" in text
    assert "TIMEOUT_PARAMETER_DESIGN" in generator
    assert "timeout/retry/backoff/concurrency/batch/chunk/progress/heartbeat/cancel=調整可能" in generator
