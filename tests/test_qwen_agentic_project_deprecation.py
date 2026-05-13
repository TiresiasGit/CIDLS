import subprocess
import sys
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODEX_HOME = Path.home() / ".codex"


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_agents_contains_qwen_agentic_commercial_and_project_deprecation():
    text = read("AGENTS.md")
    for term in [
        "[QWEN_THINKING_MAX_PROGRAMMER]",
        "Qwen3.6ThinkingMax",
        "[AGENTIC_CONTROL_STACK]",
        "LangChain",
        "LangGraph",
        "CrewAI",
        "Claude World",
        "[COMMERCIAL_AUTONOMOUS_EVOLUTION]",
        "企画、開発、運用、保守、販売、LP、改善、生成物欠落",
        "[PROJECT_MD_DEPRECATION]",
        "project.mdは廃止する",
    ]:
        assert term in text


def test_project_md_is_removed_and_migrated_to_kanban_html():
    assert not (ROOT / "project.md").exists()

    kanban = read("kanban_project.html")
    mirror = read("project_kanban.html")
    assert kanban == mirror

    for term in [
        "project-md-archive",
        "project.md廃止済みアーカイブ",
        "CIDLS Project Summary",
        "Current Snapshot",
        "CAPDkA Snapshot",
        "Latest Run",
    ]:
        assert term in kanban


def test_agentic_terms_are_in_html_outputs():
    completed = subprocess.run(
        [sys.executable, "scripts/generate_cidls_platform_overview.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    completed = subprocess.run(
        [sys.executable, "scripts/generate_graph_project_mindmap.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    texts = [
        read("cidls_platform_overview.html"),
        read("reports/cidls_pipeline_output/cidls_platform_overview.html"),
        read("graph_project_mindmap.html"),
        read("reports/cidls_pipeline_output/graph_project_mindmap.html"),
    ]
    for text in texts:
        for term in [
            "Qwen3.6ThinkingMax",
            "LangChain",
            "LangGraph",
            "CrewAI",
            "Claude World",
            "商用自律進化",
        ]:
            assert term in text


def test_orthogonal_compression_contains_agentic_deprecation_terms():
    completed = subprocess.run(
        [sys.executable, "scripts/generate_agents_orthogonal_compression.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    text = read("AGENTS直交圧縮.md")
    for term in [
        "QWEN_THINKING_MAX_PROGRAMMER",
        "AGENTIC_CONTROL_STACK",
        "COMMERCIAL_AUTONOMOUS_EVOLUTION",
        "PROJECT_MD_DEPRECATION",
        "project.md廃止",
    ]:
        assert term in text


def test_daily_automation_contains_agentic_control_rules():
    text = (
        CODEX_HOME / "automations" / "agents-sw-cycle" / "automation.toml"
    ).read_text(encoding="utf-8")

    for term in [
        "Qwen3.6ThinkingMax",
        "LangChain / LangGraph / CrewAI / Claude World",
        "project.mdは廃止済み",
        "kanban_project.html",
    ]:
        assert term in text
