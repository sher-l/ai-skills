#!/usr/bin/env python3
"""Validate a R/Python code contract after the module source review gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


PLACEHOLDER = re.compile(r"(?:TODO|REPLACE|EVIDENCE_REQUIRED|EVIDENCE_NEEDED|XXX|\bXX\b|PENDING)", re.IGNORECASE)
ABSOLUTE = re.compile(r"(?:^|[=:(,\s])(?:/media/|/home/|[A-Za-z]:[\\/])")
RISK_PATTERNS = {
    "absolute_path": ABSOLUTE,
    "placeholder": PLACEHOLDER,
    "global_workspace_reset": re.compile(r"rm\s*\(\s*list\s*=\s*ls\s*\(", re.I),
    "global_warning_suppression": re.compile(r"options\s*\(\s*warn\s*=\s*-1", re.I),
    "runtime_install": re.compile(r"(?:install\.packages\s*\(|pip\s+install\b|conda\s+install\b)", re.I),
    "working_directory_mutation": re.compile(r"(?:^|\n)\s*setwd\s*\(", re.I),
    "silent_error": re.compile(r"(?:except\s*:\s*pass|tryCatch\s*\([^\n]*error\s*=\s*function\s*\([^)]*\)\s*\{\s*\})", re.I),
}
SKIP_DIRS = {".git", ".venv", "venv", "cache", "log", "report", "result", "output", "__pycache__", "doc", "docs", ".code-contract"}
RESULT_NAME = re.compile(r"^[0-9]{2,}[._-][A-Za-z0-9][A-Za-z0-9._-]*\.[A-Za-z0-9]+$")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def validate_output_declarations(value: dict, errors: list[str], warnings: list[str], *, final: bool) -> None:
    """Require a purpose and consumer for every public output declaration."""
    collections: list[tuple[str, object]] = [("outputs", value.get("outputs"))]
    for index, stage in enumerate(value.get("stages", []) if isinstance(value.get("stages"), list) else []):
        if isinstance(stage, dict):
            collections.append((f"stages[{index}].outputs", stage.get("outputs")))
    for label, items in collections:
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            prefix = f"{label}[{index}]"
            missing: list[str] = []
            if not isinstance(item.get("id"), str) or not item["id"].strip():
                missing.append("id")
            if not isinstance(item.get("purpose"), str) or not item["purpose"].strip():
                missing.append("purpose")
            consumers = item.get("consumers")
            if not isinstance(consumers, list) or not consumers or any(not isinstance(c, str) or not c.strip() for c in consumers):
                missing.append("consumers")
            if missing:
                message = f"{prefix} needs declared id/purpose/consumers"
                (errors if final else warnings).append(message)


def validate_contract(value: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["contract must be a JSON object"]
    required = {
        "schema_version", "module", "description", "help", "quality_profile",
        "effort_profile", "max_repair_rounds", "result_layout", "canonical_source",
        "stages", "inputs", "outputs", "evidence_pack",
    }
    optional = {"source_review", "statistics", "plot", "environment", "provenance"}
    extra = sorted(set(value) - required - optional)
    for key in extra:
        fail(errors, f"unknown top-level field: {key}")
    for key in sorted(required - set(value)):
        fail(errors, f"missing top-level field: {key}")
    if value.get("schema_version") != "0.1.0":
        fail(errors, "schema_version must be 0.1.0")
    if value.get("quality_profile") not in {"draft", "release"}:
        fail(errors, "quality_profile must be draft or release")
    if value.get("effort_profile") not in {"mechanical", "scientific_review"}:
        fail(errors, "effort_profile must be mechanical or scientific_review")
    if type(value.get("max_repair_rounds")) is not int or not 0 <= value["max_repair_rounds"] <= 2:
        fail(errors, "max_repair_rounds must be an integer from 0 to 2")
    if value.get("result_layout") not in {"flat", "module_contract"}:
        fail(errors, "result_layout must be flat or module_contract")
    for key in ("module", "description", "canonical_source", "evidence_pack"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            fail(errors, f"{key} must be a non-empty string")
    canonical = value.get("canonical_source")
    if isinstance(canonical, str) and (Path(canonical).is_absolute() or ".." in Path(canonical).parts):
        fail(errors, "canonical_source must be relative and stay inside the module")
    for key in ("evidence_pack",):
        path_value = value.get(key)
        if isinstance(path_value, str) and (Path(path_value).is_absolute() or ".." in Path(path_value).parts):
            fail(errors, f"{key} must be relative and stay inside the module")
    source_review = value.get("source_review")
    if source_review is not None:
        if not isinstance(source_review, str) or not source_review.strip():
            fail(errors, "source_review must be a non-empty relative path")
        elif Path(source_review).is_absolute() or ".." in Path(source_review).parts:
            fail(errors, "source_review must be relative and stay inside the module")
    stages = value.get("stages")
    if not isinstance(stages, list) or not stages:
        fail(errors, "stages must contain at least one stage")
    else:
        ids: set[str] = set()
        for index, stage in enumerate(stages):
            if not isinstance(stage, dict):
                fail(errors, f"stages[{index}] must be an object")
                continue
            stage_extra = sorted(set(stage) - {"id", "purpose", "inputs", "outputs", "method", "parameters", "seed", "non_degenerate", "provenance", "lineage", "error_policy"})
            for key in stage_extra:
                fail(errors, f"stages[{index}] unknown field: {key}")
            for key in ("id", "purpose", "inputs", "outputs", "method", "parameters", "seed", "non_degenerate"):
                if key not in stage:
                    fail(errors, f"stages[{index}] missing {key}")
            stage_id = stage.get("id")
            if not isinstance(stage_id, str) or not stage_id.strip():
                fail(errors, f"stages[{index}].id must be non-empty")
            elif stage_id in ids:
                fail(errors, f"duplicate stage id: {stage_id}")
            else:
                ids.add(stage_id)
            stage_outputs = stage.get("outputs")
            if isinstance(stage_outputs, list):
                for output_index, item in enumerate(stage_outputs):
                    if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                        continue
                    path = Path(item["path"])
                    if path.is_absolute() or ".." in path.parts:
                        fail(errors, f"stages[{index}].outputs[{output_index}] path must be relative: {item['path']}")
                        continue
                    if value.get("result_layout") == "flat" and path.parts[:1] == ("result",):
                        if len(path.parts) != 2:
                            fail(errors, f"stages[{index}].outputs[{output_index}] public result path must be directly under result/: {item['path']}")
                        elif not RESULT_NAME.fullmatch(path.name):
                            fail(errors, f"stages[{index}].outputs[{output_index}] result filename must use NN.semantic_name.ext: {item['path']}")
    for key in ("inputs", "outputs"):
        if not isinstance(value.get(key), list):
            fail(errors, f"{key} must be an array")
    for collection_name in ("inputs", "outputs"):
        collection = value.get(collection_name)
        if isinstance(collection, list):
            for index, item in enumerate(collection):
                if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                    continue
                path = Path(item["path"])
                if path.is_absolute() or ".." in path.parts:
                    fail(errors, f"{collection_name}[{index}] path must be relative: {item['path']}")
                    continue
                if value.get("result_layout") == "flat" and path.parts[:1] == ("result",):
                    if len(path.parts) != 2:
                        fail(errors, f"{collection_name}[{index}] public result path must be directly under result/: {item['path']}")
                    elif not RESULT_NAME.fullmatch(path.name):
                        fail(errors, f"{collection_name}[{index}] result filename must use NN.semantic_name.ext: {item['path']}")
    stats = value.get("statistics")
    if stats is not None and not isinstance(stats, dict):
        fail(errors, "statistics must be an object when declared")
    elif isinstance(stats, dict):
        for key in sorted(set(stats) - {"statistical_unit", "comparison", "correction", "thresholds"}):
            fail(errors, f"statistics unknown field: {key}")
        for key in ("statistical_unit", "comparison", "correction", "thresholds"):
            if key not in stats:
                fail(errors, f"statistics missing {key}")
        comparison = stats.get("comparison")
        if isinstance(comparison, dict):
            for key in sorted(set(comparison) - {"target", "reference", "metric", "direction"}):
                fail(errors, f"statistics.comparison unknown field: {key}")
            for key in ("target", "reference", "direction"):
                if not isinstance(comparison.get(key), str) or not comparison[key].strip():
                    fail(errors, f"statistics.comparison.{key} must be non-empty")
    plot = value.get("plot")
    if plot is not None and isinstance(plot, dict):
        for key in sorted(set(plot) - {"figure_manifest"}):
            fail(errors, f"plot unknown field: {key}")
    if plot is not None and (
        not isinstance(plot, dict)
        or not isinstance(plot.get("figure_manifest"), str)
        or not plot["figure_manifest"].strip()
    ):
        fail(errors, "plot.figure_manifest must be a non-empty string when plot is declared")
    help_value = value.get("help")
    if not isinstance(help_value, dict):
        fail(errors, "help must be an object with command descriptions")
    else:
        for key in sorted(set(help_value) - {"summary", "commands"}):
            fail(errors, f"help unknown field: {key}")
        if not isinstance(help_value.get("summary"), str) or not help_value["summary"].strip():
            fail(errors, "help.summary must be a non-empty string")
        if not isinstance(help_value.get("commands"), dict):
            fail(errors, "help.commands must be an object")
        elif any(not isinstance(key, str) or not key.strip() or not isinstance(command, str) or not command.strip() for key, command in help_value["commands"].items()):
            fail(errors, "help.commands must map names to non-empty descriptions")
    return errors


def scan_sources(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not root.exists():
        return [f"source root does not exist: {root}"], warnings
    files = [
        path for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".r", ".rmd", ".py"}
        and not any(part in SKIP_DIRS for part in path.relative_to(root).parts)
    ]
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"{path}: not UTF-8 source")
            continue
        for name, pattern in RISK_PATTERNS.items():
            if pattern.search(text):
                if name in {"placeholder", "absolute_path", "runtime_install"}:
                    errors.append(f"{path}: {name}")
                else:
                    warnings.append(f"{path}: review {name}")
        if re.search(r"\bna\.omit\s*\(", text) and not re.search(r"dropped|removed|before|after", text, re.I):
            warnings.append(f"{path}: na.omit without visible loss accounting")
    return errors, warnings


def contains_placeholder(value: object) -> bool:
    if isinstance(value, str):
        return bool(PLACEHOLDER.search(value))
    if isinstance(value, dict):
        return any(contains_placeholder(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_placeholder(item) for item in value)
    return False


def diagnostics(errors: list[str], warnings: list[str], subject: str) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for message in errors:
        if "placeholder" in message:
            code = "draft/unresolved-marker"
        elif "absolute" in message:
            code = "source/absolute-path"
        elif "runtime_install" in message:
            code = "runtime/dependency-install"
        elif "canonical" in message:
            code = "contract/canonical-source"
        elif "missing" in message:
            code = "contract/missing-field"
        else:
            code = "contract/invalid"
        entries.append({"code": code, "severity": "error", "message": message, "subject": {"path": subject}, "evidence": {}, "supportedFixes": ["edit the named contract or source and run validation again"]})
    for message in warnings:
        entries.append({"code": "review/manual-check", "severity": "warning", "message": message, "subject": {"path": subject}, "evidence": {}, "supportedFixes": ["review the named item and record the decision"]})
    return entries


def _source_review_result(contract: object, root: Path, final: bool, required: bool = False) -> tuple[list[str], list[str]]:
    """Run the optional Step-0 review without making it a second dependency."""
    if not isinstance(contract, dict):
        return [], []
    review = contract.get("source_review")
    if not isinstance(review, str) or not review.strip():
        return (["source_review is required before code validation"], []) if (final or required) else ([], ["source_review is not declared; run source-review init first"])
    if Path(review).as_posix() != "doc/source-review.md":
        message = "source_review must point to module-local doc/source-review.md"
        return ([message], []) if final or required else ([], [message])
    review_path = (root / review).resolve()
    try:
        review_path.relative_to(root.resolve())
    except ValueError:
        return ([f"source_review escapes source root: {review}"], [])
    if not review_path.is_file():
        return ([f"source_review does not exist under source root: {review}"], []) if final else ([], [f"source_review evidence needed: {review}"])
    try:
        import source_review

        result = source_review.validate_document(review_path, root, final=final)
    except (ImportError, OSError, ValueError) as exc:
        return ([f"cannot validate source_review: {exc}"], [])
    review_errors = [f"source_review: {item}" for item in result.get("errors", [])]
    review_warnings = [f"source_review: {item}" for item in result.get("warnings", [])]
    if result.get("status") == "DECISION_REQUIRED":
        review_errors.append("source_review returned DECISION_REQUIRED")
    elif result.get("status") not in {"PASS"}:
        review_warnings.append(f"source_review status={result.get('status', 'EVIDENCE_NEEDED')}")
    return review_errors, review_warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--final", action="store_true", help="把草稿占位符和警告升级为 final 门禁")
    parser.add_argument("--require-source-review", action="store_true", help="要求并验证 module-local doc/source-review.md")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    errors: list[str] = []
    warnings: list[str] = []
    try:
        value = json.loads(args.contract.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"cannot read contract: {exc}")
        value = None
    errors.extend(validate_contract(value))
    if isinstance(value, dict):
        validate_output_declarations(value, errors, warnings, final=args.final)
    if contains_placeholder(value):
        warnings.append("contract contains draft placeholders")
    if args.final and contains_placeholder(value):
        errors.append("contract contains an unresolved placeholder")
    if args.final and isinstance(value, dict) and value.get("quality_profile") != "release":
        errors.append("final validation requires quality_profile=release")
    if args.final and isinstance(value, dict):
        help_value = value.get("help")
        if isinstance(help_value, dict) and not help_value.get("commands"):
            errors.append("final validation requires help.commands")
        if not isinstance(value.get("source_review"), str) or not value["source_review"].strip():
            errors.append("final validation requires source_review=doc/source-review.md")
    if args.source_root:
        source_errors, source_warnings = scan_sources(args.source_root.resolve())
        for message in source_errors:
            if not args.final and "placeholder" in message:
                source_warnings.append(message)
            else:
                errors.append(message)
        warnings.extend(source_warnings)
        if isinstance(value, dict):
            canonical = value.get("canonical_source")
            if isinstance(canonical, str) and canonical and not (args.source_root / canonical).is_file():
                errors.append(f"canonical_source does not exist under source root: {canonical}")
            review_errors, review_warnings = _source_review_result(value, args.source_root.resolve(), args.final, args.require_source_review)
            errors.extend(review_errors)
            warnings.extend(review_warnings)
    elif args.require_source_review:
        errors.append("--require-source-review needs --source-root")
    elif args.final and isinstance(value, dict) and isinstance(value.get("source_review"), str):
        local_review = (args.contract.parent / value["source_review"]).resolve()
        if not local_review.is_file():
            errors.append(f"source_review cannot be verified without --source-root: {value['source_review']}")
    if args.final and warnings:
        errors.extend(f"final review required: {warning}" for warning in warnings)
    if errors:
        status = "BLOCKED"
    elif not args.final:
        status = "EVIDENCE_NEEDED"
        if not warnings:
            warnings.append("validation without --final is not a release PASS")
    elif warnings:
        status = "EVIDENCE_NEEDED"
    elif isinstance(value, dict) and value.get("quality_profile") == "release":
        status = "PASS"
    else:
        status = "BLOCKED"
    result = {"status": status, "errors": errors, "warnings": warnings, "diagnostics": diagnostics(errors, warnings, str(args.contract)), "summary": {"errors": len(errors), "warnings": len(warnings)}}
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"CODE_CONTRACT_{result['status']} errors={len(errors)} warnings={len(warnings)}")
        for item in errors + warnings:
            print(item, file=sys.stderr if item in errors else sys.stdout)
    return 0 if status == "PASS" and not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
