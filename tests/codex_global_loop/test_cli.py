import os
import subprocess
import sys
from pathlib import Path


def test_codex_global_loop_cli_module_help_is_executable():
    env = dict(os.environ)
    src_path = str(Path(__file__).resolve().parents[2] / "src")
    env["PYTHONPATH"] = src_path

    completed = subprocess.run(
        [sys.executable, "-m", "cidls.codex_global_loop.cli", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )

    assert completed.returncode == 0
    assert "CIDLS global Codex maintenance helpers" in completed.stdout
    assert "run-loop" in completed.stdout
    assert "audit" in completed.stdout
