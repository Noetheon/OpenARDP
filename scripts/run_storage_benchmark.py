"""Run and publish the F022 storage benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from scripts.storage_benchmark import execute
except ModuleNotFoundError:
    from storage_benchmark import execute


def main() -> int:
    """Execute all frozen scenarios into one fresh output directory."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        decision = execute(arguments.repository_root, arguments.output)
    except (FileExistsError, OSError, ValueError):
        print("storage_benchmark_failed")
        return 4
    print(f"storage_benchmark_decision={decision['decision']}")
    return 0 if decision["decision"] == "PASS" else 8


if __name__ == "__main__":
    raise SystemExit(main())
