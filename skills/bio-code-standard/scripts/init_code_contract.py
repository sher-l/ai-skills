#!/usr/bin/env python3
"""创建合同工作区，并在模块根补齐五阶段入口骨架。"""
from __future__ import annotations

import argparse
import configparser
import json
import os
from pathlib import Path
import shutil
import sys

import source_review
import diagnostic_output

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def starter(
    module: str,
    quality_profile: str,
    effort_profile: str,
    languages: set[str],
    with_plot: bool = True,
    with_report: bool = True,
    with_full: bool = True,
) -> tuple[dict, dict]:
    # 同时生成两种语言时优先可移植的 Python 入口；已有 source-review 记录会覆盖该起始选择。
    canonical_source = "scripts/calculate/main.py" if "python" in languages else "scripts/calculate/main.R"
    contract = {
        "schema_version": "0.1.0",
        "module": module,
        "quality_profile": quality_profile,
        "effort_profile": effort_profile,
        "max_repair_rounds": 2,
        "result_layout": "flat",
        "description": "填写模块目的、对象范围和公开产物",
        "help": {
            "summary": f"{module}：填写面向人和 AI 的模块摘要",
            "commands": {
                "help": "显示模块目的、输入和输出",
                "init": "创建或校验配置，不运行分析",
                "calculate": "执行已声明的科学计算",
            },
        },
        "canonical_source": canonical_source,
        "source_review": "doc/source-review.md",
        "stages": [
            {
                "id": "init",
                "purpose": "创建或校验 module.config.ini，不运行分析",
                "inputs": [{"path": "module.config.ini", "kind": "ini_config"}],
                "outputs": [],
                "method": {"name": "ini_validation", "version": "stdlib"},
                "parameters": {},
                "seed": None,
                "non_degenerate": "配置可解析且路径边界合法",
            },
            {
                "id": "calculate",
                "purpose": "填写一个已批准的分析目标",
                "inputs": [],
                "outputs": [],
                "method": {"name": "填写实际方法", "version": "填写实现版本"},
                "parameters": {},
                "seed": None,
                "non_degenerate": "填写最小有效输入和停止条件",
                "log": "log/calculate.log",
            }
        ],
        "inputs": [],
        "outputs": [],
        "evidence_pack": ".code-contract/analysis_evidence_pack.json",
    }
    if with_plot:
        contract["help"]["commands"]["plot"] = "只从 calculate 已发布结果渲染图件"
        contract["plot"] = {"figure_manifest": ".code-contract/figure_manifest.json"}
        contract["stages"].append(
            {
                "id": "plot",
                "purpose": "从 calculate 已发布结果渲染图件",
                "inputs": [{"from_stage": "calculate", "kind": "published_result"}],
                "outputs": [],
                "method": {"name": "figure_renderer", "version": "填写实现版本"},
                "parameters": {},
                "seed": None,
                "non_degenerate": "calculate 结果存在且图件输入可读",
                "lineage": ["calculate"],
                "log": "log/plot.log",
            }
        )
    if with_report:
        contract["help"]["commands"]["report"] = "只组装 calculate 事实和 plot 图件"
        contract["report"] = {"inputs": ["calculate", "plot"]}
        contract["stages"].append(
            {
                "id": "report",
                "purpose": "组装 calculate 事实和 plot 图件",
                "inputs": [
                    {"from_stage": "calculate", "kind": "published_result"},
                    {"from_stage": "plot", "kind": "figure_manifest"},
                ],
                "outputs": [],
                "method": {"name": "report_assembly", "version": "填写实现版本"},
                "parameters": {},
                "seed": None,
                "non_degenerate": "calculate 结果和 plot 图件均存在",
                "lineage": ["calculate", "plot"],
                "log": "log/report.log",
            }
        )
    if with_full:
        contract["help"]["commands"]["full"] = "按 calculate → plot → report 顺序串联"
        contract["full"] = {"expands_to": ["calculate", "plot", "report"]}
        contract["stages"].append(
            {
                "id": "full",
                "purpose": "按 calculate → plot → report 顺序串联",
                "inputs": [{"from_stage": "calculate", "kind": "declared_input"}],
                "outputs": [],
                "method": {"name": "stage_orchestration", "version": "填写实现版本"},
                "parameters": {},
                "seed": None,
                "non_degenerate": "三个被串联阶段均成功；不运行 init",
                "lineage": ["calculate", "plot", "report"],
                "log": "log/full.log",
            }
        )
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


def validate_ini(path: Path) -> tuple[bool, str]:
    """只检查 INI 语法和最小命名，不执行配置中的科学操作。"""
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    try:
        with path.open("r", encoding="utf-8") as handle:
            parser.read_file(handle)
    except (OSError, UnicodeDecodeError, configparser.Error) as exc:
        return False, str(exc)
    if not parser.sections():
        return False, "INI 至少需要一个 section"
    return True, ""


