#!/usr/bin/env python3
"""生信代码合同工具的统一命令行入口。"""
from __future__ import annotations

import argparse
import sys

import init_code_contract
import validate_evidence_pack
import validate_code_contract
import validate_figure_manifest
import source_review
import validate_stage_contract


def main(argv: list[str] | None = None) -> int:
    description = "校验生信代码合同、INI 阶段边界、证据包、源码审查或图件声明（v2.2）。"
    if argv is None:
        argv = sys.argv[1:]
    if not argv or argv[0] in {"-h", "--help"}:
        parser = argparse.ArgumentParser(description=description)
        parser.add_argument("command", choices=("init", "validate", "evidence", "figure", "stage", "source-review", "source_review"), help="选择一个确定性操作")
        parser.print_help()
        return 0
    parser = argparse.ArgumentParser(description=description, add_help=False)
    parser.add_argument(
        "command",
        choices=("init", "validate", "evidence", "figure", "stage", "source-review", "source_review"),
        help="选择一个确定性操作",
    )
    args, rest = parser.parse_known_args(argv)
    if args.command == "init":
        return init_code_contract.main(rest)
    if args.command == "validate":
        return validate_code_contract.main(rest)
    if args.command == "evidence":
        return validate_evidence_pack.main(rest)
    if args.command == "stage":
        return validate_stage_contract.main(rest)
    if args.command in {"source-review", "source_review"}:
        return source_review.main(rest)
    return validate_figure_manifest.main(rest)


if __name__ == "__main__":
    raise SystemExit(main())
