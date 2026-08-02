"""Verify a PDF model bundle against an independent committed source lock."""

from __future__ import annotations

import argparse
from pathlib import Path

from openardp.adapters.docling_bundle import BundleValidationError, verify_installation
from openardp.domain.identity import canonical_json_bytes


def main() -> int:
    """Verify the exact closed installation and print a body-free result."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-lock", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        result = verify_installation(
            arguments.bundle,
            expected_source_lock=arguments.source_lock,
        )
    except BundleValidationError:
        print('{"category":"pdf_bundle_invalid"}')
        return 6
    print(canonical_json_bytes(result.model_dump(mode="json")).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
