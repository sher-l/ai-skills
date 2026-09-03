#!/usr/bin/env python3
"""校验共享的机器可读分析证据包交接。

本适配器只检查事实、路径和 provenance；面向读者的正文、章节和解释由报告 skill 负责。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

import diagnostic_output


TOP_FIELDS = {
    "schema_version", "module", "quality_profile", "result_layout", "title",
    "audience", "references", "versions", "terminology_sources", "notes",
    "result_table", "output_table", "version_table", "evidence_targets", "analysis_points",
}
POINT_FIELDS = {
    "id", "title", "scope", "qc", "inputs", "method", "parameters",
    "statistical_unit", "comparison", "results", "outputs", "figure_table_refs",
    "notes", "result_table", "output_table", "version_table", "interpretation_level",
    "interpretation", "next_step", "limitations", "status",
}
REQUIRED_POINT_FIELDS = {
    "id", "title", "scope", "inputs", "method", "parameters", "results",
    "outputs", "figure_table_refs", "limitations", "status",
}
INTERPRETATION_LEVELS = {"descriptive", "association", "prediction", "candidate", "mechanistic_hint"}
STATUSES = {"complete", "valid_no_findings", "evidence_missing", "blocked"}
RESULT_NAME = re.compile(r"^[0-9]{2,}[._-][A-Za-z0-9][A-Za-z0-9._-]*\.[A-Za-z0-9]+$")
PLACEHOLDER = re.compile(r"(?:EVIDENCE_REQUIRED|EVIDENCE_NEEDED|TODO|TBD|REPLACE|XXX|PENDING)", re.I)


def diagnostics(errors: list[str], warnings: list[str], subject: str) -> list[dict[str, object]]:
    return diagnostic_output.entries(
        errors,
        warnings,
        subject,
        domain="evidence",
        fixes="补齐标记的事实或运行记录后重新运行校验",
    )


def _relative_path(value: object, label: str, root: Path | None, final: bool, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} needs a relative path")
        return
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        errors.append(f"{label} path must be relative")
        return
    if root is not None and final:
        candidate = (root / path).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            errors.append(f"{label} escapes root: {value}")
        else:
            if not candidate.is_file():
                errors.append(f"{label} file does not exist: {value}")


def _flat_path(value: object, label: str, layout: str, errors: list[str]) -> None:
    if layout != "flat" or not isinstance(value, str):
        return
    path = Path(value)
    if path.parts[:1] == ("result",) and (len(path.parts) != 2 or not RESULT_NAME.fullmatch(path.name)):
        errors.append(f"{label} must be a flat numbered result path: {value}")


def _string(value: object, label: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")


def validate(value: object, root: Path | None = None, final: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(value, dict):
        return ["evidence pack must be an object"], warnings
    errors.extend(f"unknown top-level field: {key}" for key in sorted(set(value) - TOP_FIELDS))
    for key in ("schema_version", "module", "quality_profile", "result_layout", "evidence_targets", "analysis_points"):
        if key not in value:
            errors.append(f"missing top-level field: {key}")
    if value.get("schema_version") != "0.1.0":
        errors.append("schema_version must be 0.1.0")
    if value.get("quality_profile") not in {"draft", "release"}:
        errors.append("quality_profile must be draft or release")
    if value.get("result_layout") not in {"flat", "module_contract"}:
        errors.append("result_layout must be flat or module_contract")
    if final and value.get("result_layout") != "flat":
        errors.append("release result_layout must be flat; migrate the historical module_contract layout first")
    layout = value.get("result_layout", "")
    for key in ("title", "audience"):
        if key in value and value[key] is not None and not isinstance(value[key], str):
            errors.append(f"{key} must be a string")
    for key in ("references", "versions"):
        if key in value and not isinstance(value[key], list):
            errors.append(f"{key} must be an array")
        elif isinstance(value.get(key), list):
            for index, source in enumerate(value[key]):
                if not isinstance(source, dict) or not all(isinstance(source.get(field), str) and source[field].strip() for field in ("name", "version")):
                    errors.append(f"{key}[{index}] needs name and version")
                elif any(field in source and not isinstance(source[field], str) for field in ("source", "purpose")):
                    errors.append(f"{key}[{index}] source/purpose must be strings")
    terminology = value.get("terminology_sources")
    if terminology is not None:
        if not isinstance(terminology, list):
            errors.append("terminology_sources must be an array")
        else:
            for index, item in enumerate(terminology):
                if isinstance(item, str):
                    if not item.strip():
                        errors.append(f"terminology_sources[{index}] must be non-empty")
                elif not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"].strip():
                    errors.append(f"terminology_sources[{index}] needs a name or non-empty string")

    targets = value.get("evidence_targets")
    if not isinstance(targets, list):
        errors.append("evidence_targets must be an array")
    else:
        target_ids: set[str] = set()
        for index, target in enumerate(targets):
            label = f"evidence_targets[{index}]"
            if not isinstance(target, dict):
                errors.append(f"{label} must be an object")
                continue
            unknown_target = sorted(set(target) - {"id", "title", "analysis_point_ids"})
            errors.extend(f"{label} unknown field: {key}" for key in unknown_target)
            if not isinstance(target.get("id"), str) or not target["id"].strip() or not isinstance(target.get("title"), str) or not target["title"].strip():
                errors.append(f"{label} needs id and title")
            elif target["id"] in target_ids:
                errors.append(f"duplicate evidence target: {target['id']}")
            else:
                target_ids.add(target["id"])
            if "analysis_point_ids" in target and (
                not isinstance(target["analysis_point_ids"], list)
                or any(not isinstance(item, str) or not item.strip() for item in target["analysis_point_ids"])
            ):
                errors.append(f"{label}.analysis_point_ids must be a string array")

    points = value.get("analysis_points")
    if not isinstance(points, list) or not points:
        errors.append("analysis_points must be a non-empty array")
        points = []
    point_ids: set[str] = set()
    output_ids: set[str] = set()
    figure_ids: set[str] = set()
    for index, point in enumerate(points):
        label = f"analysis_points[{index}]"
        if not isinstance(point, dict):
            errors.append(f"{label} must be an object")
            continue
        errors.extend(f"{label} unknown field: {key}" for key in sorted(set(point) - POINT_FIELDS))
        for key in REQUIRED_POINT_FIELDS:
            if key not in point:
                errors.append(f"{label} missing {key}")
        point_id = point.get("id")
        if not isinstance(point_id, str) or not re.fullmatch(r"AP-[0-9]{2,}", point_id):
            errors.append(f"{label}.id must match AP-NN")
        elif point_id in point_ids:
            errors.append(f"duplicate analysis point: {point_id}")
        else:
            point_ids.add(point_id)
        for key in ("title", "scope"):
            _string(point.get(key), f"{label}.{key}", errors)
        for key in ("qc", "statistical_unit", "interpretation"):
            if key in point and point[key] is not None:
                _string(point.get(key), f"{label}.{key}", errors)
        method = point.get("method")
        if not isinstance(method, dict):
            errors.append(f"{label}.method must be an object")
        else:
            _string(method.get("name"), f"{label}.method.name", errors)
            _string(method.get("version"), f"{label}.method.version", errors)
        if not isinstance(point.get("parameters"), dict):
            errors.append(f"{label}.parameters must be an object")
        if "interpretation_level" in point and point.get("interpretation_level") not in INTERPRETATION_LEVELS:
            errors.append(f"{label}.interpretation_level is invalid")
        if point.get("status") not in STATUSES:
            errors.append(f"{label}.status is invalid")
        if not isinstance(point.get("limitations"), list) or any(not isinstance(item, str) or not item.strip() for item in point.get("limitations", [])):
            errors.append(f"{label}.limitations must be a string array")
        comparison = point.get("comparison")
        if comparison is not None and not isinstance(comparison, dict):
            errors.append(f"{label}.comparison must be an object when declared")
        elif isinstance(comparison, dict):
            for key in ("target", "reference", "direction"):
                _string(comparison.get(key), f"{label}.comparison.{key}", errors)

        inputs = point.get("inputs")
        if not isinstance(inputs, list):
            errors.append(f"{label}.inputs must be an array")
        else:
            for item_index, item in enumerate(inputs):
                item_label = f"{label}.inputs[{item_index}]"
                if not isinstance(item, dict):
                    errors.append(f"{item_label} must be an object")
                    continue
                for key in ("id", "path", "identity"):
                    _string(item.get(key), f"{item_label}.{key}", errors)
                _relative_path(item.get("path"), item_label, root, final, errors)

        results = point.get("results")
        if not isinstance(results, list):
            errors.append(f"{label}.results must be an array")
        else:
            for item_index, item in enumerate(results):
                item_label = f"{label}.results[{item_index}]"
                if not isinstance(item, dict):
                    errors.append(f"{item_label} must be an object")
                    continue
                for key in ("name", "unit", "source"):
                    _string(item.get(key), f"{item_label}.{key}", errors)
                _relative_path(item.get("source"), f"{item_label}.source", root, final, errors)
                _flat_path(item.get("source"), f"{item_label}.source", layout, errors)

        for field in ("outputs", "figure_table_refs"):
            values = point.get(field)
            if not isinstance(values, list):
                errors.append(f"{label}.{field} must be an array")
                continue
            for item_index, item in enumerate(values):
                item_label = f"{label}.{field}[{item_index}]"
                if not isinstance(item, dict):
                    errors.append(f"{item_label} must be an object")
                    continue
                _string(item.get("id"), f"{item_label}.id", errors)
                _string(item.get("path"), f"{item_label}.path", errors)
                _relative_path(item.get("path"), item_label, root, final, errors)
                _flat_path(item.get("path"), item_label, layout, errors)
                item_id = item.get("id")
                seen = figure_ids if field == "figure_table_refs" else output_ids
                if isinstance(item_id, str) and item_id:
                    if item_id in seen:
                        errors.append(f"duplicate {field} id: {item_id}")
                    seen.add(item_id)
                if field == "outputs":
                    if not isinstance(item.get("kind"), str) or not item["kind"].strip():
                        errors.append(f"{item_label}.kind must be a non-empty string")
                    if type(item.get("published")) is not bool:
                        errors.append(f"{item_label}.published must be boolean")
                    if not isinstance(item.get("purpose"), str) or not item["purpose"].strip():
                        errors.append(f"{item_label}.purpose must be a non-empty string")
                    if "description" in item and not isinstance(item.get("description"), str):
                        errors.append(f"{item_label}.description must be a string")
                    consumers = item.get("consumers")
                    if not isinstance(consumers, list) or not consumers or any(
                        not isinstance(consumer, str) or not consumer.strip() for consumer in consumers
                    ):
                        errors.append(f"{item_label}.consumers must be a non-empty string array")
                elif item.get("kind") not in {"figure", "table"}:
                    errors.append(f"{item_label}.kind must be figure or table")
                if field == "figure_table_refs" and item.get("caption_fields") is not None and not isinstance(item.get("caption_fields"), dict):
                    errors.append(f"{item_label}.caption_fields must be an object")
        notes = point.get("notes")
        if notes is not None:
            if not isinstance(notes, list):
                errors.append(f"{label}.notes must be an array")
            else:
                for note_index, note in enumerate(notes):
                    note_label = f"{label}.notes[{note_index}]"
                    if not isinstance(note, dict):
                        errors.append(f"{note_label} must be an object")
                        continue
                    for key in ("id", "text"):
                        _string(note.get(key), f"{note_label}.{key}", errors)
                    if note.get("kind") is not None and note.get("kind") not in {"direction", "unit", "boundary", "interpretation"}:
                        errors.append(f"{note_label}.kind is invalid")
                    for key, expected in (("border", "#5B9BD5"), ("fill", "#DDEBF7"), ("label_color", "#2F75B5")):
                        if key in note and note[key] != expected:
                            errors.append(f"{note_label}.{key} must be {expected}")

    if isinstance(targets, list) and points:
        known_points = point_ids
        covered_points: set[str] = set()
        for index, target in enumerate(targets):
            if not isinstance(target, dict):
                continue
            mapped = target.get("analysis_point_ids")
            if mapped is None:
                if final:
                    errors.append(f"evidence_targets[{index}] must map analysis_point_ids in final evidence")
                continue
            for point_id in mapped if isinstance(mapped, list) else []:
                if point_id not in known_points:
                    errors.append(f"evidence_targets[{index}] references unknown analysis point: {point_id}")
                covered_points.add(point_id)
        if final:
            missing_points = sorted(known_points - covered_points)
            if missing_points:
                errors.append(f"final evidence targets do not cover analysis points: {missing_points}")

    if PLACEHOLDER.search(json.dumps(value, ensure_ascii=False)):
        warnings.append("evidence pack contains draft markers")
    if final:
        if value.get("quality_profile") != "release":
            errors.append("final validation requires quality_profile=release")
        for index, point in enumerate(points):
            if not isinstance(point, dict):
                continue
            if point.get("status") not in {"complete", "valid_no_findings"}:
                errors.append(f"final requires evidence-complete status at analysis_points[{index}]")
            if not isinstance(point.get("next_step"), str) or not point["next_step"].strip():
                errors.append(f"final requires next_step at analysis_points[{index}]")
            if not point.get("limitations"):
                errors.append(f"final requires limitations at analysis_points[{index}]")
        if not value.get("references"):
            errors.append("final requires references")
        if not value.get("versions"):
            errors.append("final requires versions")
        if PLACEHOLDER.search(json.dumps(value, ensure_ascii=False)):
            errors.append("final validation rejects draft markers")
        warnings.clear()
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    try:
        value = json.loads(args.pack.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        value = None
        errors, warnings = [f"cannot read evidence pack: {exc}"], []
    else:
        errors, warnings = validate(value, args.root.resolve() if args.root else None, args.final)
    if errors:
        status = "BLOCKED"
    elif not args.final:
        status = "EVIDENCE_NEEDED"
        if not warnings:
            warnings.append("validation without --final is not a release PASS")
    elif isinstance(value, dict) and value.get("quality_profile") == "release":
        status = "PASS"
    else:
        status = "BLOCKED"
    code = diagnostic_output.exit_code(errors, warnings, status=status, domain="evidence")
    result = {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "diagnostics": diagnostics(errors, warnings, str(args.pack)),
        "exit_code": code,
        "summary": {"errors": len(errors), "warnings": len(warnings)},
    }
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        diagnostic_output.print_result(
            "EVIDENCE_PACK",
            status,
            errors,
            warnings,
            domain="evidence",
            fixes="补齐标记的事实或运行记录后重新运行校验",
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