def _same_file(left: Path, right: Path) -> bool:
    """比较两个普通文件内容；目标不存在时返回 False。"""
    try:
        return left.is_file() and right.is_file() and left.read_bytes() == right.read_bytes()
    except OSError:
        return False


def _copy_if_absent(source: Path, target: Path) -> None:
    """只补齐缺少的模板，不覆盖模块已有源码。"""
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_file():
            raise OSError(f"目标不是普通文件: {target}")
        return
    shutil.copyfile(source, target)


def _install_module_skeleton(module_root: Path, languages: set[str]) -> None:
    """在模块根补齐入口和四个实际脚本目录；不预建结果、报告或日志目录。"""
    run_path = module_root / "run.sh"
    run_created = not run_path.exists()
    _copy_if_absent(TEMPLATES / "run.sh", run_path)
    if run_created:
        run_path.chmod(0o755)
    if "r" in languages:
        _copy_if_absent(TEMPLATES / "init_stage.R", module_root / "scripts" / "init.R")
        for stage in ("calculate", "plot", "report"):
            _copy_if_absent(TEMPLATES / "r_stage.R", module_root / "scripts" / stage / "main.R")
    if "python" in languages:
        _copy_if_absent(TEMPLATES / "init_stage.py", module_root / "scripts" / "init.py")
        for stage in ("calculate", "plot", "report"):
            _copy_if_absent(TEMPLATES / "python_stage.py", module_root / "scripts" / stage / "main.py")


