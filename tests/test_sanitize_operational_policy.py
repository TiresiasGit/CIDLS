from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_agents_limits_sanitize_to_release_or_explicit_sensitive_events():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "scripts\\sanitize_sensitive_artifacts.py" in text
    assert "毎入力サイクル・毎応答・通常開発のたびに実行しない" in text
    assert "配布物作成前" in text
    assert "外部共有前" in text
    assert "ユーザーが明示した場合" in text
