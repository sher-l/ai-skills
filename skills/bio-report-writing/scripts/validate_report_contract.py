#!/usr/bin/env python3
"""Validate report slots/evidence; only --final release checks can return PASS."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from pathlib import PurePosixPath
import re
import sys


QUESTION = re.compile(r"(?:[？?]|哪些|如何|是否|为什么|什么|哪种|请判断|待确认)")
PLACEHOLDER = re.compile(r"(?:\[\[EVIDENCE_REQUIRED[^\]]*\]\]|\{\{[^}]+\}\}|\b(?:EVIDENCE_NEEDED|TODO|TBD|REPLACE|XXX|XXXX|PENDING)\b)", re.I)
INTERPRETATION_LEVELS = {"descriptive", "association", "prediction", "candidate", "mechanistic_hint"}
RESULT_NAME = re.compile(r"^[0-9]{2,}[._-][A-Za-z0-9][A-Za-z0-9._-]*\.[A-Za-z0-9]+$")
OVERCLAIM_TERMS = ("证明", "验证", "因果", "治疗", "疗效", "临床价值", "无混杂", "稳定结合", "安全性")
NEGATION = ("不代表", "不能", "无法", "尚不能", "未证明", "不支持", "未能")
MARKETING = re.compile(r"(?:扫码|公司介绍|服务领域|风险比看不懂|小果带你|联系我们)")
CORRUPTION = re.compile(r"\uFFFD")
REPEATED_WORD = re.compile(r"(?:结果显示|候选|表达|分析|数值越大表示){2,}")
TOP_FIELDS = {"schema_version", "module", "quality_profile", "result_layout", "title", "audience", "references", "versions", "evidence_targets", "analysis_points"}
POINT_FIELDS = {"id", "title", "scope", "qc", "inputs", "method", "parameters", "statistical_unit", "comparison", "results", "outputs", "figure_table_refs", "interpretation_level", "interpretation", "next_step", "limitations", "status"}
STATUSES = {"complete", "valid_no_findings", "evidence_missing", "blocked"}
SEMANTIC_ALIASES = {
    "summary": ("summary", "abstract", "摘要"),
    "scope": ("scope", "boundary", "data", "范围", "对象", "目的"),
    "method": ("method", "methods", "material", "材料", "方法"),
    "qc": ("qc", "quality", "质控", "质量"),
    "results": ("result", "results", "finding", "分析结果", "结果", "发现"),
    "interpretation": ("interpretation", "conclusion", "解读", "结论", "意义"),
    "limitations": ("limitation", "boundary", "局限", "限制", "待验证"),
    "outputs": ("output", "file", "artifact", "输出", "文件"),
    "references": ("reference", "citation", "source", "参考", "文献", "来源"),
    "versions": ("version", "software", "resource", "版本", "软件", "资源"),
    "figures": ("figure", "plot", "图", "绘图"),
    "tables": ("table", "表", "结果表"),
}


def section_semantics(section: dict) -> set[str]:
    explicit = section.get("semantic")
    if isinstance(explicit, str):
        explicit = [explicit]
    if isinstance(explicit, list) and explicit:
        return {str(item) for item in explicit if str(item) in SEMANTIC_ALIASES}
    text = f"{section.get('id', '')} {section.get('title', '')}".lower()
    return {name for name, aliases in SEMANTIC_ALIASES.items() if any(alias.lower() in text for alias in aliases)}


def normalise_relative(value: object) -> str | None:
    """Return a portable relative path, or None for an unsafe path."""
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip().replace("\\", "/")
    path = PurePosixPath(raw)
    if path.is_absolute() or re.match(r"^[A-Za-z]:/", raw) or any(part in {"", ".", ".."} for part in path.parts):
        return None
    return "/".join(path.parts)


def resolve_under(root: Path, relative: str) -> Path | None:
    """Resolve a published path without allowing symlink or .. escape."""
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def make_diagnostics(errors: list[str], warnings: list[str], subject: str) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for message in errors:
        if "declarative" in message or "question" in message:
            code = "language/non-declarative"
        elif "overclaim" in message:
            code = "interpretation/overclaim"
        elif "evidence" in message or "source" in message:
            code = "evidence/missing-or-unbound"
        elif "file" in message or "path" in message:
            code = "artifact/path"
        else:
            code = "report/invalid"
        fixes = ["edit the named plan, evidence field, or report text and validate again"]
        if code == "language/non-declarative":
            fixes.insert(0, "把内部问题改成陈述式主题，例如“GRN 候选 TF–target 关系”")
        entries.append({"code": code, "severity": "error", "message": message, "subject": {"path": subject}, "evidence": {}, "supportedFixes": fixes})
    for message in warnings:
        code = "evidence/needed" if "draft" in message.lower() or "evidence" in message.lower() or "marker" in message.lower() else "review/manual-check"
        entries.append({"code": code, "severity": "warning", "message": message, "subject": {"path": subject}, "evidence": {}, "supportedFixes": ["record the missing fact or run receipt, then validate again"]})
    return entries


def positive_overclaim(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    for term in OVERCLAIM_TERMS:
        start = 0
        while True:
            index = value.find(term, start)
            if index < 0:
                break
            context = value[max(0, index - 8):index]
            suffix = value[index + len(term):index + len(term) + 3]
            if term == "验证" and suffix.startswith(("集", "数据", "结果")):
                start = index + len(term)
                continue
            if not any(token in context for token in NEGATION):
                return term
            start = index + len(term)
    return None


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_pack(pack: object, root: Path | None = None, require_files: bool = False) -> list[str]:
    errors: list[str] = []
    if not isinstance(pack, dict):
        return ["evidence pack must be an object"]
    errors.extend(f"pack unknown top-level field: {key}" for key in sorted(set(pack) - TOP_FIELDS))
    for key in ("schema_version", "module", "quality_profile", "evidence_targets", "analysis_points"):
        if key not in pack:
            errors.append(f"pack missing {key}")
    if pack.get("schema_version") != "0.1.0":
        errors.append("pack schema_version must be 0.1.0")
    if pack.get("quality_profile") not in {"draft", "release"}:
        errors.append("pack quality_profile must be draft or release")
    if pack.get("result_layout") not in {"flat", "module_contract"}:
        errors.append("pack result_layout must be flat or module_contract")
    for field in ("title", "audience"):
        if field in pack and pack[field] is not None and not isinstance(pack[field], str):
            errors.append(f"pack {field} must be a string")
    for field in ("references", "versions"):
        if field in pack and not isinstance(pack[field], list):
            errors.append(f"pack {field} must be an array")
        elif isinstance(pack.get(field), list):
            for index, source in enumerate(pack[field]):
                if not isinstance(source, dict) or not all(isinstance(source.get(key), str) and source[key].strip() for key in ("name", "version")):
                    errors.append(f"pack {field}[{index}] needs name and version")
    for field in ("title",):
        value = pack.get(field)
        if isinstance(value, str) and QUESTION.search(value):
            errors.append(f"pack {field} must be declarative visible text")
    targets = pack.get("evidence_targets", [])
    target_ids: set[str] = set()
    for index, target in enumerate(targets if isinstance(targets, list) else []):
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
        if isinstance(target.get("title"), str) and QUESTION.search(target["title"]):
            errors.append(f"{label}.title must be declarative visible text")
        if "analysis_point_ids" in target and (
            not isinstance(target["analysis_point_ids"], list)
            or any(not isinstance(item, str) or not item.strip() for item in target["analysis_point_ids"])
        ):
            errors.append(f"{label}.analysis_point_ids must be a string array")
    points = pack.get("analysis_points")
    if not isinstance(points, list) or not points:
        return errors + ["pack analysis_points must be non-empty"]
    ids: set[str] = set()
    figure_ids: set[str] = set()
    output_ids: set[str] = set()
    for index, point in enumerate(points):
        label = f"analysis_points[{index}]"
        if not isinstance(point, dict):
            errors.append(f"{label} must be an object")
            continue
        errors.extend(f"{label} unknown field: {key}" for key in sorted(set(point) - POINT_FIELDS))
        for key in ("id", "title", "scope", "inputs", "method", "parameters", "results", "outputs", "figure_table_refs", "limitations", "status"):
            if key not in point:
                errors.append(f"{label} missing {key}")
        point_id = point.get("id")
        if not isinstance(point_id, str) or not point_id.strip():
            errors.append(f"{label}.id must be non-empty")
        elif point_id in ids:
            errors.append(f"duplicate analysis point: {point_id}")
        else:
            ids.add(point_id)
        for field in ("title", "scope"):
            if not isinstance(point.get(field), str) or not point[field].strip():
                errors.append(f"{label}.{field} must be a non-empty string")
        if isinstance(point.get("title"), str) and QUESTION.search(point["title"]):
            errors.append(f"{label}.title must be declarative visible text")
        for field in ("scope", "qc", "interpretation", "next_step"):
            if isinstance(point.get(field), str) and QUESTION.search(point[field]):
                errors.append(f"{label}.{field} must be declarative visible text")
        for field in ("qc", "statistical_unit", "interpretation", "next_step"):
            if field in point and point[field] not in (None, "") and (not isinstance(point[field], str) or not point[field].strip()):
                errors.append(f"{label}.{field} must be a non-empty string when declared")
        overclaim = positive_overclaim(point.get("interpretation"))
        if overclaim:
            errors.append(f"{label}.interpretation overclaim: unbounded claim term {overclaim}")
        if point.get("status") not in STATUSES:
            errors.append(f"{label}.status is invalid")
        if point.get("interpretation_level") is not None and point.get("interpretation_level") not in INTERPRETATION_LEVELS:
            errors.append(f"{label}.interpretation_level is invalid")
        if not isinstance(point.get("limitations"), list) or any(not isinstance(item, str) or not item.strip() for item in point.get("limitations", [])):
            errors.append(f"{label}.limitations must be a string array")
        method = point.get("method")
        if not isinstance(method, dict):
            errors.append(f"{label}.method must be an object")
        else:
            for field in ("name", "version"):
                if not isinstance(method.get(field), str) or not method[field].strip():
                    errors.append(f"{label}.method.{field} must be a non-empty string")
        if not isinstance(point.get("parameters"), dict):
            errors.append(f"{label}.parameters must be an object")
        for field in ("inputs", "results", "outputs", "figure_table_refs"):
            if not isinstance(point.get(field), list):
                errors.append(f"{label}.{field} must be an array")
        comparison = point.get("comparison")
        if comparison is not None:
            if not isinstance(comparison, dict):
                errors.append(f"{label}.comparison must be an object")
            elif not all(isinstance(comparison.get(k), str) and comparison[k].strip() for k in ("target", "reference", "direction")):
                errors.append(f"{label}.comparison must state target/reference/direction")
        for input_index, input_item in enumerate(point.get("inputs", []) if isinstance(point.get("inputs"), list) else []):
            if not isinstance(input_item, dict):
                errors.append(f"{label}.inputs[{input_index}] must be an object")
                continue
            if not all(isinstance(input_item.get(key), str) and input_item[key].strip() for key in ("id", "path", "identity")):
                errors.append(f"{label}.inputs[{input_index}] needs a path")
                continue
            if normalise_relative(input_item["path"]) is None:
                errors.append(f"{label}.inputs[{input_index}] path must be relative")
            elif root is not None:
                relative = normalise_relative(input_item["path"])
                resolved = resolve_under(root, relative) if relative else None
                if resolved is None:
                    errors.append(f"{label}.inputs[{input_index}] path escapes root: {input_item['path']}")
                elif require_files and not resolved.is_file():
                    errors.append(f"{label}.inputs[{input_index}] file does not exist: {input_item['path']}")
        for result_index, result in enumerate(point.get("results", []) if isinstance(point.get("results"), list) else []):
            if not isinstance(result, dict):
                errors.append(f"{label}.results[{result_index}] must be an object")
                continue
            if not all(isinstance(result.get(key), str) and result[key].strip() for key in ("name", "unit", "source")):
                errors.append(f"{label}.results[{result_index}] needs name/unit/source")
                continue
            if normalise_relative(result["source"]) is None:
                errors.append(f"{label}.results[{result_index}] source must be relative")
            elif root is not None:
                relative = normalise_relative(result["source"])
                resolved = resolve_under(root, relative) if relative else None
                if resolved is None:
                    errors.append(f"{label}.results[{result_index}] source escapes root: {result['source']}")
                elif require_files and not resolved.is_file():
                    errors.append(f"{label}.results[{result_index}] source does not exist: {result['source']}")
        for output_index, output in enumerate(point.get("outputs", []) if isinstance(point.get("outputs"), list) else []):
            if not isinstance(output, dict):
                errors.append(f"{label}.outputs[{output_index}] must be an object")
                continue
            if not all(isinstance(output.get(key), str) and output[key].strip() for key in ("id", "path", "kind")):
                errors.append(f"{label}.outputs[{output_index}] needs id/path/kind")
                continue
            if type(output.get("published")) is not bool:
                errors.append(f"{label}.outputs[{output_index}].published must be boolean")
            if not isinstance(output.get("purpose"), str) or not output["purpose"].strip():
                errors.append(f"{label}.outputs[{output_index}].purpose must be a non-empty string")
            consumers = output.get("consumers")
            if not isinstance(consumers, list) or not consumers or any(
                not isinstance(consumer, str) or not consumer.strip() for consumer in consumers
            ):
                errors.append(f"{label}.outputs[{output_index}].consumers must be a non-empty string array")
            if output["id"] in output_ids:
                errors.append(f"duplicate output id: {output['id']}")
            else:
                output_ids.add(output["id"])
            if normalise_relative(output["path"]) is None:
                errors.append(f"{label}.outputs[{output_index}] path must be relative")
            elif root is not None:
                relative = normalise_relative(output["path"])
                resolved = resolve_under(root, relative) if relative else None
                if resolved is None:
                    errors.append(f"{label}.outputs[{output_index}] path escapes root: {output['path']}")
                elif require_files and not resolved.is_file():
                    errors.append(f"{label}.outputs[{output_index}] file does not exist: {output['path']}")
        for ref_index, reference in enumerate(point.get("figure_table_refs", []) if isinstance(point.get("figure_table_refs"), list) else []):
            if not isinstance(reference, dict):
                errors.append(f"{label}.figure_table_refs[{ref_index}] must be an object")
                continue
            if not all(isinstance(reference.get(key), str) and reference[key].strip() for key in ("id", "path")):
                errors.append(f"{label}.figure_table_refs[{ref_index}] needs id/path")
                continue
            if reference.get("id") in figure_ids:
                errors.append(f"duplicate figure/table id: {reference['id']}")
            else:
                figure_ids.add(reference["id"])
            if reference.get("kind") not in {"figure", "table"}:
                errors.append(f"{label}.figure_table_refs[{ref_index}] kind must be figure or table")
            if normalise_relative(reference["path"]) is None:
                errors.append(f"{label}.figure_table_refs[{ref_index}] path must be relative")
            elif root is not None:
                relative = normalise_relative(reference["path"])
                resolved = resolve_under(root, relative) if relative else None
                if resolved is None:
                    errors.append(f"{label}.figure_table_refs[{ref_index}] path escapes root: {reference['path']}")
                elif require_files and not resolved.is_file():
                    errors.append(f"{label}.figure_table_refs[{ref_index}] file does not exist: {reference['path']}")
    if isinstance(targets, list) and isinstance(points, list) and points:
        covered: set[str] = set()
        for index, target in enumerate(targets):
            if not isinstance(target, dict):
                continue
            mapped = target.get("analysis_point_ids")
            if mapped is None:
                if require_files:
                    errors.append(f"evidence_targets[{index}] must map analysis_point_ids in final report")
                continue
            for point_id in mapped if isinstance(mapped, list) else []:
                if point_id not in ids:
                    errors.append(f"evidence_targets[{index}] references unknown analysis point: {point_id}")
                covered.add(point_id)
        if require_files:
            missing = sorted(ids - covered)
            if missing:
                errors.append(f"final report targets do not cover analysis points: {missing}")
    return errors


def validate_plan(plan: object, point_ids: set[str]) -> list[str]:
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ["report plan must be an object"]
    allowed = {"schema_version", "module", "mode", "title", "audience", "quality_profile", "effort_profile", "max_repair_rounds", "result_layout", "evidence_pack", "evidence_targets", "sections", "output_policy"}
    for key in sorted(set(plan) - allowed):
        errors.append(f"plan unknown top-level field: {key}")
    if plan.get("schema_version") != "0.1.0":
        errors.append("plan schema_version must be 0.1.0")
    if plan.get("quality_profile") not in {"draft", "release"}:
        errors.append("plan quality_profile must be draft or release")
    if plan.get("mode", "module") not in {"module", "one_off"}:
        errors.append("plan mode must be module or one_off")
    if plan.get("effort_profile") not in {"mechanical", "scientific_review"}:
        errors.append("plan effort_profile must be mechanical or scientific_review")
    if not isinstance(plan.get("module"), str) or not plan["module"].strip():
        errors.append("plan module must be a non-empty string")
    if plan.get("quality_profile") == "release" and (not isinstance(plan.get("audience"), str) or not plan["audience"].strip()):
        errors.append("release plan audience must be a non-empty string")
    for field in ("title",):
        if isinstance(plan.get(field), str) and QUESTION.search(plan[field]):
            errors.append(f"plan {field} must be declarative visible text")
    if type(plan.get("max_repair_rounds")) is not int or not 0 <= plan["max_repair_rounds"] <= 2:
        errors.append("plan max_repair_rounds must be an integer from 0 to 2")
    if plan.get("result_layout") not in {"flat", "module_contract"}:
        errors.append("plan result_layout must be flat or module_contract")
    evidence_pack = plan.get("evidence_pack")
    if not isinstance(evidence_pack, str) or not evidence_pack.strip():
        errors.append("plan evidence_pack must be a non-empty string")
    elif Path(evidence_pack).is_absolute():
        errors.append("plan evidence_pack must be relative")
    output_policy = plan.get("output_policy")
    if not isinstance(output_policy, dict) or not isinstance(output_policy.get("report_file"), str) or not output_policy["report_file"].strip():
        errors.append("plan output_policy.report_file must be a non-empty string")
    elif normalise_relative(output_policy["report_file"]) is None:
        errors.append("plan output_policy.report_file must be a safe relative path")
    elif plan.get("mode", "module") == "module" and not normalise_relative(output_policy["report_file"]).startswith("report/"):
        errors.append("module report_file must be under report/")
    sections = plan.get("sections")
    if not isinstance(sections, list):
        return errors + ["plan sections must be an array"]
    section_ids = [item.get("id") for item in sections if isinstance(item, dict)]
    if len(section_ids) != len(set(section_ids)):
        errors.append("plan section ids must be unique")
    sections_by_semantic: dict[str, list[dict]] = {}
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            errors.append(f"sections[{index}] must be an object")
            continue
        if not isinstance(section.get("id"), str) or not section["id"].strip():
            errors.append(f"sections[{index}].id must be a non-empty string")
        if type(section.get("required")) is not bool:
            errors.append(f"sections[{index}].required must be boolean")
        if not isinstance(section.get("analysis_point_ids"), list):
            errors.append(f"sections[{index}].analysis_point_ids must be an array")
        explicit = section.get("semantic")
        explicit_values = [explicit] if isinstance(explicit, str) else explicit if isinstance(explicit, list) else []
        if explicit_values and any(str(item) not in SEMANTIC_ALIASES for item in explicit_values):
            errors.append(f"sections[{index}].semantic contains an unknown semantic")
        sems = section_semantics(section)
        for semantic in sems:
            sections_by_semantic.setdefault(semantic, []).append(section)
        if isinstance(section.get("title"), str) and QUESTION.search(section["title"]):
            errors.append(f"sections[{index}].title must be declarative visible text")
        for point_id in section.get("analysis_point_ids", []) if isinstance(section.get("analysis_point_ids"), list) else []:
            if point_id not in point_ids:
                errors.append(f"section {section.get('id')} references unknown point {point_id}")
    required_semantics = {"scope", "method", "results", "interpretation", "limitations", "outputs"}
    missing_semantics = sorted(required_semantics - set(sections_by_semantic))
    if missing_semantics:
        errors.append(f"plan missing required semantic sections: {missing_semantics}")
    covered: dict[str, set[str]] = {name: set() for name in sections_by_semantic}
    for semantic, items in sections_by_semantic.items():
        for section in items:
            ids = section.get("analysis_point_ids", [])
            covered[semantic].update(ids if ids else (point_ids if semantic in {"scope", "summary"} else set()))
    for semantic in ("method", "results", "interpretation", "limitations"):
        missing_points = sorted(point_ids - covered.get(semantic, set()))
        if missing_points:
            errors.append(f"semantic section {semantic} does not cover analysis points: {missing_points}")
    if isinstance(plan.get("quality_profile"), str) and plan.get("quality_profile") == "release":
        for semantic in ("references", "versions"):
            if semantic not in sections_by_semantic:
                errors.append(f"release plan missing semantic section: {semantic}")
    plan_targets = plan.get("evidence_targets")
    if not isinstance(plan_targets, list):
        errors.append("plan evidence_targets must be an array")
    else:
        target_ids: set[str] = set()
        for index, target in enumerate(plan_targets):
            if not isinstance(target, dict) or not isinstance(target.get("id"), str) or not target["id"].strip() or not isinstance(target.get("title"), str) or not target["title"].strip():
                errors.append(f"plan evidence_targets[{index}] needs id/title")
                continue
            if target["id"] in target_ids:
                errors.append(f"plan evidence_targets has duplicate id: {target['id']}")
            target_ids.add(target["id"])
            if QUESTION.search(target["title"]):
                errors.append(f"plan evidence_targets[{index}].title must be declarative visible text")
    return errors


def validate_flat_result_paths(pack: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(pack, dict):
        return errors
    for point_index, point in enumerate(pack.get("analysis_points", [])):
        if not isinstance(point, dict):
            continue
        for field in ("outputs", "figure_table_refs"):
            for item_index, item in enumerate(point.get(field, [])):
                if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                    continue
                relative = normalise_relative(item["path"])
                path = PurePosixPath(relative) if relative else PurePosixPath(".")
                if path.parts[:1] == ("result",) and (len(path.parts) != 2 or not RESULT_NAME.fullmatch(path.name)):
                    errors.append(f"analysis_points[{point_index}].{field}[{item_index}] must be a flat numbered result path: {item['path']}")
    return errors


def scan_markdown(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [f"cannot read markdown: {exc}"]
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("<!--"):
            continue
        if "http://" in stripped or "https://" in stripped:
            continue
        if QUESTION.search(stripped):
            errors.append(f"line {number}: declarative visible text required")
        if PLACEHOLDER.search(stripped):
            errors.append(f"line {number}: unresolved evidence/template marker")
        if MARKETING.search(stripped):
            errors.append(f"line {number}: marketing text is outside the scientific report")
        if CORRUPTION.search(stripped):
            errors.append(f"line {number}: encoding corruption marker found")
        if REPEATED_WORD.search(stripped):
            errors.append(f"line {number}: repeated phrase needs editorial repair")
    return errors


def has_draft_state(pack: object, plan: object) -> bool:
    """A draft is never a delivery PASS, even when its shape validates."""
    values = (pack, plan)
    for value in values:
        if isinstance(value, dict) and value.get("quality_profile") != "release":
            return True
    if isinstance(pack, dict):
        points = pack.get("analysis_points", [])
        if any(isinstance(point, dict) and point.get("status") not in {"complete", "valid_no_findings"} for point in points):
            return True
        if PLACEHOLDER.search(json.dumps(pack, ensure_ascii=False)):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--evidence-pack", required=True, type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--root", type=Path, help="root used to verify published files")
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    errors: list[str] = []
    warnings: list[str] = []
    try:
        pack = load(args.evidence_pack)
        plan = load(args.plan)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"cannot read input: {exc}")
        pack = {}
        plan = {}
    errors.extend(validate_pack(pack, args.root.resolve() if args.root else None, require_files=args.final))
    if args.final and args.root is None:
        errors.append("final validation requires --root for published artifact checks")
    elif args.root is not None and not args.root.is_dir():
        errors.append(f"artifact root does not exist or is not a directory: {args.root}")
    point_ids = {item.get("id") for item in pack.get("analysis_points", []) if isinstance(item, dict)} if isinstance(pack, dict) else set()
    errors.extend(validate_plan(plan, point_ids))
    if isinstance(plan, dict) and plan.get("result_layout") == "flat":
        errors.extend(validate_flat_result_paths(pack))
    if isinstance(pack, dict) and isinstance(plan, dict):
        if pack.get("quality_profile") != plan.get("quality_profile"):
            errors.append("plan and evidence pack quality_profile must match")
        if pack.get("result_layout") != plan.get("result_layout"):
            errors.append("plan and evidence pack result_layout must match")
        pack_ref = plan.get("evidence_pack")
        if isinstance(pack_ref, str) and pack_ref.strip():
            expected_pack = (args.plan.parent / pack_ref.replace("\\", "/")).resolve()
            if expected_pack != args.evidence_pack.resolve():
                errors.append("plan evidence_pack does not match --evidence-pack")
        pack_target_ids = {
            item.get("id") for item in pack.get("evidence_targets", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        plan_target_ids = {
            item.get("id") for item in plan.get("evidence_targets", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        if pack_target_ids != plan_target_ids:
            errors.append("plan and evidence pack evidence_targets must match")
    if args.markdown:
        markdown_errors = scan_markdown(args.markdown)
        if not args.final:
            # A draft marker is useful evidence of unfinished work, not a claim that
            # the generic scaffold is a broken final report.
            marker_errors = [item for item in markdown_errors if "unresolved evidence/template marker" in item]
            warnings.extend(marker_errors)
            markdown_errors = [item for item in markdown_errors if item not in marker_errors]
        errors.extend(markdown_errors)
    if args.final and isinstance(pack, dict):
        for index, point in enumerate(pack.get("analysis_points", [])):
            if isinstance(point, dict) and point.get("status") not in {"complete", "valid_no_findings"}:
                errors.append(f"final requires evidence-complete status at analysis_points[{index}]")
            if isinstance(point, dict) and not point.get("limitations"):
                errors.append(f"final requires explicit limitations at analysis_points[{index}]")
            if isinstance(point, dict) and (not isinstance(point.get("next_step"), str) or not point["next_step"].strip()):
                errors.append(f"final requires next_step at analysis_points[{index}]")
            if isinstance(point, dict):
                for ref_index, reference in enumerate(point.get("figure_table_refs", [])):
                    if isinstance(reference, dict) and reference.get("kind") == "figure":
                        caption = reference.get("caption")
                        if not isinstance(caption, str) or not caption.strip():
                            errors.append(f"final requires caption for analysis_points[{index}].figure_table_refs[{ref_index}]")
        if not pack.get("references"):
            errors.append("final requires used references")
        if not pack.get("versions"):
            errors.append("final requires software and resource versions")
        if isinstance(plan, dict) and plan.get("quality_profile") != "release":
            errors.append("final requires plan quality_profile=release")
        if isinstance(pack, dict) and pack.get("quality_profile") != "release":
            errors.append("final requires evidence pack quality_profile=release")
        if PLACEHOLDER.search(json.dumps(pack, ensure_ascii=False)):
            errors.append("final validation rejects draft markers")
    if isinstance(plan, dict):
        report_file = plan.get("output_policy", {}).get("report_file") if isinstance(plan.get("output_policy"), dict) else None
        report_file = normalise_relative(report_file)
        for point in pack.get("analysis_points", []) if isinstance(pack, dict) else []:
            for output in point.get("outputs", []) if isinstance(point, dict) else []:
                output_path = normalise_relative(output.get("path")) if isinstance(output, dict) else None
                if report_file and output_path == report_file:
                    errors.append("report itself must not be listed as a business output")
    subject = str(args.markdown or args.plan)
    if errors:
        status = "BLOCKED"
    elif not args.final or has_draft_state(pack, plan):
        status = "EVIDENCE_NEEDED"
        warnings.append("draft/review validation is not a delivery PASS; complete release evidence and rerun with --final")
    elif warnings:
        status = "EVIDENCE_NEEDED"
    else:
        status = "PASS"
    result = {"status": status, "errors": errors, "warnings": warnings, "diagnostics": make_diagnostics(errors, warnings, subject), "summary": {"errors": len(errors), "warnings": len(warnings)}}
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"REPORT_CONTRACT_{result['status']} errors={len(errors)} warnings={len(warnings)}")
        for item in errors:
            print(item, file=sys.stderr)
        for item in warnings:
            print(item)
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
