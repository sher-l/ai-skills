#!/usr/bin/env python3
"""模块开发内部调度的统一 CLI。"""
from __future__ import annotations

import argparse

import route_module_task
import validate_route_plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="为模块任务选择一个 Matt 路径及有限领域检查。"
    )
    parser.add_argument("command", choices=("route", "validate"))
    args, rest = parser.parse_known_args(argv)
    if args.command == "route":
        return route_module_task.main(rest)
    return validate_route_plan.main(rest)


if __name__ == "__main__":
    raise SystemExit(main())
