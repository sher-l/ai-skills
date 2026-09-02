#!/usr/bin/env python3
"""Single CLI for internal module-development scheduling."""
from __future__ import annotations

import argparse

import route_module_task
import validate_route_plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Choose one Matt route and the finite domain checks for a module task."
    )
    parser.add_argument("command", choices=("route", "validate"))
    args, rest = parser.parse_known_args(argv)
    if args.command == "route":
        return route_module_task.main(rest)
    return validate_route_plan.main(rest)


if __name__ == "__main__":
    raise SystemExit(main())
