"""Validate a published F020 product-value result without rerunning workloads."""

from __future__ import annotations

import argparse
from pathlib import Path

from product_benchmark_runner import validate_product_benchmark


def main() -> int:
    """Recompute all identities, summaries, decision checks and report projection."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--result", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        result = validate_product_benchmark(arguments.repository_root, arguments.result)
    except (OSError, ValueError):
        print("benchmark_evidence_invalid")
        return 6
    print(
        '{"category":"benchmark_evidence_valid","decision_id":"'
        f'{result.decision.decision_id}","outcome":"{result.decision.outcome.value}"}}'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
