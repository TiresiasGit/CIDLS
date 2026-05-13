"""CLI for CIDLS agentic-control helpers."""

import argparse
import sys

from .qwen_control import (
    build_qwen_programmer_brief,
    detect_qwen_environment,
)


def _print_plain_status(status) -> None:
    ready = "ready" if status.invocation_ready else "blocked"
    print(f"Qwen status: {ready}")
    print(f"CLI available: {status.cli_available}")
    if status.cli_version:
        print(f"CLI version: {status.cli_version}")
    print(f"Credential available: {status.credential_available}")
    if status.credential_sources:
        print(f"Credential sources: {', '.join(status.credential_sources)}")
    if status.blockers:
        print(f"Blockers: {', '.join(status.blockers)}")
    if status.next_actions:
        print("Next actions:")
        for action in status.next_actions:
            print(f"- {action}")


def main(
    argv: list[str] | None = None,
    env: dict | None = None,
    command_runner=None,
    path_lookup=None,
) -> int:
    parser = argparse.ArgumentParser(prog="cidls-qwen-control")
    sub = parser.add_subparsers(dest="command")

    status_parser = sub.add_parser("status", help="Show Qwen readiness")
    status_parser.add_argument("--json", action="store_true")
    status_parser.add_argument("--strict", action="store_true")
    status_parser.add_argument("--no-powershell-probe", action="store_true")

    brief_parser = sub.add_parser("brief", help="Build a Qwen Programmer brief")
    brief_parser.add_argument("--title", required=True)
    brief_parser.add_argument("--goal", required=True)
    brief_parser.add_argument("--file", action="append", default=[])
    brief_parser.add_argument("--constraint", action="append", default=[])
    brief_parser.add_argument("--test-command", default=None)

    args = parser.parse_args(argv)
    if args.command == "status":
        status = detect_qwen_environment(
            env=env,
            command_runner=command_runner,
            path_lookup=path_lookup,
            probe_powershell=not args.no_powershell_probe,
        )
        if args.json:
            print(status.to_json())
        else:
            _print_plain_status(status)
        return 0 if status.invocation_ready or not args.strict else 2

    if args.command == "brief":
        print(
            build_qwen_programmer_brief(
                title=args.title,
                goal=args.goal,
                files=args.file,
                constraints=args.constraint,
                test_command=args.test_command,
            )
        )
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
