"""Run and publish the offline F020 product-value benchmark."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from product_benchmark_runner import execute_product_benchmark

from openardp.domain.product_benchmark import BenchmarkProfile
from openardp.domain.rich_ingestion import ModelBundleManifest
from openardp.ports.parser import ParserError

_LOGGER = logging.getLogger(__name__)


def main() -> int:
    """Execute the selected profile with optional explicit offline PDF assets."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--profile",
        choices=tuple(item.value for item in BenchmarkProfile),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pdf-model-root", type=Path)
    parser.add_argument("--pdf-model-manifest", type=Path)
    arguments = parser.parse_args()
    if (arguments.pdf_model_root is None) != (arguments.pdf_model_manifest is None):
        parser.error("PDF model root and manifest must be supplied together")
    try:
        manifest = None
        if arguments.pdf_model_manifest is not None:
            manifest = ModelBundleManifest.model_validate_json(
                arguments.pdf_model_manifest.read_bytes()
            )
        result = execute_product_benchmark(
            arguments.repository_root,
            profile=BenchmarkProfile(arguments.profile),
            output=arguments.output,
            model_root=arguments.pdf_model_root,
            model_manifest=manifest,
        )
    except FileExistsError:
        print("benchmark_output_conflict")
        return 8
    except ParserError as error:
        _LOGGER.debug("product benchmark parser failure: %s", type(error).__name__)
        print("benchmark_execution_failed")
        return 6
    except (OSError, ValueError):
        print("benchmark_execution_failed")
        return 6
    print(
        f"outcome={result.decision.outcome.value} "
        f"decision_id={result.decision.decision_id} output={result.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
