"""Generate one deterministic F020 text corpus for inspection."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from openardp.adapters.product_benchmarks import generate_text_corpus, load_benchmark_inputs
from openardp.domain.product_benchmark import BenchmarkProfile


def main() -> int:
    """Generate the selected frozen corpus profile into a fresh directory."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--profile",
        choices=("smoke", "reference", "scale"),
        required=True,
    )
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--output", type=Path)
    destination.add_argument("--check", type=Path)
    arguments = parser.parse_args()
    try:
        inputs = load_benchmark_inputs(
            arguments.repository_root.resolve() / "benchmarks/product-value/v0.1.0"
        )
        if arguments.check is not None:
            with tempfile.TemporaryDirectory(prefix="openardp-f020-check-") as temporary:
                generated = generate_text_corpus(
                    inputs,
                    BenchmarkProfile(arguments.profile),
                    Path(temporary) / "generated",
                )
                expected = arguments.check
                expected_files = tuple(sorted(path.name for path in expected.iterdir()))
                actual_files = tuple(
                    sorted(path.name for path in generated.source.parent.iterdir())
                )
                if expected_files != actual_files or any(
                    (expected / name).read_bytes() != (generated.source.parent / name).read_bytes()
                    for name in actual_files
                ):
                    print("benchmark_drift_detected")
                    return 8
        else:
            generated = generate_text_corpus(
                inputs,
                BenchmarkProfile(arguments.profile),
                arguments.output,
            )
    except (FileExistsError, OSError, ValueError):
        print("benchmark_input_rejected")
        return 4
    print(
        f"generated profile={generated.profile.value} blocks={generated.block_count} "
        f"bytes={generated.source_bytes} sha256={generated.source_sha256}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
