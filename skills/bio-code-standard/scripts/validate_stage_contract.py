#!/usr/bin/env python3
"""校验单个阶段的 INI 配置、能力声明和复用边界。"""
from __future__ import annotations

import argparse
import configparser
import json
from pathlib import Path
import sys

import diagnostic_output


STAGES = ("init", "calculate", "plot", "report", "full")


def read_ini(path: Path) -> tuple[configparser.ConfigParser | None, list[str]]:
    """读取 INI；只做语法解析，不执行任何配置中的命令。"""
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    try:
        with path.open("r", encoding="utf-8") as handle:
            parser.read_file(handle)
    except (OSError, UnicodeDecodeError, configparser.Error) as exc:
        return None, [f"无法读取 INI 配置：{exc}"]
    if not parser.sections():
        return None, ["INI 配置至少需要一个 section"]
    return parser, []


def enabled_stages(parser: configparser.ConfigParser) -> tuple[set[str], list[str]]:
    """解析 [stages] enabled；缺省按 v2.2 标准声明三个业务阶段和 full。"""
    section = parser["stages"] if parser.has_section("stages") else None
    raw = section.get("enabled", "calculate,plot,report,full") if section is not None else "calculate,plot,report,full"
    names = {item.strip().lower() for item in raw.split(",") if item.strip()}
    errors: list[str] = []
    unknown = sorted(names - set(STAGES))
    if unknown:
        errors.append(f"stages.enabled 含不支持的阶段：{', '.join(unknown)}")
    if not names:
        errors.append("stages.enabled 至少包含 calculate")
    if "plot" in names and "calculate" not in names:
        errors.append("plot 需要在 stages.enabled 中声明 calculate")
    if "report" in names and not {"calculate", "plot"}.issubset(names):
        errors.append("report 需要在 stages.enabled 中声明 calculate 和 plot")
    if "full" in names and not {"calculate", "plot", "report"}.issubset(names):
        errors.append("full 需要在 stages.enabled 中声明 calculate、plot 和 report")
    return names, errors


def validate(
    stage: str,
    config: Path,
    *,
    module_root: Path | None = None,
    output: Path | None = None,
) -> tuple[list[str], list[str]]:
    """校验阶段入口；不会运行 R/Python，也不会创建目录或日志。"""
    errors: list[str] = []
    warnings: list[str] = []
    if stage not in STAGES:
        errors.append(f"stage 必须是以下值之一：{', '.join(STAGES)}")
        return errors, warnings
    if config.suffix.lower() != ".ini":
        errors.append(f"配置文件必须使用 .ini 后缀：{config.name}")
    if config.name != "module.config.ini":
        warnings.append(f"配置文件名为 {config.name}；规范名称是 module.config.ini")
    parser, read_errors = read_ini(config)
    errors.extend(read_errors)
    if parser is None:
        return errors, warnings
    enabled, stage_errors = enabled_stages(parser)
    errors.extend(stage_errors)
    if parser.has_section("output") and parser["output"].get("result_layout", "flat").strip().lower() != "flat":
        errors.append("output.result_layout 必须为 flat")
    # init 是配置入口，始终可调用；[stages].enabled 只控制计算/绘图/报告能力。
    if stage != "init" and stage not in enabled:
        errors.append(f"阶段 {stage} 未在 stages.enabled 中声明")
    if output is not None:
        log_dir = output / "log"
        if stage == "init":
            for forbidden in ("init.log", "calculate.log", "plot.log", "report.log", "full.log"):
                if (log_dir / forbidden).exists():
                    errors.append(f"init 不得生成阶段日志：log/{forbidden}")
        elif stage == "full":
            for sibling in ("calculate.log", "plot.log", "report.log"):
                if (log_dir / sibling).exists():
                    errors.append(f"full 只能使用 log/full.log，但发现兄弟日志：log/{sibling}")
    if module_root is not None and stage == "calculate":
        scripts = module_root / "scripts"
        split_dir = scripts / "calculate"
        flat_candidates = [scripts / "calculate.R", scripts / "calculate.py"]
        if not split_dir.is_dir() and not any(path.is_file() for path in flat_candidates):
            warnings.append("未在 scripts/calculate/ 或 scripts/calculate.R|py 找到 calculate 入口")
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=STAGES, help="要校验的阶段")
    parser.add_argument("-c", "--config", required=True, type=Path, help="INI 配置文件")
    parser.add_argument("--module-root", type=Path, help="模块根目录（仅做 calculate 入口提示）")
    parser.add_argument("--output", type=Path, help="已有输出目录（仅检查 init 日志禁写）")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    errors, warnings = validate(
        args.stage,
        args.config.resolve(),
        module_root=args.module_root.resolve() if args.module_root else None,
        output=args.output.resolve() if args.output else None,
    )
    status = "BLOCKED" if errors else ("EVIDENCE_NEEDED" if warnings else "PASS")
    code = diagnostic_output.exit_code(errors, warnings, status=status, domain="contract")
    result = {
        "status": status,
        "stage": args.stage,
        "config": str(args.config),
        "errors": errors,
        "warnings": warnings,
        "diagnostics": diagnostic_output.entries(
            errors,
            warnings,
            str(args.config),
            domain="contract",
            fixes="修正 module.config.ini 或阶段声明后重新运行校验",
        ),
        "exit_code": code,
    }
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        diagnostic_output.print_result(
            f"STAGE_{args.stage.upper()}",
            status,
            errors,
            warnings,
            domain="contract",
            fixes="修正 module.config.ini 或阶段声明后重新运行校验",
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
