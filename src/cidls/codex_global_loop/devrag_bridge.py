import json
import os
import re
import subprocess
from pathlib import Path

from .models import DevragSearchResult


class DevragBridge:
    def __init__(self, codex_home="", config_path="", executable_path=""):
        userprofile = Path(os.environ.get("USERPROFILE", "").strip()) if os.environ.get("USERPROFILE", "").strip() else Path.home()
        self.codex_home = Path(codex_home) if codex_home else userprofile / ".codex"
        self.config_path = Path(config_path) if config_path else self.codex_home / "mcp" / "cidls_global" / "runtime-devrag-config.json"
        self.executable_path = Path(executable_path) if executable_path else Path(self._discover_executable_path())

    def search(self, query, top_k=5, directory="", file_pattern=""):
        command = [
            str(self.executable_path),
            "--config",
            str(self.config_path),
            "search",
            "--top-k",
            str(int(top_k)),
            "--output",
            "json",
        ]
        if directory:
            command.extend(["--directory", str(directory)])
        if file_pattern:
            command.extend(["--file-pattern", str(file_pattern)])
        command.append(str(query))

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        results = []
        if completed.stdout.strip():
            try:
                payload = json.loads(completed.stdout)
            except json.JSONDecodeError:
                payload = {}
            if isinstance(payload, dict):
                results = list(payload.get("results", []))
            elif isinstance(payload, list):
                results = payload
        return DevragSearchResult(
            query=query,
            command=command,
            returncode=completed.returncode,
            results=results,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def _discover_executable_path(self):
        launcher_path = self.codex_home / "mcp" / "cidls_global" / "launch-devrag.cmd"
        launcher_text = launcher_path.read_text(encoding="utf-8")
        match = re.search(r'"([^"]*devrag[^"]*\.exe)"', launcher_text, flags=re.I)
        if not match:
            raise ValueError("devrag executable path not found in launch-devrag.cmd")
        return match.group(1)