def _set_template_language(path: Path, languages: set[str]) -> None:
    """让公开入口知道同时生成两种模板时应调用哪一种。"""
    preferred = "python" if "python" in languages else "r"
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError:
        return
    updated = []
    replaced = False
    for line in lines:
        if line.lstrip().startswith("language ="):
            updated.append(f"language = {preferred}\n")
            replaced = True
        else:
            updated.append(line)
    if replaced:
        path.write_text("".join(updated), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", help="模块名称（脚手架模式必填）")
    parser.add_argument("--output", type=Path, help="合同工作区目录（脚手架模式必填）")
    parser.add_argument("-c", "--config", type=Path, help="模块 INI 配置文件；省略时复制模板")
    parser.add_argument("--languages", default="r,python", help="逗号分隔：r、python")
    parser.add_argument("--quality-profile", choices=("draft", "release"), default="draft")
    parser.add_argument("--effort-profile", choices=("mechanical", "scientific_review"), default="mechanical")
    parser.add_argument("--with-plot", action="store_true", help="兼容旧命令；标准脚手架始终声明 plot")
    parser.add_argument("--with-report", action="store_true", help="兼容旧命令；标准脚手架始终声明 report")
    parser.add_argument("--with-full", action="store_true", help="兼容旧命令；标准脚手架始终声明 full")
    parser.add_argument("--json", action="store_true", dest="as_json", help="以 JSON 输出配置校验结果")
    args = parser.parse_args(argv)

    # `init -c PATH` 是公开的零计算配置入口；缺少目标文件时直接复制单个 INI 模板。
    if args.module is None or args.output is None:
        if args.module is not None or args.output is not None or args.config is None:
            message = "配置校验模式只需 -c module.config.ini；脚手架模式需同时提供 --module 和 --output"
            print(f"错误类型: CONFIG_ERROR\n错误内容: {message}\n修复建议: 使用 run.sh init -c module.config.ini，或补齐脚手架参数\n退出码: 2", file=sys.stderr)
            return 2
        if args.with_plot or args.with_report or args.with_full:
            message = "init 配置校验不会声明 plot/report/full 能力"
            print(f"错误类型: CONFIG_ERROR\n错误内容: {message}\n修复建议: 去掉 --with-*，阶段能力写入合同的 stages\n退出码: 2", file=sys.stderr)
            return 2
        config_path = args.config.resolve()
        created = False
        if config_path.is_symlink() or (config_path.exists() and not config_path.is_file()):
            errors = [f"配置目标不是普通文件: {config_path}"]
        elif not config_path.exists():
            template = TEMPLATES / "module.config.ini"
            if not config_path.parent.is_dir():
                errors = [f"配置文件的父目录不存在；init 不创建配置目录: {config_path.parent}"]
            elif not template.is_file():
                errors = [f"找不到可复制的 INI 模板: {template}"]
            else:
                temporary = config_path.with_name(f".{config_path.name}.tmp.{os.getpid()}")
                try:
                    shutil.copyfile(template, temporary)
                    os.replace(temporary, config_path)
                    created = True
                    valid, detail = validate_ini(config_path)
                    errors = [] if valid else [f"生成的 INI 配置不可读: {detail}"]
                except OSError as exc:
                    try:
                        temporary.unlink()
                    except OSError:
                        pass
                    errors = [f"无法生成配置文件: {exc}"]
        else:
            valid, detail = validate_ini(config_path)
            errors = [] if valid else [f"INI 配置不可读: {detail}"]
        result = {
            "status": "PASS" if not errors else "BLOCKED",
            "stage": "init",
            "config": str(config_path),
            "created": created,
            "errors": errors,
            "warnings": [],
            "diagnostics": diagnostic_output.entries(errors, [], str(config_path), domain="contract", fixes="修正 module.config.ini 后重新运行校验"),
            "exit_code": 0 if not errors else 2,
        }
        if args.as_json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif errors:
            diagnostic_output.print_result("INIT", "BLOCKED", errors, [], domain="contract", fixes="修正 module.config.ini 后重新运行校验")
        else:
            print("INIT_PASS config_valid=true")
            print("退出码: 0", file=sys.stderr)
        return result["exit_code"]

    # v2.2 标准脚手架固定包含三个业务阶段和 full 编排；旧 --with-* 仅保留兼容，不再改变能力集合。
    with_plot = with_report = with_full = True

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        message = f"输出目录非空: {output}"
        print(f"错误类型: OUTPUT_ERROR\n错误内容: {message}\n修复建议: 选择空目录或确认后清理目标\n退出码: 1", file=sys.stderr)
        return 1
    languages = {item.strip().lower() for item in args.languages.split(",") if item.strip()}
    if languages - {"r", "python"} or not languages:
        print("错误类型: CONFIG_ERROR\n错误内容: languages 只能包含 r 和/或 python；实际值="
              f"{args.languages}\n修复建议: 使用 --languages r、python 或 r,python\n退出码: 2", file=sys.stderr)
        return 2
    config_source = args.config.resolve() if args.config else None
    module_root = output.parent
    config_target = module_root / "module.config.ini"
    if config_target.is_symlink():
        print(f"错误类型: OUTPUT_ERROR\n错误内容: 模块根配置不能是符号链接: {config_target}\n"
              "修复建议: 使用普通文件 module.config.ini 后重试\n退出码: 1", file=sys.stderr)
        return 1
    if config_source is not None:
        if not config_source.is_file():
            print(f"错误类型: CONFIG_ERROR\n错误内容: 配置文件不存在: {config_source}\n"
                  "修复建议: 使用存在的 module.config.ini，或省略 -c 复制模板\n退出码: 2", file=sys.stderr)
            return 2
        valid_ini, ini_error = validate_ini(config_source)
        if not valid_ini:
            print(f"错误类型: CONFIG_ERROR\n错误内容: INI 配置不可读: {ini_error}\n"
                  "修复建议: 修正 module.config.ini 的 section、键和值后重试\n退出码: 2", file=sys.stderr)
            return 2
        if config_target.exists() and config_source != config_target and not _same_file(config_source, config_target):
            print(f"错误类型: OUTPUT_ERROR\n错误内容: 模块根已有不同的 module.config.ini: {config_target}\n"
                  "修复建议: 保留现有配置，或先确认后使用同一配置文件\n退出码: 1", file=sys.stderr)
            return 1
    elif config_target.exists():
        valid_ini, ini_error = validate_ini(config_target)
        if not valid_ini:
            print(f"错误类型: CONFIG_ERROR\n错误内容: 模块根配置不可读: {ini_error}\n"
                  "修复建议: 修正 module.config.ini 后重试\n退出码: 2", file=sys.stderr)
            return 2
    output.mkdir(parents=True, exist_ok=True)
    contract, pack = starter(
        args.module,
        args.quality_profile,
        args.effort_profile,
        languages,
        with_plot,
        with_report,
        with_full,
    )
    # 审查记录属于模块级科学文档，不是生成合同工作区的子文件。
    # ``--output`` 通常是 MODULE/.code-contract；公开入口和阶段脚本位于 MODULE 根。
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
    if with_plot:
        write_json(
            output / "figure_manifest.json",
            {"schema_version": "0.1.0", "result_layout": "flat", "figures": []},
        )
    created_config = not config_target.exists()
    if created_config:
        shutil.copyfile(config_source or (TEMPLATES / "module.config.ini"), config_target)
    if created_config and config_source is None:
        _set_template_language(config_target, languages)
    try:
        _install_module_skeleton(module_root, languages)
    except OSError as exc:
        print(f"错误类型: OUTPUT_ERROR\n错误内容: 无法补齐模块入口: {exc}\n"
              "修复建议: 检查模块根目录中的既有入口文件和权限\n退出码: 1", file=sys.stderr)
        return 1
    # 模块尚无源码时不要伪造审查记录；第一步必须针对真实模块根目录执行
    # ``source-review init``，否则合同保持 EVIDENCE_NEEDED。
    print(json.dumps({
        "status": "DRAFT",
        "module": args.module,
        "output": str(output),
        "module_root": str(module_root),
        "config": str(config_target),
        "stages": ["init", "calculate", "plot", "report", "full"],
        "exit_code": 0,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
