"""Explicitly provision the pinned optional embedding model bundle."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openardp.adapters.embedding_bundle_provisioning import (
    EmbeddingProvisioningError,
    provision_embedding_bundle,
)


def main() -> int:
    """Parse explicit source/destination paths and publish one sanitized result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-lock", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        result = provision_embedding_bundle(arguments.source_lock, arguments.destination)
    except EmbeddingProvisioningError:
        print("embedding_bundle_provision_failed")
        return 6
    print(
        f"embedding_bundle_provisioned bundle_id={result.bundle_id} "
        f"files={result.asset_file_count} bytes={result.asset_bytes}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
