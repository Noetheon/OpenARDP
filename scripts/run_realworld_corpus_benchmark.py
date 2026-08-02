"""Execute and publish the F024 six-format structural baseline."""

from __future__ import annotations

import argparse
from pathlib import Path

from realworld_corpus_benchmark import execute


def main() -> int:
    """Run one explicit reference benchmark with a validated F023 bundle."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--pdf-bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        decision = execute(
            arguments.repository_root,
            pdf_bundle=arguments.pdf_bundle,
            output=arguments.output,
        )
    except FileExistsError:
        print("benchmark_output_conflict")
        return 8
    except (OSError, ValueError):
        print("benchmark_execution_failed")
        return 6
    print(
        f"decision={decision['decision']} failures={len(decision['failure_codes'])} "
        f"output={arguments.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
