"""Explicit body-free orchestration for derived-block storage optimization."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from openardp.domain.maintenance import (
    StorageOptimizationItem,
    StorageOptimizationOutcome,
    StorageOptimizationReport,
)
from openardp.ports.catalog import StorageOptimizationCatalog
from openardp.ports.object_store import ExistingObjectOptimizer, ObjectStoreError


def _utc_now() -> datetime:
    """Return the current UTC instant for the default production clock."""
    return datetime.now(UTC)


class StorageOptimizationService:
    """Converge catalog-approved blocks and reclaim only disposable free pages."""

    def __init__(
        self,
        object_store: ExistingObjectOptimizer,
        catalog: StorageOptimizationCatalog,
        *,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        """Bind explicit optimizer capabilities without depending on adapters."""
        self._object_store = object_store
        self._catalog = catalog
        self._clock = clock

    def optimize(self) -> StorageOptimizationReport:
        """Optimize every eligible object deterministically and compact the catalog."""
        revision = self._catalog.schema_version()
        items: list[StorageOptimizationItem] = []
        operation_id, eligible = self._catalog.claim_storage_optimization(now=self._clock())
        for stored in eligible:
            try:
                item = self._object_store.optimize_derived_block(
                    stored.object_id,
                    expected_length=stored.byte_length,
                )
            except ObjectStoreError:
                item = StorageOptimizationItem(
                    object_id=stored.object_id,
                    outcome=StorageOptimizationOutcome.FAILED,
                    logical_bytes=stored.byte_length,
                    stored_bytes_before=0,
                    stored_bytes_after=0,
                    reason_code="object_integrity_failed",
                )
            items.append(item)
        self._catalog.complete_storage_optimization(
            operation_id,
            entry_count=len(items),
            byte_count=sum(item.logical_bytes for item in items),
            now=self._clock(),
        )
        catalog_before, catalog_after = self._catalog.compact_catalog_storage()
        return StorageOptimizationReport(
            workspace_revision=revision,
            items=tuple(items),
            catalog_bytes_before=catalog_before,
            catalog_bytes_after=catalog_after,
        )


__all__ = ["StorageOptimizationService"]
