#!/usr/bin/env python3
"""生成或校验单个 module.config.ini，不运行任何科学分析。"""
from __future__ import annotations

import configparser
from pathlib import Path
import shutil
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("错误类型: INPUT_ERROR\n错误内容: init 需要一个 module.config.ini 路径\n修复建议: 使用 run.sh init -c module.config.ini\n退出码: 2", file=sys.stderr)
        return 2
    raw_config = Path(sys.argv[1]).expanduser()
    config = raw_config.absolute()
    module_root = Path(__file__).resolve().parents[1]
    template = module_root / "module.config.ini"
    created = False
    if raw_config.is_symlink() or (config.exists() and not config.is_file()):
        print("错误类型: OUTPUT_ERROR\n错误内容: 配置目标必须是普通文件\n修复建议: 将 -c 指向普通的 module.config.ini 文件\n退出码: 1", file=sys.stderr)
        return 1
    if not config.exists():
        if not config.parent.is_dir():
            print("错误类型: OUTPUT_ERROR\n错误内容: 配置文件的父目录不存在；init 不创建配置目录\n修复建议: 先创建父目录，再使用 -c module.config.ini\n退出码: 1", file=sys.stderr)
            return 1
        if not template.is_file() or config == template:
            print("错误类型: CONFIG_ERROR\n错误内容: 找不到可复制的模块 INI 模板\n修复建议: 保留模块根 module.config.ini，或先运行代码脚手架\n退出码: 2", file=sys.stderr)
            return 2
        temporary = config.with_name(config.name + f".tmp.{__import__('os').getpid()}")
        try:
            shutil.copyfile(template, temporary)
            temporary.replace(config)
            created = True
        except OSError as exc:
            try:
                temporary.unlink()
            except OSError:
                pass
            print(f"错误类型: OUTPUT_ERROR\n错误内容: 无法生成配置文件：{exc}\n修复建议: 检查目标目录权限后重试\n退出码: 1", file=sys.stderr)
            return 1
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    try:
        with config.open("r", encoding="utf-8") as handle:
            parser.read_file(handle)
    except (OSError, UnicodeDecodeError, configparser.Error) as exc:
        print(f"错误类型: CONFIG_ERROR\n错误内容: 无法读取 INI 配置：{exc}\n修复建议: 修正 module.config.ini 的格式和编码\n退出码: 2", file=sys.stderr)
        return 2
    if not parser.sections():
        print("错误类型: CONFIG_ERROR\n错误内容: INI 配置至少需要一个 section\n修复建议: 添加 [module] 等配置段后重试\n退出码: 2", file=sys.stderr)
        return 2
    print(f"INIT_PASS config={config} created={'true' if created else 'false'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
