"""Independently verify one installed optional embedding model bundle offline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openardp.adapters.embedding_bundle import EmbeddingBundleError, verify_embedding_bundle


def main() -> int:
    """Parse explicit paths and emit one body-free verification line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-lock", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        result = verify_embedding_bundle(
            arguments.bundle,
            expected_source_lock=arguments.source_lock,
        )
    except (EmbeddingBundleError, OSError, ValueError):
        print("embedding_bundle_invalid")
        return 6
    print(
        f"embedding_bundle_valid bundle_id={result.bundle_id} "
        f"files={result.asset_file_count} bytes={result.asset_bytes}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
