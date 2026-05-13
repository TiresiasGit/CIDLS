from unittest.mock import patch

from cidls.codex_global_loop.devrag_bridge import DevragBridge


def test_search_builds_cli_command():
    completed = type(
        "Completed",
        (),
        {
            "returncode": 0,
            "stdout": '{"results":[{"document":"docs/ocr.md","chunk":"OCR"}]}',
            "stderr": "",
        },
    )()

    with patch("subprocess.run", return_value=completed) as mock_run:
        bridge = DevragBridge(
            config_path="C:\\cidls\\runtime-devrag-config.json",
            executable_path="C:\\tools\\devrag.exe",
        )
        result = bridge.search("OCR", top_k=3, directory="docs", file_pattern="*.md")

    command = mock_run.call_args.args[0]
    assert command[0] == "C:\\tools\\devrag.exe"
    assert "--config" in command
    assert "search" in command
    assert result.ok() is True
    assert result.results[0]["document"] == "docs/ocr.md"
