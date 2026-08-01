"""Structural port tests for the F014 interchange boundary."""

from __future__ import annotations

from collections.abc import Iterator

from openardp.domain.interchange import PortableAsset
from openardp.ports.interchange import AssetByteSource


class _Source:
    def iter_asset(self, asset: PortableAsset, *, chunk_size: int) -> Iterator[bytes]:
        del asset, chunk_size
        yield b"synthetic"


def test_asset_source_port_is_runtime_checkable() -> None:
    """Keep the byte-source boundary structural and provider neutral."""
    assert isinstance(_Source(), AssetByteSource)
