"""Create a deterministic portable PDF model bundle package."""

from __future__ import annotations

import argparse
from pathlib import Path

from openardp.adapters.docling_bundle import BundleValidationError
from openardp.adapters.docling_bundle_archive import create_bundle_package
from openardp.domain.identity import canonical_json_bytes


def main() -> int:
    """Package one verified installation and print its exact identity."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-lock", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        result = create_bundle_package(
            arguments.bundle,
            arguments.output,
            expected_source_lock=arguments.source_lock,
        )
    except BundleValidationError:
        print('{"category":"pdf_bundle_packaging_failed"}')
        return 6
    print(canonical_json_bytes(result.model_dump(mode="json")).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
