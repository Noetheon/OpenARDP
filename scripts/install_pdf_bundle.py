"""Safely install a portable PDF model bundle without network access."""

from __future__ import annotations

import argparse
from pathlib import Path

from openardp.adapters.docling_bundle import BundleValidationError
from openardp.adapters.docling_bundle_archive import install_bundle_package
from openardp.domain.identity import canonical_json_bytes


def main() -> int:
    """Install into a fresh destination and print reconciled identities."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-lock", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        result = install_bundle_package(
            arguments.package,
            arguments.destination,
            expected_source_lock=arguments.source_lock,
        )
    except BundleValidationError:
        print('{"category":"pdf_bundle_installation_failed"}')
        return 6
    print(canonical_json_bytes(result.model_dump(mode="json")).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
