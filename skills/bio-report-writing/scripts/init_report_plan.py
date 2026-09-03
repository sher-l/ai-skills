#!/usr/bin/env python3
"""Create a draft report plan from a structured evidence pack."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def make_plan(
    pack: dict,
    evidence_path: Path,
    *,
    mode: str = "module",
    title: str | None = None,
    audience: str | None = None,
) -> dict:
    points = pack.get("analysis_points")
    if not isinstance(points, list) or not points:
        raise ValueError("analysis_points must contain at least one item")
    ids: list[str] = []
    for index, point in enumerate(points):
        if not isinstance(point, dict) or not isinstance(point.get("id"), str):
            raise ValueError(f"analysis_points[{index}] needs a string id")
        ids.append(point["id"])
    targets = pack.get("evidence_targets")
    if not isinstance(targets, list):
        targets = [{"id": f"ET-{index:02d}", "title": point.get("title", point["id"])} for index, point in enumerate(points, 1)]
    sections = [
        {"id": "summary", "title": "摘要", "required": True, "analysis_point_ids": [], "semantic": "summary"},
        {"id": "scope", "title": "数据范围与分析边界", "required": True, "analysis_point_ids": [], "semantic": "scope"},
        {"id": "methods", "title": "材料与方法", "required": True, "analysis_point_ids": ids, "semantic": "method"},
    ]
    if any(isinstance(point, dict) and point.get("qc") not in (None, "", []) for point in points):
        sections.append({"id": "qc", "title": "质控与异常", "required": True, "analysis_point_ids": ids, "semantic": "qc"})
    sections.extend([
        {"id": "results", "title": "分析结果与解读", "required": True, "analysis_point_ids": ids, "semantic": ["results", "interpretation"]},
        {"id": "conclusion", "title": "综合结论", "required": True, "analysis_point_ids": ids, "semantic": "interpretation"},
        {"id": "limitations", "title": "局限、未完成与待验证", "required": True, "analysis_point_ids": ids, "semantic": "limitations"},
        {"id": "outputs", "title": "输出文件说明", "required": True, "analysis_point_ids": [], "semantic": "outputs"},
        {"id": "references", "title": "参考文献", "required": True, "analysis_point_ids": [], "semantic": "references"},
        {"id": "versions", "title": "软件与资源版本", "required": True, "analysis_point_ids": [], "semantic": "versions"},
    ])
    return {
        "schema_version": "0.1.0",
        "module": str(pack.get("module") or "module"),
        "mode": mode,
        "quality_profile": pack.get("quality_profile") if pack.get("quality_profile") in {"draft", "release"} else "draft",
        "effort_profile": pack.get("effort_profile") if pack.get("effort_profile") in {"mechanical", "scientific_review"} else "mechanical",
        "max_repair_rounds": 2,
        "result_layout": str(pack.get("result_layout") or "flat"),
        "title": str(title if title is not None else pack.get("title", "生物信息学分析结果")),
        # Never invent a reader.  A missing audience remains a draft gap and
        # is rejected by the release validator.
        "audience": str(audience if audience is not None else pack.get("audience", "")),
        "evidence_pack": str(evidence_path),
        "template": "report_templates/report_template.docx" if mode == "module" else "report_template.docx",
        "evidence_targets": targets,
        "sections": sections,
        "output_policy": {
            "report_file": "report/analysis_report.docx" if mode == "module" else "analysis_report.docx",
            "include_pdf": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-pack", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mode", choices=("module", "one_off"), default="module")
    parser.add_argument("--title")
    parser.add_argument("--audience")
    args = parser.parse_args(argv)
    try:
        evidence_path = args.evidence_pack.resolve()
        output_path = args.output.resolve()
        evidence_ref = Path(os.path.relpath(evidence_path, output_path.parent))
        plan = make_plan(
            read_json(evidence_path),
            evidence_ref,
            mode=args.mode,
            title=args.title,
            audience=args.audience,
        )
        if args.output.exists():
            print(f"REPORT_PLAN_BLOCKED: output exists: {args.output}", file=sys.stderr)
            return 2
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"REPORT_PLAN_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(
        f"REPORT_PLAN_INIT_DRAFT output={args.output.resolve()} "
        f"quality_profile={plan.get('quality_profile', 'draft')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
