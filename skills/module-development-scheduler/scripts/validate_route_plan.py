#!/usr/bin/env python3
"""校验 route_module_task.py 生成的路由计划。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


TASK_TYPES = {"new", "migrate", "optimize", "substantial_change", "review"}
WORK_KINDS = {"auto", "code", "report", "both", "review"}
PHASES = {"scope", "build", "draft", "finish"}
PLAN_PHASE = {"scope": "start", "build": "build", "draft": "draft", "finish": "finish"}
ADAPTERS = {"module-development-scheduler", "bio-code-standard", "bio-report-writing"}
CORE_REQUIRED = {
    "schema_version",
    "module",
    "task_type",
    "work_kind",
    "execution_scope",
    "quality_profile",
    "effort_profile",
    "max_repair_rounds",
    "route",
    "phase",
    "loaded_skills",
    "required_checks",
    "blocked_reasons",
    "next_owner",
}
OPTIONAL_FIELDS = {
    "report_context",
    "max_checkpoint_rounds",
    "max_regression_rounds",
    "repair_round",
    "checkpoint_round",
    "regression_round",
    "rounds",
    "plan_phase",
    "entry_skill",
    "owner",
    "adapter_skills",
    "execution_order",
    "coder_order",
    "finish_policy",
    "development_plan",
}
ALLOWED_FIELDS = CORE_REQUIRED | OPTIONAL_FIELDS


def _string_array(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) and item.strip() for item in value
    )


def _non_negative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def validate(value: Any, subject: str) -> list[str]:
    if not isinstance(value, dict):
        return ["plan root must be an object"]

    errors = [f"unknown top-level field: {key}" for key in sorted(set(value) - ALLOWED_FIELDS)]
    errors.extend(f"missing {key}" for key in sorted(CORE_REQUIRED - set(value)))
    if errors and not CORE_REQUIRED.issubset(value):
        return errors

    if value.get("schema_version") != "0.1.0":
        errors.append("schema_version must be 0.1.0")
    if not isinstance(value.get("module"), str) or not value["module"].strip():
        errors.append("module must be a non-empty string")
    if value.get("task_type") not in TASK_TYPES:
        errors.append("invalid task_type")
    if value.get("work_kind") not in WORK_KINDS:
        errors.append("invalid work_kind")
    execution_scope = value.get("execution_scope")
    if isinstance(execution_scope, str):
        execution_scope = execution_scope.strip().lower().replace("_", "-")
        execution_scope = {"report": "report-only", "report-only": "report-only"}.get(execution_scope, execution_scope)
    if execution_scope not in {"report-only", "plot", "full"}:
        errors.append("invalid execution_scope")
    report_context = value.get("report_context")
    if report_context is None:
        report_context = "module_reusable" if "bio-report-writing" in value.get("loaded_skills", []) else "none"
    if isinstance(report_context, str):
        report_context = report_context.strip().lower().replace("-", "_")
    if report_context not in {"none", "one_off", "module_reusable"}:
        errors.append("invalid report_context")
    if value.get("route") not in {"ask-matt", "fork", "goal", "BLOCKED"}:
        errors.append("invalid route")
    if value.get("phase") not in PHASES:
        errors.append("invalid phase")
    elif value.get("plan_phase", PLAN_PHASE[value["phase"]]) != PLAN_PHASE[value["phase"]]:
        errors.append("plan_phase does not match phase")
    if value.get("quality_profile") not in {"draft", "release"}:
        errors.append("invalid quality_profile")
    if value.get("effort_profile") not in {"mechanical", "scientific_review"}:
        errors.append("invalid effort_profile")

    round_fields = (
        "max_repair_rounds",
        "max_checkpoint_rounds",
        "max_regression_rounds",
        "repair_round",
        "checkpoint_round",
        "regression_round",
    )
    has_round_metadata = any(
        field in value for field in round_fields if field != "max_repair_rounds"
    ) or "rounds" in value
    for field in round_fields:
        if field in value and not _non_negative_int(value.get(field)):
            errors.append(f"invalid {field}")
    if "max_repair_rounds" in value and _non_negative_int(value.get("max_repair_rounds")) and value["max_repair_rounds"] > 2:
        errors.append("max_repair_rounds must not exceed 2")

    rounds = value.get("rounds")
    if has_round_metadata and (not isinstance(rounds, dict) or set(rounds) != {"repair", "checkpoint", "regression"}):
        errors.append("rounds must contain repair/checkpoint/regression")
    elif isinstance(rounds, dict):
        for kind, current_field, max_field in (
            ("repair", "repair_round", "max_repair_rounds"),
            ("checkpoint", "checkpoint_round", "max_checkpoint_rounds"),
            ("regression", "regression_round", "max_regression_rounds"),
        ):
            item = rounds[kind]
            expected_fields = {"current", "max", "unbounded"} if kind == "regression" else {"current", "max"}
            if not isinstance(item, dict) or set(item) != expected_fields:
                errors.append(f"rounds.{kind} has invalid fields")
                continue
            if item.get("current") != value.get(current_field) or item.get("max") != value.get(max_field):
                errors.append(f"rounds.{kind} does not match top-level counters")
            if kind == "regression" and item.get("unbounded") != (value.get(max_field) == 0):
                errors.append("rounds.regression.unbounded does not match max_regression_rounds")
    if has_round_metadata and all(_non_negative_int(value.get(field)) for field in round_fields):
        if value["repair_round"] > value["max_repair_rounds"]:
            errors.append("repair_round exceeds max_repair_rounds")
        if value["checkpoint_round"] > value["max_checkpoint_rounds"]:
            errors.append("checkpoint_round exceeds max_checkpoint_rounds")
        if value["max_regression_rounds"] and value["regression_round"] > value["max_regression_rounds"]:
            errors.append("regression_round exceeds max_regression_rounds")

    for field in ("loaded_skills", "required_checks", "blocked_reasons"):
        if not _string_array(value.get(field)):
            errors.append(f"{field} must be a string array")
        elif len(value[field]) != len(set(value[field])):
            errors.append(f"{field} must not contain duplicates")

    adapters = value.get("adapter_skills")
    loaded = value.get("loaded_skills")
    order = value.get("execution_order")
    coder_order = value.get("coder_order")
    checks = value.get("required_checks")
    if adapters is None and isinstance(loaded, list):
        # 旧计划把组合入口放在 loaded_skills 中；这里只把它视为上下文，不视为叶子 adapter。
        adapters = [item for item in loaded if item != "develop-module"]
    for field in ("adapter_skills", "execution_order", "coder_order"):
        if field in value and not _string_array(value.get(field)):
            errors.append(f"{field} must be a string array")
        elif field in value and len(value[field]) != len(set(value[field])):
            errors.append(f"{field} must not contain duplicates")
    if isinstance(adapters, list):
        unknown = sorted(set(adapters) - ADAPTERS)
        if unknown:
            errors.append(f"unknown adapter_skills: {unknown}")
        if not adapters or adapters[0] != "module-development-scheduler":
            errors.append("adapter_skills must start with module-development-scheduler")
        if value.get("entry_skill") in adapters or value.get("owner") in adapters:
            errors.append("entry skill/lifecycle owner must not be an adapter")
    if "entry_skill" in value and value.get("entry_skill") != "develop-module":
        errors.append("entry_skill must be develop-module")
    if "adapter_skills" in value and isinstance(loaded, list) and loaded != adapters:
        errors.append("loaded_skills must equal adapter_skills")

    code = isinstance(adapters, list) and "bio-code-standard" in adapters
    report = isinstance(adapters, list) and "bio-report-writing" in adapters
    if execution_scope == "report-only" and code:
        errors.append("report-only scope cannot load bio-code-standard")
    if execution_scope == "report-only" and not report:
        errors.append("report-only scope requires bio-report-writing")
    if execution_scope == "plot" and not code:
        errors.append("plot scope requires bio-code-standard")
    if execution_scope == "full" and not code and value.get("task_type") != "review":
        errors.append("full scope requires bio-code-standard")
    if report_context == "none" and report:
        errors.append("report adapter requires a report_context")
    if report_context in {"one_off", "module_reusable"} and not report:
        errors.append("report_context requires bio-report-writing")
    coder = "plot_coder" if execution_scope == "plot" else "analysis_coder"
    expected_order = (["source_review", coder] if code else []) + (["report_coder"] if report else [])
    if "execution_order" in value and isinstance(order, list) and order != expected_order:
        errors.append("execution_order must match the declared execution_scope and coder order")
    expected_coders = [item for item in expected_order if item.endswith("_coder")]
    if "coder_order" in value and isinstance(coder_order, list) and coder_order != expected_coders:
        errors.append("coder_order does not match execution_order")
    if code and isinstance(checks, list):
        required_code_checks = ["source_review", "code_contract"]
        required_code_checks.append(
            "figure_manifest" if execution_scope == "plot" else "analysis_evidence_pack"
        )
        for check in required_code_checks:
            if check not in checks:
                errors.append(f"code work missing required check: {check}")
        if all(check in checks for check in ("source_review", "code_contract")) and checks.index("source_review") > checks.index("code_contract"):
            errors.append("source_review must precede code_contract")
        if execution_scope == "plot" and "analysis_evidence_pack" in checks:
            errors.append("plot scope must not schedule analysis_evidence_pack")
    elif execution_scope == "report-only" and isinstance(checks, list):
        forbidden = {"source_review", "code_contract", "analysis_evidence_pack"} & set(checks)
        if forbidden:
            errors.append(f"report-only scope must not schedule code checks: {sorted(forbidden)}")
    if report and isinstance(checks, list):
        for check in ("report_contract", "figure_manifest", "docx_structure"):
            if check not in checks:
                errors.append(f"report work missing required check: {check}")

    finish_policy = value.get("finish_policy")
    if finish_policy is not None and (not isinstance(finish_policy, dict) or set(finish_policy) != {"requires_review", "requires_full"} or any(type(item) is not bool for item in finish_policy.values())):
        errors.append("finish_policy must contain boolean requires_review/requires_full")
    elif isinstance(finish_policy, dict) and isinstance(checks, list):
        if execution_scope in {"report-only", "plot"} and finish_policy["requires_full"]:
            errors.append("report-only/plot scope cannot require final_full")
        for enabled, required in (
            (finish_policy["requires_review"], {"independent_test", "scientific_review"}),
            (finish_policy["requires_full"], {"final_full"}),
        ):
            present = required & set(checks)
            if value.get("phase") == "finish" and enabled and present != required:
                errors.append(f"finish_policy missing checks: {sorted(required - present)}")
            if (value.get("phase") != "finish" or not enabled) and present:
                errors.append(f"conditional finish checks are not applicable: {sorted(present)}")

    development_plan = value.get("development_plan")
    if development_plan is not None and (not isinstance(development_plan, dict) or set(development_plan) != {"path", "phase"}):
        errors.append("development_plan must contain path/phase")
    elif isinstance(development_plan, dict):
        if not isinstance(development_plan.get("path"), str) or not development_plan["path"].strip():
            errors.append("development_plan.path must be non-empty")
        if development_plan.get("phase") != value.get("plan_phase"):
            errors.append("development_plan.phase must equal plan_phase")

    owner = value.get("owner", value.get("next_owner"))
    if value.get("route") == "BLOCKED":
        if not value.get("blocked_reasons"):
            errors.append("BLOCKED route needs a reason")
        if owner != "user_decision" or value.get("next_owner") != "user_decision":
            errors.append("BLOCKED route owner must be user_decision")
    else:
        if owner != "matt-executor" or value.get("next_owner") != "matt-executor":
            errors.append("routable plan owner must be matt-executor")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    try:
        value = json.loads(args.plan.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ROUTE_PLAN_BLOCKED: {exc}", file=sys.stderr)
        return 2

    errors = validate(value, str(args.plan))
    diagnostics = [
        {
            "code": "route/invalid",
            "severity": "error",
            "message": error,
            "subject": {"path": str(args.plan)},
            "evidence": {},
            "supportedFixes": ["edit the route plan and run validation again"],
        }
        for error in errors
    ]
    result = {
        "status": "BLOCKED" if errors else "PASS",
        "diagnostics": diagnostics,
        "summary": {"errors": len(errors), "warnings": 0},
    }
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ROUTE_PLAN_{'BLOCKED' if errors else 'PASS'} errors={len(errors)}")
        print(json.dumps(result, ensure_ascii=False))
        for error in errors:
            print(error, file=sys.stderr)
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
