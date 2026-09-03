#!/usr/bin/env python3
"""校验图件声明及其真实、可复现的来源。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

import diagnostic_output


FORMATS = {"png", "pdf"}
RESULT_NAME = re.compile(r"^[0-9]{2,}[._-][A-Za-z0-9][A-Za-z0-9._-]*\.[A-Za-z0-9]+$")
PLACEHOLDER = re.compile(r"(?:TODO|TBD|REPLACE|PENDING|EVIDENCE_REQUIRED|EVIDENCE_NEEDED|XXX)", re.I)


def make_diagnostics(errors: list[str], warnings: list[str], subject: str) -> list[dict[str, object]]:
    return diagnostic_output.entries(
        errors,
        warnings,
        subject,
        domain="figure",
        fixes="编辑图件合同或真实来源后重新运行校验",
    )


def _relative(value: object, label: str, root: Path, final: bool, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty relative path")
        return
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        errors.append(f"{label} must be relative")
        return
    if final:
        candidate = (root / path).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            errors.append(f"{label} escapes root: {value}")
        else:
            if not candidate.is_file():
                errors.append(f"{label} does not exist: {value}")


def validate(value: object, root: Path, final: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(value, dict):
        return ["manifest must be an object"], warnings
    errors.extend(f"unknown top-level field: {key}" for key in sorted(set(value) - {"schema_version", "result_layout", "figures"}))
    if value.get("schema_version") != "0.1.0":
        errors.append("schema_version must be 0.1.0")
    layout = value.get("result_layout")
    if layout != "flat":
        errors.append("v2.2 figure manifest result_layout must be flat")
    figures = value.get("figures")
    if not isinstance(figures, list):
        return errors + ["figures must be an array"], warnings
    seen: set[str] = set()
    for index, figure in enumerate(figures):
        label = f"figures[{index}]"
        if not isinstance(figure, dict):
            errors.append(f"{label} must be an object")
            continue
        allowed = {"id", "source", "formats", "width", "height", "dpi", "font", "renderer", "provenance", "panels", "crop", "split", "source_code", "data_sources", "run_record"}
        errors.extend(f"{label} unknown field: {key}" for key in sorted(set(figure) - allowed))
        for key in ("id", "source", "formats", "width", "height", "dpi", "font", "renderer", "provenance"):
            if key not in figure:
                errors.append(f"{label} missing {key}")
        figure_id = figure.get("id")
        if not isinstance(figure_id, str) or not figure_id.strip():
            errors.append(f"{label}.id must be non-empty")
        elif figure_id in seen:
            errors.append(f"duplicate figure id: {figure_id}")
        else:
            seen.add(figure_id)
        source = figure.get("source")
        if isinstance(source, str):
            _relative(source, f"{label}.source", root, final, errors)
            source_path = Path(source)
            if layout == "flat" and source_path.parts[:1] == ("result",) and (len(source_path.parts) != 2 or not RESULT_NAME.fullmatch(source_path.name)):
                errors.append(f"{label}.source in result/ must use flat NN.semantic_name.ext: {source}")
            formats = figure.get("formats") if isinstance(figure.get("formats"), list) else []
            for fmt in formats:
                companion = (root / source_path.with_suffix(f".{fmt}")).resolve()
                if final and not companion.is_file():
                    errors.append(f"{label} declared {fmt} file does not exist beside source")
                elif not companion.is_file() and companion != (root / source_path).resolve():
                    warnings.append(f"{label}: declared {fmt} file is not beside source")
        elif source is not None:
            errors.append(f"{label}.source must be a non-empty relative path")
        formats = figure.get("formats")
        if not isinstance(formats, list) or not formats:
            errors.append(f"{label}.formats must be a non-empty array")
        elif any(not isinstance(fmt, str) for fmt in formats) or not set(formats).issubset(FORMATS) or len(set(formats)) != len(formats):
            errors.append(f"{label}.formats contains unsupported or duplicate format")
        for key in ("width", "height", "dpi"):
            if not isinstance(figure.get(key), (int, float)) or figure[key] <= 0:
                errors.append(f"{label}.{key} must be positive")
        provenance = figure.get("provenance")
        if not isinstance(provenance, dict) or not provenance:
            errors.append(f"{label}.provenance must identify source data and parameters")
        else:
            # 这些字段可以放在 manifest 顶层或 provenance 内；最终检查要求三条真实链接都存在。
            source_code = figure.get("source_code", provenance.get("source_code"))
            data_sources = figure.get("data_sources", provenance.get("data_sources"))
            run_record = figure.get("run_record", provenance.get("run_record"))
            if final:
                _relative(source_code, f"{label}.source_code", root, True, errors)
                if not isinstance(data_sources, list) or not data_sources:
                    errors.append(f"{label}.data_sources must be a non-empty path array")
                else:
                    for item_index, item in enumerate(data_sources):
                        _relative(item, f"{label}.data_sources[{item_index}]", root, True, errors)
                _relative(run_record, f"{label}.run_record", root, True, errors)
            elif any((source_code is None, data_sources is None, run_record is None)):
                warnings.append(f"{label}: provenance should bind source_code, data_sources and run_record")
        panels = figure.get("panels")
        if panels is not None and (not isinstance(panels, list) or any(not isinstance(panel, str) or not panel.strip() for panel in panels)):
            errors.append(f"{label}.panels must be a string array")
        if panels is not None and isinstance(panels, list) and len(set(panels)) != len(panels):
            errors.append(f"{label}.panels must be unique")
        for key in ("font", "renderer"):
            if not isinstance(figure.get(key), str) or not figure[key].strip():
                errors.append(f"{label}.{key} must be a non-empty string")
        if figure.get("crop") not in (None, False, {"left": 0, "top": 0, "right": 0, "bottom": 0}):
            errors.append(f"{label}.crop must be absent or zero")
        if figure.get("split") not in (None, False):
            errors.append(f"{label}.split must be false or absent")
        if "png" not in (formats or []) or "pdf" not in (formats or []):
            message = f"{label}: both PNG and PDF are not declared"
            (errors if final else warnings).append(message)
    if PLACEHOLDER.search(json.dumps(value, ensure_ascii=False)):
        warnings.append("figure manifest contains draft markers")
    if final and warnings:
        errors.extend(f"final review required: {warning}" for warning in warnings)
        warnings.clear()
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args(argv)
    try:
        value = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        value = None
        errors, warnings = [f"cannot read figure manifest: {exc}"], []
    else:
        errors, warnings = validate(value, args.root.resolve(), final=args.final)
    if errors:
        status = "BLOCKED"
    elif args.final:
        status = "PASS"
    elif warnings:
        status = "EVIDENCE_NEEDED"
    else:
        # 草稿 manifest 只是脚手架，不能作为发布 PASS。
        status = "EVIDENCE_NEEDED"
    code = diagnostic_output.exit_code(errors, warnings, status=status, domain="figure")
    result = {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "diagnostics": make_diagnostics(errors, warnings, str(args.manifest)),
        "exit_code": code,
        "summary": {"errors": len(errors), "warnings": len(warnings)},
    }
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        diagnostic_output.print_result(
            "FIGURE_MANIFEST",
            status,
            errors,
            warnings,
            domain="figure",
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
