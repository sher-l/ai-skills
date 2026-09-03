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


def main(argv: list[str] | None = None) -> int:
    description = "Validate an evidence pack, source review, code contract or figure manifest (v2.2)."
    if argv is None:
        argv = sys.argv[1:]
    if not argv or argv[0] in {"-h", "--help"}:
        parser = argparse.ArgumentParser(description=description)
        parser.add_argument("command", choices=("init", "validate", "evidence", "figure", "source-review", "source_review"), help="one deterministic operation")
        parser.print_help()
        return 0
    parser = argparse.ArgumentParser(description=description, add_help=False)
    parser.add_argument(
        "command",
        choices=("init", "validate", "evidence", "figure", "source-review", "source_review"),
        help="one deterministic operation",
    )
    args, rest = parser.parse_known_args(argv)
    if args.command == "init":
        return init_code_contract.main(rest)
    if args.command == "validate":
        return validate_code_contract.main(rest)
    if args.command == "evidence":
        return validate_evidence_pack.main(rest)
    if args.command in {"source-review", "source_review"}:
        return source_review.main(rest)
    return validate_figure_manifest.main(rest)


if __name__ == "__main__":
    raise SystemExit(main())
