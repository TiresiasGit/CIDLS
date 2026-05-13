"""
compute_use.cli - CLI entry point for CIDLS ComputeUse module.

Commands:
  cidls-compute-use run       -- Run a single ComputeUse task (interactive).
  cidls-compute-use evolve    -- Daily self-evolution (concept image driven).
  cidls-compute-use status    -- Show recent evolution log from DuckDB.

Usage examples:
  uv run cidls-compute-use evolve
  uv run cidls-compute-use evolve --dry-run
  uv run cidls-compute-use run --goal "Open kanban_project.html and verify Done tasks"
  uv run cidls-compute-use status
"""

import argparse
import logging
import sys
from pathlib import Path


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=level,
        stream=sys.stderr,
    )


def cmd_evolve(args: argparse.Namespace) -> int:
    from .evolution_runner import run_daily_evolution

    result = run_daily_evolution(
        api_key=args.api_key,
        dry_run=args.dry_run,
        max_iterations=args.max_iterations,
    )
    if result is None:
        print("Evolution skipped (see logs for reason).")
        return 0
    print(f"Evolution completed. success={result.success} iterations={result.iterations}")
    if result.summary:
        print(f"Summary: {result.summary[:300]}")
    if result.error:
        print(f"Error: {result.error}", file=sys.stderr)
        return 1
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from .agent import ComputeUseAgent, ComputeUseUnavailableError, make_evolution_task

    task = make_evolution_task(
        description=args.description or args.goal,
        goal=args.goal,
        max_iterations=args.max_iterations,
        screenshot_dir=Path(args.screenshot_dir),
    )

    try:
        agent = ComputeUseAgent(
            api_key=args.api_key,
            dry_run=args.dry_run,
        )
        result = agent.run(task)
    except ComputeUseUnavailableError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Task completed. success={result.success} iterations={result.iterations}")
    if result.summary:
        print(f"Summary: {result.summary[:500]}")
    if result.evidence_paths:
        print(f"Evidence: {result.evidence_paths}")
    return 0 if result.success else 1


def cmd_status(args: argparse.Namespace) -> int:
    import duckdb
    from pathlib import Path

    db_path = Path(args.db_path)
    if not db_path.exists():
        print("No evolution log found. Run 'cidls-compute-use evolve' first.")
        return 0

    con = duckdb.connect(str(db_path))
    try:
        rows = con.execute(
            "SELECT cycle_n, timestamp, hypothesis, delta_desc "
            "FROM evolve_log ORDER BY cycle_n DESC LIMIT ?",
            [args.limit],
        ).fetchall()
    except Exception:
        print("evolve_log table not found.")
        return 0
    finally:
        con.close()

    if not rows:
        print("No entries in evolve_log.")
        return 0

    print(f"{'cycle':>5}  {'timestamp':<20}  {'hypothesis':<60}  delta")
    print("-" * 120)
    for cycle_n, ts, hyp, delta in rows:
        hyp_s = (hyp or "")[:58]
        delta_s = (delta or "")[:40]
        print(f"{cycle_n:>5}  {str(ts):<20}  {hyp_s:<60}  {delta_s}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cidls-compute-use",
        description="CIDLS ComputeUse autonomous evolution CLI",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command")

    # evolve
    p_evolve = sub.add_parser("evolve", help="Run daily self-evolution")
    p_evolve.add_argument("--api-key", dest="api_key", default=None)
    p_evolve.add_argument("--dry-run", dest="dry_run", action="store_true")
    p_evolve.add_argument("--max-iterations", dest="max_iterations", type=int, default=30)

    # run
    p_run = sub.add_parser("run", help="Run single ComputeUse task")
    p_run.add_argument("--goal", required=True, help="Task goal (one sentence)")
    p_run.add_argument("--description", default=None, help="Detailed description")
    p_run.add_argument("--api-key", dest="api_key", default=None)
    p_run.add_argument("--dry-run", dest="dry_run", action="store_true")
    p_run.add_argument("--max-iterations", dest="max_iterations", type=int, default=20)
    p_run.add_argument(
        "--screenshot-dir",
        dest="screenshot_dir",
        default="reports/compute_use",
    )

    # status
    p_status = sub.add_parser("status", help="Show recent evolution log")
    p_status.add_argument(
        "--db-path",
        dest="db_path",
        default="data/cidls.duckdb",
    )
    p_status.add_argument("--limit", type=int, default=20)

    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    dispatch = {
        "evolve": cmd_evolve,
        "run": cmd_run,
        "status": cmd_status,
    }

    if args.command not in dispatch:
        parser.print_help()
        return 0

    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
