#!/usr/bin/env python3
"""Render a deterministic draft slot scaffold; never a reader-facing final report."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

from render_text import (
    comparison_text,
    compact,
    figure_ref_texts,
    marker,
    method_text,
    parameters_text,
    reference_texts,
    result_texts,
)
from validate_report_contract import normalise_relative, section_semantics, validate_flat_result_paths, validate_pack, validate_plan


def read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def text(value: object, marker_name: str) -> str:
    if value is None or value == "" or value == [] or value == {}:
        return marker(marker_name)
    return compact(value, marker_name)


def point_block(point: dict, mode: str) -> list[str]:
    lines = [f"### {text(point.get('title'), point.get('id', 'AP'))}"]
    if mode == "methods":
        lines += [
            f"- 输入与范围：{text(point.get('scope'), point.get('id', 'AP') + '.scope')}",
            f"- 方法与版本：{method_text(point.get('method'), point.get('id', 'AP') + '.method')}",
            f"- 参数与统计口径：{parameters_text(point.get('parameters'), point.get('id', 'AP') + '.parameters')}",
            f"- 推断单位与比较方向：{comparison_text(point, point.get('id', 'AP') + '.comparison')}",
        ]
    elif mode == "results":
        lines += [
            f"- 结果：{result_texts(point.get('results'), point.get('id', 'AP') + '.results')}",
            f"- 图表与文件：{figure_ref_texts(point.get('figure_table_refs'), point.get('id', 'AP') + '.figure_table_refs')}",
            f"- 领域解释：{text(point.get('interpretation'), point.get('id', 'AP') + '.interpretation')}",
            f"- 下一步用途：{text(point.get('next_step'), point.get('id', 'AP') + '.next_step')}",
        ]
    elif mode == "qc":
        lines += [f"- 可核对质控与异常：{text(point.get('qc'), point.get('id', 'AP') + '.qc')}" ]
    elif mode == "limitations":
        lines += [
            f"- 状态：{text(point.get('status'), point.get('id', 'AP') + '.status')}",
            f"- 限制与待验证：{text(point.get('limitations'), point.get('id', 'AP') + '.limitations')}",
        ]
    elif mode == "conclusion":
        lines += [f"- 结论回收：{text(point.get('interpretation'), point.get('id', 'AP') + '.conclusion')}" ]
    return lines


def md_cell(value: object, field: str) -> str:
    return text(value, field).replace("|", "\\|").replace("\n", " ")


def render(plan: dict, pack: dict) -> str:
    points = {point.get("id"): point for point in pack.get("analysis_points", []) if isinstance(point, dict)}
    out: list[str] = [
        "<!-- DRAFT SCAFFOLD: generic key-value preview; use the module renderer for delivery. -->",
        f"# {text(plan.get('title'), 'title')}",
        "",
    ]
    for section in plan.get("sections", []):
        sid = section.get("id")
        title = text(section.get("title"), sid or "section")
        out += [f"## {title}", ""]
        ids = section.get("analysis_point_ids", [])
        semantics = section_semantics(section)
        if sid == "summary" or "summary" in semantics:
            summaries = [
                f"{text(point.get('title'), point.get('id', 'AP'))}：{result_texts(point.get('results'), point.get('id', 'AP') + '.results')}"
                for point in points.values()
            ]
            out.extend(summaries or [marker("summary")])
        elif sid == "scope" or "scope" in semantics:
            for point in points.values():
                out += [f"- {text(point.get('title'), point.get('id', 'AP'))}：{text(point.get('scope'), point.get('id', 'AP') + '.scope')}"]
        elif sid in {"methods", "qc", "results", "conclusion", "limitations"} or semantics.intersection({"method", "qc", "results", "interpretation", "limitations"}):
            mode = sid
            if "method" in semantics:
                mode = "methods"
            elif "qc" in semantics:
                mode = "qc"
            elif "limitations" in semantics:
                mode = "limitations"
            elif "interpretation" in semantics and "results" not in semantics:
                mode = "conclusion"
            else:
                mode = "results"
            for point_id in ids:
                if point_id not in points:
                    out += [f"[[EVIDENCE_REQUIRED:{point_id}]]", ""]
                else:
                    out += point_block(points[point_id], mode) + [""]
        elif sid == "outputs" or "outputs" in semantics:
            outputs = [item for point in points.values() for item in point.get("outputs", []) if isinstance(item, dict) and item.get("published")]
            report_file = normalise_relative(plan.get("output_policy", {}).get("report_file"))
            outputs = [item for item in outputs if normalise_relative(item.get("path")) != report_file]
            if outputs:
                out += ["| 文件 | 类型 | 用途 |", "|---|---|---|"]
                for item in outputs:
                    out.append(f"| {md_cell(item.get('path'), item.get('id', 'OUT') + '.path')} | {md_cell(item.get('kind'), item.get('id', 'OUT') + '.kind')} | {md_cell(item.get('purpose', ''), item.get('id', 'OUT') + '.purpose')} |")
            else:
                out += ["[[EVIDENCE_REQUIRED:published_outputs]]"]
        elif sid == "references" or "references" in semantics:
            if pack.get("references"):
                out += [f"- {reference_texts(pack.get('references'), 'used_references')}"]
            else:
                out += ["[[EVIDENCE_REQUIRED:used_references]]"]
        elif sid == "versions" or "versions" in semantics:
            if pack.get("versions"):
                out += [f"- {reference_texts(pack.get('versions'), 'software_versions')}"]
            else:
                out += ["[[EVIDENCE_REQUIRED:software_versions]]"]
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--evidence-pack", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--root", type=Path, help="root for relative published paths")
    args = parser.parse_args(argv)
    try:
        plan = read(args.plan)
        pack = read(args.evidence_pack)
        point_ids = {item.get("id") for item in pack.get("analysis_points", []) if isinstance(item, dict)}
        root = (args.root or args.evidence_pack.parent).resolve()
        if not root.is_dir():
            raise ValueError(f"artifact root does not exist or is not a directory: {root}")
        preflight = validate_pack(pack, root=root, require_files=False) + validate_plan(plan, point_ids)
        if pack.get("result_layout") != plan.get("result_layout"):
            preflight.append("plan and evidence pack result_layout must match")
        if plan.get("result_layout") == "flat":
            preflight += validate_flat_result_paths(pack)
        pack_ref = plan.get("evidence_pack") if isinstance(plan, dict) else None
        if isinstance(pack_ref, str) and pack_ref.strip() and (args.plan.parent / pack_ref.replace("\\", "/")).resolve() != args.evidence_pack.resolve():
            preflight.append("plan evidence_pack does not match --evidence-pack")
        if preflight:
            raise ValueError("preflight: " + "; ".join(preflight))
        rendered = render(plan, pack)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.output.parent, prefix=f".{args.output.name}.", delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(rendered)
            os.replace(temporary, args.output)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"REPORT_SKELETON_BLOCKED: {exc}", file=sys.stderr)
        return 2
    data = args.output.read_bytes()
    print(f"REPORT_SKELETON_DRAFT output={args.output.resolve()} bytes={len(data)} sha256={hashlib.sha256(data).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
