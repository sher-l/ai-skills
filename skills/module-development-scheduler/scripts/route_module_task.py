#!/usr/bin/env python3
"""Produce a deterministic internal route plan for develop-module.

The scheduler is deliberately boring: it classifies the work, names the
leaf adapters and returns one Matt owner.  It never runs an adapter or makes a
scientific decision.  Keep the data model explicit so a lifecycle owner is not
mistaken for a domain adapter by a downstream consumer.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
from typing import Any


CODE_HINTS = {".r", ".rmd", ".py", ".sh", ".yaml", ".yml", ".json", ".ini", ".toml"}
REPORT_HINTS = {"report", "figure", "caption", "docx", "report_stage"}
TASK_TYPES = {"new", "migrate", "optimize", "substantial_change", "review"}
PHASES = {"scope", "build", "draft", "finish"}
WORK_KINDS = {"auto", "code", "report", "both", "review"}
REPORT_CONTEXTS = {"none", "one_off", "module_reusable"}
ENTRY_SKILL = "develop-module"
SCHEDULER_SKILL = "module-development-scheduler"
CODE_SKILL = "bio-code-standard"
REPORT_SKILL = "bio-report-writing"
OWNER = "matt-executor"
PLAN_PHASE = {"scope": "start", "build": "build", "draft": "draft", "finish": "finish"}


def _normalise_report_context(value: str | None, report: bool) -> str:
    """Accept the human spelling while keeping one canonical JSON value."""
    if value is None or value in {"", "auto"}:
        return "module_reusable" if report else "none"
    normalised = value.strip().lower().replace("-", "_")
    return normalised


def _as_bool(value: bool | None, default: bool) -> bool:
    return default if value is None else bool(value)


def _bounded_rounds(
    repair_round: int,
    checkpoint_round: int,
    regression_round: int,
    max_repair_rounds: int,
    max_checkpoint_rounds: int,
    max_regression_rounds: int,
) -> list[str]:
    errors: list[str] = []
    for name, current in (
        ("repair_round", repair_round),
        ("checkpoint_round", checkpoint_round),
        ("regression_round", regression_round),
    ):
        if type(current) is not int or current < 0:
            errors.append(f"{name} must be a non-negative integer")
    for name, maximum in (
        ("max_repair_rounds", max_repair_rounds),
        ("max_checkpoint_rounds", max_checkpoint_rounds),
        ("max_regression_rounds", max_regression_rounds),
    ):
        if type(maximum) is not int or maximum < 0:
            errors.append(f"{name} must be a non-negative integer")
    if not errors:
        if repair_round > max_repair_rounds:
            errors.append("repair_round exceeds max_repair_rounds")
        if checkpoint_round > max_checkpoint_rounds:
            errors.append("checkpoint_round exceeds max_checkpoint_rounds")
        # A zero regression ceiling means no artificial cap; regression rounds
        # are evidence, not a second lifecycle.
        if max_regression_rounds and regression_round > max_regression_rounds:
            errors.append("regression_round exceeds max_regression_rounds")
    return errors


def infer(
    task_type: str,
    paths: list[str],
    has_report: bool,
    spec_ready: bool,
    single_session: bool,
    multi_session: bool,
    phase: str,
    quality_profile: str,
    effort_profile: str,
    work_kind: str,
    max_repair_rounds: int,
    report_context: str | None = None,
    has_full: bool | None = None,
    requires_review: bool | None = None,
    development_plan: str | None = None,
    repair_round: int = 0,
    checkpoint_round: int = 0,
    regression_round: int = 0,
    max_checkpoint_rounds: int = 1,
    max_regression_rounds: int = 0,
    module: str | None = None,
    full_required: bool | None = None,
    review_required: bool | None = None,
) -> dict[str, Any]:
    """Return one deterministic route plan.

    Positional arguments up to ``max_repair_rounds`` are retained for callers
    of the first scheduler draft.  New controls are keyword-friendly and do
    not alter the lifecycle owner.
    """
    paths = [path for path in paths if isinstance(path, str)]
    lowered = [path.lower() for path in paths]
    path_code = any(Path(path).suffix.lower() in CODE_HINTS for path in lowered)
    path_report = any(any(token.lower() in path for token in REPORT_HINTS) for path in lowered)
    inferred_report = bool(has_report or path_report)

    # New/migrate/optimize/change are code work by default.  An explicit report
    # kind remains authoritative; this is the bug fix for an empty ``new``
    # scope silently skipping the code adapter.
    code_default = task_type in {"new", "migrate", "optimize", "substantial_change"}
    code = work_kind in {"code", "both"} or (
        work_kind in {"auto", "review"} and (path_code or code_default)
    )
    report = work_kind in {"report", "both"} or (
        work_kind in {"auto", "review"} and inferred_report
    )
    if work_kind == "report":
        report = True
        code = False
    if work_kind == "code":
        report = False
    if work_kind == "both":
        code = report = True

    context = _normalise_report_context(report_context, report)
    blockers: list[str] = []
    if not task_type or task_type not in TASK_TYPES:
        blockers.append("task_type must be one of new/migrate/optimize/substantial_change/review")
    if not phase or phase not in PHASES:
        blockers.append("phase must be one of scope/build/draft/finish")
    if not paths and task_type in {"migrate", "optimize", "substantial_change", "review"}:
        blockers.append("changed paths or an explicit scope are required")
    if work_kind not in WORK_KINDS:
        blockers.append("work_kind must be auto, code, report, both, or review")
    if context not in REPORT_CONTEXTS:
        blockers.append("report_context must be none, one_off, or module_reusable")
    if context == "none" and report:
        blockers.append("report work requires report_context one_off or module_reusable")
    if context != "none" and not report:
        blockers.append("report_context is only valid for report work")
    if single_session and multi_session:
        blockers.append("single_session and multi_session cannot both be selected")
    if not isinstance(max_repair_rounds, int) or not 0 <= max_repair_rounds <= 2:
        blockers.append("max_repair_rounds must be an integer from 0 to 2")
    blockers.extend(
        _bounded_rounds(
            repair_round,
            checkpoint_round,
            regression_round,
            max_repair_rounds,
            max_checkpoint_rounds,
            max_regression_rounds,
        )
    )

    # A route is a handoff decision, not a second lifecycle.  A spec-less
    # request always returns to Matt planning, even if the caller says it is a
    # multi-session job.
    if single_session and spec_ready:
        route = "fork"
    elif multi_session and spec_ready:
        route = "goal"
    else:
        route = "ask-matt"

    # ``has_full`` and ``requires_review`` are capability declarations, not
    # guesses from file names.  Unknown capability means the corresponding
    # finish check is not scheduled; the caller must opt in explicitly.
    if full_required is not None:
        has_full = full_required
    if review_required is not None:
        requires_review = review_required
    full = _as_bool(has_full, False)
    review = _as_bool(
        requires_review,
        False,
    )
    if phase == "finish" and quality_profile != "release":
        blockers.append("finish phase requires quality_profile=release")

    adapters = [SCHEDULER_SKILL]
    if code:
        adapters.append(CODE_SKILL)
    if report:
        adapters.append(REPORT_SKILL)
    loaded = list(adapters)
    checks = ["module_identity"]
    execution_order: list[str] = []
    if phase == "scope":
        checks.append("scope_review")
    if code:
        # Source review is deliberately first; report work can only consume a
        # code evidence pack after this hook has completed.
        checks.extend(["source_review", "code_contract", "analysis_evidence_pack"])
        execution_order.extend(["source_review", "analysis_coder"])
    if report:
        checks.extend(["report_contract", "figure_manifest", "docx_structure"])
        execution_order.append("report_coder")
    if not code and not report:
        checks.append("module_contract")
    if phase in {"draft", "finish"}:
        checks.append("domain_adapter_aggregate")
    if phase == "finish":
        if review:
            checks.extend(["independent_test", "scientific_review"])
        if full:
            checks.append("final_full")
    if repair_round:
        checks.append("repair_round")
    if checkpoint_round:
        checks.append("checkpoint_round")
    if regression_round:
        checks.append("regression_round")

    plan_path = development_plan or (
        f"{module}/docs/development-plan.md" if module else "MODULE/docs/development-plan.md"
    )
    return {
        "schema_version": "0.1.0",
        "module": "",
        "task_type": task_type,
        "work_kind": work_kind,
        "report_context": context,
        "quality_profile": quality_profile,
        "effort_profile": effort_profile,
        "max_repair_rounds": max_repair_rounds,
        "max_checkpoint_rounds": max_checkpoint_rounds,
        "max_regression_rounds": max_regression_rounds,
        "repair_round": repair_round,
        "checkpoint_round": checkpoint_round,
        "regression_round": regression_round,
        "rounds": {
            "repair": {"current": repair_round, "max": max_repair_rounds},
            "checkpoint": {"current": checkpoint_round, "max": max_checkpoint_rounds},
            "regression": {
                "current": regression_round,
                "max": max_regression_rounds,
                "unbounded": max_regression_rounds == 0,
            },
        },
        "route": "BLOCKED" if blockers else route,
        "phase": phase,
        "plan_phase": PLAN_PHASE.get(phase, phase),
        "entry_skill": ENTRY_SKILL,
        "owner": OWNER if not blockers else "user_decision",
        "adapter_skills": adapters,
        "loaded_skills": loaded,
        "execution_order": execution_order,
        "coder_order": [item for item in execution_order if item.endswith("_coder")],
        "finish_policy": {
            "requires_review": review,
            "requires_full": full,
        },
        "development_plan": {"path": plan_path, "phase": PLAN_PHASE.get(phase, phase)},
        "required_checks": list(dict.fromkeys(checks)),
        "blocked_reasons": blockers,
        "next_owner": "user_decision" if blockers else OWNER,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", required=True)
    parser.add_argument("--task-type", required=True)
    parser.add_argument("--changed-path", action="append", default=[])
    parser.add_argument("--has-report", action="store_true")
    parser.add_argument("--spec-ready", action="store_true")
    parser.add_argument("--single-session", action="store_true")
    parser.add_argument("--multi-session", action="store_true")
    parser.add_argument("--phase", required=True)
    parser.add_argument("--work-kind", choices=sorted(WORK_KINDS), default="auto")
    parser.add_argument("--quality-profile", choices=("draft", "release"), default="draft")
    parser.add_argument("--effort-profile", choices=("mechanical", "scientific_review"), default="mechanical")
    parser.add_argument("--max-repair-rounds", type=int, choices=(0, 1, 2), default=2)
    parser.add_argument("--max-checkpoint-rounds", type=int, default=1)
    parser.add_argument("--max-regression-rounds", type=int, default=0)
    parser.add_argument("--repair-round", type=int, default=0)
    parser.add_argument("--checkpoint-round", type=int, default=0)
    parser.add_argument("--regression-round", type=int, default=0)
    parser.add_argument(
        "--report-context",
        "--report-mode",
        dest="report_context",
        choices=("none", "auto", "one-off", "one_off", "module-reusable", "module_reusable"),
    )
    full_group = parser.add_mutually_exclusive_group()
    full_group.add_argument("--has-full", "--full-required", dest="has_full", action="store_true")
    full_group.add_argument("--no-full", "--no-full-required", dest="has_full", action="store_false")
    parser.set_defaults(has_full=None)
    review_group = parser.add_mutually_exclusive_group()
    review_group.add_argument("--requires-review", "--review-required", dest="requires_review", action="store_true")
    review_group.add_argument("--no-review", "--no-review-required", dest="requires_review", action="store_false")
    parser.set_defaults(requires_review=None)
    parser.add_argument("--development-plan")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = infer(
        args.task_type,
        args.changed_path,
        args.has_report,
        args.spec_ready,
        args.single_session,
        args.multi_session,
        args.phase,
        args.quality_profile,
        args.effort_profile,
        args.work_kind,
        args.max_repair_rounds,
        report_context=args.report_context,
        has_full=args.has_full,
        requires_review=args.requires_review,
        development_plan=args.development_plan,
        repair_round=args.repair_round,
        checkpoint_round=args.checkpoint_round,
        regression_round=args.regression_round,
        max_checkpoint_rounds=args.max_checkpoint_rounds,
        max_regression_rounds=args.max_regression_rounds,
        module=args.module,
    )
    result["module"] = args.module
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.output.parent, prefix=f".{args.output.name}.", delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(payload)
            os.replace(temporary, args.output)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
    print(payload, end="")
    return 2 if result["blocked_reasons"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
