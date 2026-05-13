#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import os
import tomllib
from pathlib import Path


def resolve_codex_home(explicit_home):
    if explicit_home:
        return Path(explicit_home).expanduser().resolve()
    env_home = os.environ.get("CODEX_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def load_automation(automation_path):
    with automation_path.open("rb") as handle:
        return tomllib.load(handle)


def resolve_workspace(data, explicit_workspace):
    if explicit_workspace:
        return Path(explicit_workspace).expanduser().resolve()
    cwds = data.get("cwds") or []
    if cwds:
        return Path(cwds[0]).expanduser().resolve()
    return Path.cwd().resolve()


def build_payload(data, automation_path, workspace):
    return {
        "automation_id": data.get("id"),
        "name": data.get("name"),
        "cwd": str(workspace),
        "prompt": data.get("prompt", "").strip(),
        "rrule": data.get("rrule"),
        "model": data.get("model"),
        "reasoning_effort": data.get("reasoning_effort"),
        "execution_environment": data.get("execution_environment"),
        "source": str(automation_path),
        "scheduler_role": "ClaudeCowork",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Emit a ClaudeCowork scheduler payload from the CIDLS Codex automation."
    )
    parser.add_argument("--codex-home", help="Override CODEX_HOME.")
    parser.add_argument("--automation-id", default="agents-sw-cycle")
    parser.add_argument("--automation-path", help="Direct path to automation.toml.")
    parser.add_argument("--workspace", help="Override the workspace cwd.")
    parser.add_argument("--output", help="Optional path to write the JSON payload.")
    args = parser.parse_args()

    codex_home = resolve_codex_home(args.codex_home)
    if args.automation_path:
        automation_path = Path(args.automation_path).expanduser().resolve()
    else:
        automation_path = codex_home / "automations" / args.automation_id / "automation.toml"

    data = load_automation(automation_path)
    workspace = resolve_workspace(data, args.workspace)
    payload = build_payload(data, automation_path, workspace)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
