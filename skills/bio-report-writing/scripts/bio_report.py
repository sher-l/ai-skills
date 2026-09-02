#!/usr/bin/env python3
"""CLI for report slot scaffolds and contract checks; formal output uses a module renderer."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

import build_docx
import build_report_skeleton
import create_style_reference
import init_report_plan
import validate_docx_structure
import validate_report_contract


COMMANDS = {
    "init": init_report_plan.main,
    "skeleton": build_report_skeleton.main,
    "validate": validate_report_contract.main,
    "build": build_docx.main,
    "docx": validate_docx_structure.main,
    "style": create_style_reference.main,
}


def run_pipeline(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run the generic report draft scaffold (not a formal renderer).")
    parser.add_argument("--evidence-pack", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--mode", choices=("module", "one_off"), default="module")
    parser.add_argument("--final", action="store_true", help="reserved; generic scaffold cannot produce a final report")
    args = parser.parse_args(argv)
    output_dir = args.output_dir.resolve()
    root = (args.root or args.evidence_pack.parent).resolve()
    if not root.is_dir():
        print(f"REPORT_PIPELINE_BLOCKED: root does not exist: {root}", file=sys.stderr)
        return 2
    if args.final:
        print(
            "REPORT_PIPELINE_BLOCKED: generic scaffold has no final mode; "
            "invoke the module R/Python renderer, then run validators with --final",
            file=sys.stderr,
        )
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)
    plan = output_dir / "report_plan.json"
    markdown = output_dir / "report_draft.md"
    docx = output_dir / "report.docx"
    script_dir = Path(__file__).resolve().parent
    steps = [
        [sys.executable, str(script_dir / "init_report_plan.py"), "--evidence-pack", str(args.evidence_pack), "--output", str(plan), "--mode", args.mode],
        [sys.executable, str(script_dir / "build_report_skeleton.py"), "--plan", str(plan), "--evidence-pack", str(args.evidence_pack), "--output", str(markdown), "--root", str(root)],
        [sys.executable, str(script_dir / "validate_report_contract.py"), "--plan", str(plan), "--evidence-pack", str(args.evidence_pack), "--root", str(root)],
        [sys.executable, str(script_dir / "build_docx.py"), "--plan", str(plan), "--evidence-pack", str(args.evidence_pack), "--output", str(docx), "--root", str(root)],
        [sys.executable, str(script_dir / "validate_docx_structure.py"), str(docx)],
    ]
    if args.final:
        steps[2].extend(["--markdown", str(markdown), "--final", "--root", str(root)])
        steps[3].append("--final")
        steps[4].append("--final")
    for command in steps:
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        if result.stdout:
            print(result.stdout, end="")
        if result.returncode:
            if result.stderr:
                print(result.stderr, end="", file=sys.stderr)
            combined = f"{result.stdout}\n{result.stderr}"
            if not args.final and ("_DRAFT" in combined or "EVIDENCE_NEEDED" in combined):
                continue
            print(f"REPORT_PIPELINE_BLOCKED: command failed: {' '.join(command)}", file=sys.stderr)
            return result.returncode
    print(f"REPORT_PIPELINE_EVIDENCE_NEEDED output={docx}")
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare report slots and checks; invoke the module R/Python renderer for delivery."
    )
    parser.add_argument("command", choices=tuple(COMMANDS) + ("run",), help="one deterministic operation")
    args, rest = parser.parse_known_args(argv)
    if args.command == "run":
        return run_pipeline(rest)
    return COMMANDS[args.command](rest)


if __name__ == "__main__":
    raise SystemExit(main())
