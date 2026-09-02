#!/usr/bin/env python3
"""Minimal Python stage boundary; insert only the approved scientific logic."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one declared bioinformatics stage.")
    parser.add_argument("config", type=Path, help="configuration file")
    args = parser.parse_args()
    config = args.config.resolve(strict=True)
    config_dir = config.parent
    # Set the contract's frozen seed here after it has been approved; do not
    # derive a scientific seed from today's date or a process-global default.
    # Validate artifact identity, fields, units, direction and non-degenerate
    # conditions before importing or running the scientific core.
    raise SystemExit("EVIDENCE_NEEDED: implement the approved scientific stage")


if __name__ == "__main__":
    raise SystemExit(main())
