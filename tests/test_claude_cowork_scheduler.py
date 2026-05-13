from pathlib import Path


def test_claude_cowork_scheduler_uses_generic_paths_and_current_cidls_hook():
    repo = Path(__file__).resolve().parents[1]
    scheduler = (repo / "scripts" / "claude_cowork_scheduler.ps1").read_text(
        encoding="utf-8"
    )
    runner = (repo / "scripts" / "run_claude_cowork_cycle.cmd").read_text(
        encoding="utf-8"
    )
    automation = (
        Path.home()
        / ".codex"
        / "automations"
        / "agents-sw-cycle"
        / "automation.toml"
    ).read_text(encoding="utf-8")

    combined = "\n".join([scheduler, runner, automation])
    assert "ICDD" not in combined
    assert "%USERPROFILE%" in combined
    assert "CODEX_HOME" in combined
    assert "pre_prompt_cycle.bat" in combined
    assert "installer.bat" in combined
    assert "project_kanban.html" in combined
    assert "商用請負" in combined
    assert "A5:SQL Mk-2" in combined
    for marker in ("郢", "繝", "邵"):
        assert marker not in combined
