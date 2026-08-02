"""Explicitly provision the locked Docling PDF model bundle."""

from __future__ import annotations

import argparse
from pathlib import Path

from openardp.adapters.docling_bundle_provisioning import ProvisioningError, provision_bundle
from openardp.domain.identity import canonical_json_bytes


def main() -> int:
    """Provision a fresh destination and print a body-free canonical result."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-lock", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        result = provision_bundle(arguments.source_lock, arguments.destination)
    except ProvisioningError:
        print('{"category":"pdf_bundle_provisioning_failed"}')
        return 6
    print(canonical_json_bytes(result.model_dump(mode="json")).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
