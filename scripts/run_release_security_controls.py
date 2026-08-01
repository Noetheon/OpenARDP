"""Execute exactly the frozen F015 security-control pytest nodes offline."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from openardp.adapters.release_security import load_security_controls


def main() -> int:
    """Run every unique allowlisted node and emit one JUnit evidence file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--controls", type=Path, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    arguments = parser.parse_args()
    controls = load_security_controls(arguments.controls)
    nodes = tuple(node for control in controls for node in control.test_nodes)
    if len(nodes) != len(set(nodes)):
        raise RuntimeError("security test node registry is not unique")
    completed = subprocess.run(  # noqa: S603 -- current interpreter and frozen test nodes only
        [
            sys.executable,
            "-m",
            "pytest",
            "--no-cov",
            f"--junitxml={arguments.junit}",
            *nodes,
        ],
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
