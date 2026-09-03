#!/usr/bin/env python3
"""为 develop-module 生成确定性的内部路由计划。

调度器只分类任务、列出叶子 adapter 并返回一个 Matt owner；不运行 adapter，
也不做科学判断。数据模型显式区分生命周期 owner 与领域 adapter，避免下游误把
owner 递归成 adapter。
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
from typing import Any


CODE_HINTS = {".r", ".rmd", ".py", ".sh", ".yaml", ".yml", ".json", ".ini", ".toml"}
# `figure`/`renderer` 只表示作图能力；只有明确报告表面才加载 report adapter。
REPORT_HINTS = {
    "report",
    "caption",
    "docx",
    "report_stage",
    "narrative",
    "prose",
    "template",
}
REPORT_ONLY_HINTS = set(REPORT_HINTS)
TASK_TYPES = {"new", "migrate", "optimize", "substantial_change", "review"}
PHASES = {"scope", "build", "draft", "finish"}
WORK_KINDS = {"auto", "code", "report", "both", "review"}
REPORT_CONTEXTS = {"none", "one_off", "module_reusable"}
EXECUTION_SCOPES = {"report-only", "plot", "full"}
PLOT_HINTS = {"plot", "figure", "figures", "visual", "renderer", "render", "ggplot", "draw"}
FULL_HINTS = {
    "calculate",
    "analysis",
    "scientific",
    "config",
    "contract",
    "schema",
    "output",
    "result",
    "model",
    "stat",
    "input",
}
ENTRY_SKILL = "develop-module"
SCHEDULER_SKILL = "module-development-scheduler"
CODE_SKILL = "bio-code-standard"
REPORT_SKILL = "bio-report-writing"
OWNER = "matt-executor"
PLAN_PHASE = {"scope": "start", "build": "build", "draft": "draft", "finish": "finish"}


def _normalise_report_context(value: str | None, report: bool) -> str:
    """接受用户写法，并保留一个规范 JSON 值。"""
    if value is None or value in {"", "auto"}:
        return "module_reusable" if report else "none"
    normalised = value.strip().lower().replace("-", "_")
    return normalised


def _normalise_execution_scope(value: str | None) -> str | None:
    if value is None or value in {"", "auto"}:
        return None
    normalised = value.strip().lower().replace("_", "-")
    aliases = {"report": "report-only", "report-only": "report-only", "plot-only": "plot", "full": "full"}
    return aliases.get(normalised, normalised)


def _infer_execution_scope(
    explicit: str | None,
    work_kind: str,
    code: bool,
    report: bool,
    paths: list[str],
) -> str:
    """依据声明路径选择最小的执行边界。"""
    normalised = _normalise_execution_scope(explicit)
    if normalised is not None:
        return normalised
    if work_kind == "report" or (report and not code):
        return "report-only"
    lowered = [path.lower() for path in paths]
    joined = " ".join(lowered)
    has_plot = any(token in joined for token in PLOT_HINTS)
    has_full = any(token in joined for token in FULL_HINTS)
    if code and has_plot and not has_full:
        return "plot"
    return "full"


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
        # 回归上限为零表示不设人工上限；回归轮是证据，不是第二套生命周期。
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
    execution_scope: str | None = None,
) -> dict[str, Any]:
    """返回一个确定性的路由计划。

    保留 ``max_repair_rounds`` 之前的定位参数，兼容早期调用方；新增控制项可用
    关键字传入，且不改变生命周期 owner。
    """
    paths = [path for path in paths if isinstance(path, str)]
    lowered = [path.lower() for path in paths]
    path_code = any(Path(path).suffix.lower() in CODE_HINTS for path in lowered)
    joined_paths = " ".join(lowered)
    path_plot = any(token in joined_paths for token in PLOT_HINTS)
    path_full = any(token in joined_paths for token in FULL_HINTS)
    path_code = path_code or path_plot or path_full
    path_report = any(any(token.lower() in path for token in REPORT_HINTS) for path in lowered)
    inferred_report = bool(has_report or path_report)

    # new/migrate/optimize/change 默认是 code；显式 report 类型优先，避免空的
    # new scope 静默跳过 code adapter。
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

    explicit_scope = _normalise_execution_scope(execution_scope)
    report_surface = bool(paths) and all(
        any(token in path.lower() for token in REPORT_ONLY_HINTS)
        for path in paths
    ) and not any(token in joined_paths for token in FULL_HINTS)
    if report_surface and work_kind in {"auto", "review"}:
        code, report = False, True
    if explicit_scope == "report-only":
        # 报告编辑的显式 scope 优先。报告 renderer 也可能是 R/Python 文件，
        # 因此不能仅凭后缀把它当科学代码。
        if not any(token in joined_paths for token in FULL_HINTS):
            code, report = False, True
    elif explicit_scope == "plot":
        code = True
        report = report or has_report
    context = _normalise_report_context(report_context, report)
    scope = _infer_execution_scope(execution_scope, work_kind, code, report, paths)
    blockers: list[str] = []
    if not task_type or task_type not in TASK_TYPES:
        blockers.append("task_type must be one of new/migrate/optimize/substantial_change/review")
    if not phase or phase not in PHASES:
        blockers.append("phase must be one of scope/build/draft/finish")
    if (
        not paths
        and explicit_scope is None
        and task_type in {"migrate", "optimize", "substantial_change", "review"}
    ):
        blockers.append("changed paths or an explicit scope are required")
    if work_kind not in WORK_KINDS:
        blockers.append("work_kind must be auto, code, report, both, or review")
    if context not in REPORT_CONTEXTS:
        blockers.append("report_context must be none, one_off, or module_reusable")
    if context == "none" and report:
        blockers.append("report work requires report_context one_off or module_reusable")
    if context != "none" and not report:
        blockers.append("report_context is only valid for report work")
    if scope not in EXECUTION_SCOPES:
        blockers.append("execution_scope must be report-only, plot, or full")
    if explicit_scope is None and paths and not report_surface:
        clear_plot = any(token in joined_paths for token in PLOT_HINTS)
        clear_full = any(token in joined_paths for token in FULL_HINTS)
        if (code or (not report and task_type != "review")) and not clear_plot and not clear_full:
            blockers.append("execution_scope is ambiguous; pass --execution-scope report-only, plot, or full")
    if scope == "report-only" and code:
        blockers.append("execution_scope=report-only cannot include code work")
    if scope == "report-only" and not report:
        blockers.append("execution_scope=report-only requires report work")
    if scope == "plot" and not code:
        blockers.append("execution_scope=plot requires plotting/code work")
    if scope == "full" and not code and task_type != "review":
        blockers.append("execution_scope=full requires calculation/scientific code work")
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

    # route 是交接决策，不是第二套生命周期。没有 SPEC 时一律回到 Matt planning，
    # 即使调用方声明了 multi-session。
    if single_session and spec_ready:
        route = "fork"
    elif multi_session and spec_ready:
        route = "goal"
    else:
        route = "ask-matt"

    # ``has_full`` 与 ``requires_review`` 是能力声明，不从文件名猜测。能力未知时
    # 不安排对应 finish 检查，必须由调用方显式启用。
    if full_required is not None:
        has_full = full_required
    if review_required is not None:
        requires_review = review_required
    full = _as_bool(has_full, False)
    review = _as_bool(
        requires_review,
        False,
    )
    if full and scope in {"report-only", "plot"}:
        blockers.append(f"execution_scope={scope} cannot require full")
        full = False
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
        # source review 固定先行；报告工作只能消费该 hook 完成后的 code evidence pack。
        checks.extend(["source_review", "code_contract"])
        if scope == "full":
            checks.append("analysis_evidence_pack")
            execution_order.extend(["source_review", "analysis_coder"])
        else:  # plot：不重算科学结果或 evidence
            checks.append("figure_manifest")
            execution_order.extend(["source_review", "plot_coder"])
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
        "module": module or "",
        "task_type": task_type,
        "work_kind": work_kind,
        "execution_scope": scope,
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
    parser.add_argument(
        "--execution-scope",
        "--scope",
        dest="execution_scope",
        choices=("report-only", "report_only", "report", "plot", "full", "auto"),
        help="执行边界：report-only、plot 或 full；省略时按任务面保守推断",
    )
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
        execution_scope=args.execution_scope,
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
