import argparse
import json

from .generator import DEFAULT_CONCEPT_TITLE, build_default_spec, materialize_pipeline


def build_parser():
    parser = argparse.ArgumentParser(
        description="CIDLS concept-image pipeline: idea -> AGENTS deliverables -> Codex local package"
    )
    sub = parser.add_subparsers(dest="command")

    describe_cmd = sub.add_parser("describe", help="Print the canonical CIDLS pipeline spec")
    describe_cmd.add_argument("--concept-title", default=DEFAULT_CONCEPT_TITLE)

    materialize_cmd = sub.add_parser("materialize", help="Generate local CIDLS pipeline deliverables")
    materialize_cmd.add_argument("--concept-title", default=DEFAULT_CONCEPT_TITLE)
    materialize_cmd.add_argument("--output-dir", default="reports/cidls_pipeline_output")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "describe":
        spec = build_default_spec(concept_title=args.concept_title)
        print(json.dumps(spec.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "materialize":
        report = materialize_pipeline(
            output_dir=args.output_dir,
            concept_title=args.concept_title,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
