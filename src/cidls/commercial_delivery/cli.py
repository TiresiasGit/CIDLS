import argparse
import json
from pathlib import Path

from .generator import build_commercial_delivery_package


def build_parser():
    parser = argparse.ArgumentParser(
        description="CIDLS商用請負Excel成果物パックとSTORY.htmlを生成する。"
    )
    parser.add_argument(
        "--output-dir",
        default="reports/commercial_delivery",
        help="出力先ディレクトリ",
    )
    parser.add_argument(
        "--project-name",
        default="CIDLS商用請負納品パッケージ",
        help="成果物に記載するプロジェクト名",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    report = build_commercial_delivery_package(
        output_dir=Path(args.output_dir),
        project_name=args.project_name,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
