import argparse
import json

from .devrag_bridge import DevragBridge
from .kanban_ticket_store import ProjectKanbanTicketStore
from .maintenance import CIDLSSyncOrchestrator
from .models import KanbanTicketUpdate


def build_parser():
    parser = argparse.ArgumentParser(description="CIDLS global Codex maintenance helpers")
    sub = parser.add_subparsers(dest="command")

    run_cmd = sub.add_parser("run-loop", help="Run pre_prompt_cycle, AGENTS sync, and wiring audit")
    run_cmd.add_argument("--devrag-query", default="")
    run_cmd.add_argument("--devrag-top-k", type=int, default=5)
    run_cmd.add_argument("--devrag-directory", default="")
    run_cmd.add_argument("--devrag-file-pattern", default="")
    run_cmd.add_argument("--ticket-id", default="")
    run_cmd.add_argument("--ticket-status", default="todo")
    run_cmd.add_argument("--ticket-priority", default="medium")
    run_cmd.add_argument("--ticket-title", default="")
    run_cmd.add_argument("--ticket-copy", default="")
    run_cmd.add_argument("--ticket-stage-id", default="fusion")
    run_cmd.add_argument("--ticket-asis", default="")
    run_cmd.add_argument("--ticket-tobe", default="")
    run_cmd.add_argument("--ticket-evidence", default="")
    run_cmd.add_argument("--ticket-trace", default="")
    sub.add_parser("audit", help="Run only the global wiring audit")

    search_cmd = sub.add_parser("search-devrag", help="Search the CIDLS devrag corpus")
    search_cmd.add_argument("query")
    search_cmd.add_argument("--top-k", type=int, default=5)
    search_cmd.add_argument("--directory", default="")
    search_cmd.add_argument("--file-pattern", default="")

    ticket_cmd = sub.add_parser("upsert-ticket", help="Add or update a CIDLS ticket in project_kanban.html")
    ticket_cmd.add_argument("--ticket-id", default="")
    ticket_cmd.add_argument("--status", default="todo")
    ticket_cmd.add_argument("--priority", default="medium")
    ticket_cmd.add_argument("--title", required=True)
    ticket_cmd.add_argument("--copy", required=True)
    ticket_cmd.add_argument("--stage-id", default="fusion")
    ticket_cmd.add_argument("--asis", required=True)
    ticket_cmd.add_argument("--tobe", required=True)
    ticket_cmd.add_argument("--evidence", required=True)
    ticket_cmd.add_argument("--trace", default="")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run-loop":
        ticket_update = None
        if any([
            args.ticket_title,
            args.ticket_copy,
            args.ticket_asis,
            args.ticket_tobe,
            args.ticket_evidence,
        ]):
            missing = []
            if not args.ticket_title:
                missing.append("--ticket-title")
            if not args.ticket_copy:
                missing.append("--ticket-copy")
            if not args.ticket_asis:
                missing.append("--ticket-asis")
            if not args.ticket_tobe:
                missing.append("--ticket-tobe")
            if not args.ticket_evidence:
                missing.append("--ticket-evidence")
            if missing:
                parser.error("ticket update requires: " + ", ".join(missing))
            ticket_update = KanbanTicketUpdate(
                ticket_id=args.ticket_id,
                status=args.ticket_status,
                priority=args.ticket_priority,
                title=args.ticket_title,
                copy=args.ticket_copy,
                stage_id=args.ticket_stage_id,
                asis=args.ticket_asis,
                tobe=args.ticket_tobe,
                evidence=args.ticket_evidence,
                trace=[item.strip() for item in args.ticket_trace.split(",") if item.strip()],
            )
        result = CIDLSSyncOrchestrator().run_full_loop(
            devrag_query=args.devrag_query,
            devrag_top_k=args.devrag_top_k,
            devrag_directory=args.devrag_directory,
            devrag_file_pattern=args.devrag_file_pattern,
            ticket_update=ticket_update,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "audit":
        result = CIDLSSyncOrchestrator().audit_global_wiring().to_dict()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "search-devrag":
        result = DevragBridge().search(
            query=args.query,
            top_k=args.top_k,
            directory=args.directory,
            file_pattern=args.file_pattern,
        )
        print(result.to_json())
        return 0

    if args.command == "upsert-ticket":
        trace = [item.strip() for item in args.trace.split(",") if item.strip()]
        update = KanbanTicketUpdate(
            ticket_id=args.ticket_id,
            status=args.status,
            priority=args.priority,
            title=args.title,
            copy=args.copy,
            stage_id=args.stage_id,
            asis=args.asis,
            tobe=args.tobe,
            evidence=args.evidence,
            trace=trace,
        )
        ticket_id, action = ProjectKanbanTicketStore().upsert(update)
        print(json.dumps({"ticket_id": ticket_id, "action": action}, ensure_ascii=False, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
