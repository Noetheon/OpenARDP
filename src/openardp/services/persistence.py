"""Cross-resource orchestration for immutable source-version persistence."""

from __future__ import annotations

import secrets
from collections.abc import Callable, Iterable
from datetime import datetime
from uuid import UUID

from openardp.domain.storage import (
    DocumentVersion,
    LogicalDocument,
    ObjectReference,
    SourceKey,
    SourceVersionCommit,
    generate_uuid7,
)
from openardp.ports.catalog import Catalog, DocumentConflict
from openardp.ports.object_store import ObjectStore


def _random_uuid7_bits() -> int:
    """Return cryptographically strong entropy for a UUIDv7 identity."""
    return secrets.randbits(74)


class PersistenceService:
    """Publish complete CAS objects before atomically committing catalog facts."""

    def __init__(
        self,
        object_store: ObjectStore,
        catalog: Catalog,
        *,
        random_bits: Callable[[], int] = _random_uuid7_bits,
    ) -> None:
        """Bind provider-neutral persistence ports and an injectable UUID source."""
        self._object_store = object_store
        self._catalog = catalog
        self._random_bits = random_bits

    def register_document(self, source_key: SourceKey, *, now: datetime) -> LogicalDocument:
        """Register one exact source key under a stable generated UUIDv7."""
        for _attempt in range(8):
            try:
                return self._catalog.register_document(
                    source_key,
                    document_id=generate_uuid7(now=now, random_bits=self._random_bits()),
                    now=now,
                )
            except DocumentConflict:
                continue
        raise DocumentConflict("document UUID generation repeatedly collided")

    def persist_source_version(
        self,
        *,
        document_id: UUID,
        source_chunks: Iterable[bytes],
        media_type: str,
        now: datetime,
        references: tuple[ObjectReference, ...] = (),
        source_modified_at: datetime | None = None,
    ) -> DocumentVersion:
        """Publish and verify every object before committing one immutable version."""
        source = self._object_store.put_chunks(source_chunks)
        verified_source = self._object_store.verify(
            source.object_id,
            expected_length=source.byte_length,
        )
        for reference in references:
            self._object_store.verify(
                reference.object_id,
                expected_length=reference.byte_length,
            )
        return self._catalog.commit_source_version(
            SourceVersionCommit(
                document_id=document_id,
                version_id=verified_source.object_id,
                source=verified_source,
                media_type=media_type,
                source_modified_at=source_modified_at,
                references=references,
                committed_at=now,
            )
        )
