from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_agents_records_human_contradiction_premise():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "人は矛盾に満ちた生き物である" in text
    assert "矛盾は非難対象ではなく" in text


def test_gemini_programmer_defaults_to_yolo_without_auto_edit():
    script = (ROOT / "scripts" / "gemini_programmer.ps1").read_text(encoding="utf-8-sig")
    generator = (ROOT / "scripts" / "write_gemini_ps1.py").read_text(encoding="utf-8")
    context = (ROOT / ".gemini" / "GEMINI.md").read_text(encoding="utf-8")

    for text in (script, generator):
        assert '$approvalMode = "yolo"' in text
        assert "auto_edit" not in text

    assert "--approval-mode yolo" in context
    assert "Humans are full of contradictions" in context
