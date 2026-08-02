"""Run and publish the F023 offline PDF readiness benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from scripts.pdf_bundle_benchmark import execute
except ModuleNotFoundError:
    from pdf_bundle_benchmark import execute


def main() -> int:
    """Run the frozen actual-bundle workload into a fresh output directory."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--provision-duration-ns", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        decision = execute(
            arguments.repository_root,
            bundle=arguments.bundle,
            package=arguments.package,
            provision_duration_ns=arguments.provision_duration_ns,
            output=arguments.output,
        )
    except (FileExistsError, OSError, ValueError):
        print("pdf_bundle_benchmark_failed")
        return 4
    print(f"pdf_bundle_benchmark_decision={decision['decision']}")
    return 0 if decision["decision"] == "PDF_OFFLINE_READY" else 8


if __name__ == "__main__":
    raise SystemExit(main())
