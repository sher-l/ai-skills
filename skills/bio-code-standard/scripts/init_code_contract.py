#!/usr/bin/env python3
"""Create a small, self-contained R/Python code contract workspace."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

import source_review

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def starter(
    module: str,
    quality_profile: str,
    effort_profile: str,
    languages: set[str],
    with_plot: bool = False,
) -> tuple[dict, dict]:
    canonical_source = "r_stage.R" if "r" in languages else "python_stage.py"
    contract = {
        "schema_version": "0.1.0",
        "module": module,
        "quality_profile": quality_profile,
        "effort_profile": effort_profile,
        "max_repair_rounds": 2,
        "result_layout": "flat",
        "description": "replace with the module purpose, object and public outputs",
        "help": {
            "summary": f"{module}: replace with a human/AI-readable module summary",
            "commands": {
                "help": "show module purpose, inputs and outputs",
                "init": "create or validate configuration without analysis",
                "calculate": "run the declared scientific calculation",
            },
        },
        "canonical_source": canonical_source,
        "source_review": "doc/source-review.md",
        "stages": [
            {
                "id": "calculate",
                "purpose": "replace with one approved analysis goal",
                "inputs": [],
                "outputs": [],
                "method": {"name": "replace", "version": "replace"},
                "parameters": {},
                "seed": None,
                "non_degenerate": "replace with the minimum valid input",
            }
        ],
        "inputs": [],
        "outputs": [],
        "evidence_pack": ".code-contract/analysis_evidence_pack.json",
    }
    if with_plot:
        contract["help"]["commands"]["plot"] = "render figures from published calculation results"
        contract["plot"] = {"figure_manifest": ".code-contract/figure_manifest.json"}
    pack = {
        "schema_version": "0.1.0",
        "module": module,
        "quality_profile": quality_profile,
        "result_layout": "flat",
        "evidence_targets": [],
        "analysis_points": [],
    }
    return contract, pack


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", required=True, help="module name")
    parser.add_argument("--output", required=True, type=Path, help="new workspace directory")
    parser.add_argument("--languages", default="r,python", help="comma-separated: r,python")
    parser.add_argument("--quality-profile", choices=("draft", "release"), default="draft")
    parser.add_argument("--effort-profile", choices=("mechanical", "scientific_review"), default="mechanical")
    parser.add_argument("--with-plot", action="store_true", help="declare and scaffold the optional plot stage")
    args = parser.parse_args(argv)

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        print(f"INIT_CODE_BLOCKED: output is not empty: {output}", file=sys.stderr)
        return 2
    languages = {item.strip().lower() for item in args.languages.split(",") if item.strip()}
    if languages - {"r", "python"} or not languages:
        print("INIT_CODE_BLOCKED: languages must contain r and/or python", file=sys.stderr)
        return 2
    output.mkdir(parents=True, exist_ok=True)
    contract, pack = starter(args.module, args.quality_profile, args.effort_profile, languages, args.with_plot)
    # 审查记录属于模块级科学文档，不是生成合同工作区的子文件。
    # ``--output`` 通常是 MODULE/.code-contract。
    module_root = output.parent
    module_doc = module_root / "doc" / "source-review.md"
    if module_doc.is_file():
        # 在已有模块旁边生成脚手架时，合同绑定到已审查的真实源码，而不是新生成的示例。
        reviewed_root = module_root
        try:
            reviewed = source_review.source_inventory(reviewed_root)
            selected = next(
                (line.split(":", 1)[1].strip().strip("`")
                 for line in module_doc.read_text(encoding="utf-8").splitlines()
                 if line.strip().startswith("- canonical_source:") and ":" in line
                 and line.split(":", 1)[1].strip().strip("`") not in {"", "PENDING"}),
                None,
            )
            contract["canonical_source"] = selected or (reviewed[0]["path"] if reviewed else contract["canonical_source"])
        except (OSError, ValueError):
            pass
    write_json(output / "code_contract.json", contract)
    write_json(output / "analysis_evidence_pack.json", pack)
    if args.with_plot:
        write_json(
            output / "figure_manifest.json",
            {"schema_version": "0.1.0", "result_layout": "flat", "figures": []},
        )
    shutil.copyfile(TEMPLATES / "config.yaml", output / "config.yaml")
    if "r" in languages:
        shutil.copyfile(TEMPLATES / "r_stage.R", output / "r_stage.R")
    if "python" in languages:
        shutil.copyfile(TEMPLATES / "python_stage.py", output / "python_stage.py")
    # 模块尚无源码时不要伪造审查记录；第一步必须针对真实模块根目录执行
    # ``source-review init``，否则合同保持 EVIDENCE_NEEDED。
    print(json.dumps({"status": "DRAFT", "module": args.module, "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
