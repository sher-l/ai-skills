#!/usr/bin/env python3
"""最小 Python 阶段边界；这里只填写已批准的科学逻辑。"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="运行一个已声明的生物信息学阶段。")
    parser.add_argument("config", type=Path, nargs="?", help="配置文件")
    parser.add_argument("--output", type=Path, required=False, help="本次阶段输出根目录")
    args = parser.parse_args()
    if args.config is None:
        print("错误类型: INPUT_ERROR\n错误内容: 未提供配置文件\n修复建议: 使用 run.sh <stage> -c module.config.ini\n退出码: 2", file=sys.stderr)
        return 2
    try:
        config = args.config.resolve(strict=True)
    except OSError as exc:
        print(f"错误类型: INPUT_ERROR\n错误内容: 无法读取配置文件：{exc}\n修复建议: 检查 module.config.ini 路径和权限\n退出码: 2", file=sys.stderr)
        return 2
    config_dir = config.parent
    output = args.output.resolve() if args.output else config_dir
    # 合同批准固定随机种子后在这里设置；不得用当天日期或进程级默认值推导科学随机种子。
    # 导入或运行科学核心代码前，先校验产物身份、字段、单位、方向和非退化条件。
    print(
        "错误类型: EVIDENCE_ERROR\n"
        "错误内容: 当前阶段仍是脚手架，尚未接入已批准的科学逻辑\n"
        "修复建议: 按 code_contract 填写真实输入、方法、产物和非退化检查后重试\n"
        "退出码: 2",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
