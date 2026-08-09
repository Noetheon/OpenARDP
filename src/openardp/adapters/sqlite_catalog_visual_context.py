"""Visual evidence and context-compilation persistence."""

from __future__ import annotations

import hashlib
import sqlite3
from uuid import UUID

from pydantic import ValidationError

from openardp.adapters.sqlite_catalog_base import _SQLiteCatalogBase
from openardp.adapters.sqlite_catalog_support import (
    _PDF_RENDER_PROFILE,
    _PNG_ENCODER_PROFILE,
)
from openardp.domain.context import BudgetUnit, VersionScope
from openardp.domain.context_compilation import (
    ContextCompilationCommit,
    ContextCompilationRecord,
    ContextCompilationScope,
)
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.ingestion import RepresentationScope
from openardp.domain.storage import StoredObject, decode_storage_datetime, encode_storage_datetime
from openardp.domain.visual import (
    VisualEvidenceCommit,
    VisualEvidenceDescriptor,
    VisualEvidenceRecord,
    VisualGranularity,
    VisualPageRaster,
    visual_record_fingerprint,
)
from openardp.ports.catalog import (
    CatalogError,
    ContextCompilationConflict,
    RepresentationNotFound,
    VisualCatalogConflict,
    VisualCatalogIntegrityError,
)


class _SQLiteCatalogVisualContextMixin(_SQLiteCatalogBase):
    """Visual evidence and context-compilation persistence."""

    def commit_visual_evidence(self, commit: VisualEvidenceCommit) -> VisualEvidenceRecord:
        """Atomically insert or exactly reuse one page raster and visual descriptor."""
        commit = VisualEvidenceCommit.model_validate(commit)
        descriptor = commit.descriptor
        scope = descriptor.page_raster.scope
        created_at = encode_storage_datetime(descriptor.created_at)
        record = self._visual_record(commit)
        with self._write_connection() as connection:
            rich = self._required_rich_representation(connection, scope)
            projection = next(
                (
                    item
                    for item in rich.bundle.projections
                    if item.evidence_projection_id == descriptor.evidence_projection_id
                ),
                None,
            )
            if projection is None:
                raise VisualCatalogIntegrityError(
                    "visual projection is not in the accepted rich representation"
                )
            native_object = rich.aggregate.representation.native_object
            if (
                descriptor.evidence_reference_id != projection.reference.evidence_reference_id
                or descriptor.target_anchor != projection.reference.anchor
                or descriptor.native_representation_id
                != rich.bundle.native_representation.native_representation_id
                or descriptor.trust != projection.trust
                or native_object is None
                or descriptor.page_raster.source_object != native_object
            ):
                raise VisualCatalogIntegrityError(
                    "visual descriptor disagrees with accepted rich evidence"
                )
            for value in (
                commit.page_raster.raster_object,
                commit.raster_record_object,
                commit.crop_object,
                commit.descriptor_object,
            ):
                self._register_object(connection, value, registered_at=created_at)
                self._fault_point("after_visual_object")
            try:
                connection.execute(
                    "INSERT INTO visual_page_rasters("
                    "raster_id, document_id, version_id, representation_id, page_number, "
                    "recipe_config_hash, raster_record_object_id, raster_object_id, "
                    "raster_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(raster_id) DO NOTHING",
                    (
                        commit.page_raster.raster_id,
                        str(scope.document_id),
                        scope.version_id,
                        scope.representation_id,
                        commit.page_raster.page_number,
                        commit.page_raster.recipe.config_hash,
                        commit.raster_record_object.object_id,
                        commit.page_raster.raster_object.object_id,
                        commit.page_raster.model_dump_json(),
                        created_at,
                    ),
                )
                self._fault_point("after_visual_raster")
                connection.execute(
                    "INSERT INTO visual_evidence("
                    "visual_evidence_id, document_id, version_id, representation_id, "
                    "evidence_projection_id, raster_id, descriptor_object_id, crop_object_id, "
                    "page_number, granularity, canonical_context_profile, descriptor_json, "
                    "created_at, row_fingerprint) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(visual_evidence_id) DO NOTHING",
                    (
                        record.visual_evidence_id,
                        str(scope.document_id),
                        scope.version_id,
                        scope.representation_id,
                        record.evidence_projection_id,
                        record.raster_id,
                        record.descriptor_object.object_id,
                        record.crop_object.object_id,
                        record.page_number,
                        record.granularity.value,
                        int(record.canonical_context_profile),
                        descriptor.model_dump_json(),
                        created_at,
                        record.row_fingerprint,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise VisualCatalogConflict(
                    "visual identity conflicts with persisted immutable facts"
                ) from error
            self._fault_point("after_visual_descriptor")
            persisted = self._load_visual_evidence(connection, record.visual_evidence_id)
            if persisted is None or persisted != commit:
                raise VisualCatalogConflict(
                    "visual evidence conflicts with persisted immutable facts"
                )
            self._fault_point("before_visual_commit")
            return record

    def load_visual_evidence(self, visual_evidence_id: str) -> VisualEvidenceCommit | None:
        """Load one complete verified visual commit or no result."""
        with self._read_connection() as connection:
            return self._load_visual_evidence(connection, visual_evidence_id)

    def load_visual_raster(self, raster_id: str) -> VisualPageRaster | None:
        """Load one verified page-raster record or no result."""
        with self._read_connection() as connection:
            return self._load_visual_raster(connection, raster_id)

    def list_visual_evidence(
        self,
        scope: RepresentationScope,
    ) -> tuple[VisualEvidenceRecord, ...]:
        """List one scope's verified visual records in deterministic identity order."""
        with self._read_connection() as connection:
            rows = connection.execute(
                "SELECT visual_evidence_id FROM visual_evidence WHERE document_id = ? "
                "AND version_id = ? AND representation_id = ? ORDER BY visual_evidence_id",
                (str(scope.document_id), scope.version_id, scope.representation_id),
            ).fetchall()
            records: list[VisualEvidenceRecord] = []
            for row in rows:
                commit = self._load_visual_evidence(
                    connection,
                    str(row["visual_evidence_id"]),
                )
                if commit is None:
                    raise VisualCatalogIntegrityError("visual row vanished during listing")
                records.append(self._visual_record(commit))
            return tuple(records)

    def _load_visual_raster(
        self,
        connection: sqlite3.Connection,
        raster_id: str,
    ) -> VisualPageRaster | None:
        row = connection.execute(
            "SELECT * FROM visual_page_rasters WHERE raster_id = ?",
            (raster_id,),
        ).fetchone()
        if row is None:
            return None
        try:
            raster = VisualPageRaster.model_validate_json(str(row["raster_json"]), strict=True)
            record_object = self._catalog_object(
                connection,
                str(row["raster_record_object_id"]),
            )
            raster_object = self._catalog_object(connection, str(row["raster_object_id"]))
            if (
                raster.raster_id != str(row["raster_id"])
                or raster.scope
                != RepresentationScope(
                    document_id=UUID(str(row["document_id"])),
                    version_id=str(row["version_id"]),
                    representation_id=str(row["representation_id"]),
                )
                or raster.page_number != int(row["page_number"])
                or raster.recipe.config_hash != str(row["recipe_config_hash"])
                or raster.raster_object != raster_object
                or self._canonical_model_object(raster) != record_object
            ):
                raise ValueError("visual raster row drifted")
            return raster
        except (ValidationError, ValueError) as error:
            raise VisualCatalogIntegrityError("stored visual raster is invalid") from error

    def _load_visual_evidence(
        self,
        connection: sqlite3.Connection,
        visual_evidence_id: str,
    ) -> VisualEvidenceCommit | None:
        row = connection.execute(
            "SELECT * FROM visual_evidence WHERE visual_evidence_id = ?",
            (visual_evidence_id,),
        ).fetchone()
        if row is None:
            return None
        try:
            descriptor = VisualEvidenceDescriptor.model_validate_json(
                str(row["descriptor_json"]),
                strict=True,
            )
            raster = self._load_visual_raster(connection, str(row["raster_id"]))
            if raster is None:
                raise ValueError("visual raster is missing")
            commit = VisualEvidenceCommit(
                page_raster=raster,
                descriptor=descriptor,
                raster_record_object=self._catalog_object(
                    connection,
                    str(
                        connection.execute(
                            "SELECT raster_record_object_id FROM visual_page_rasters "
                            "WHERE raster_id = ?",
                            (raster.raster_id,),
                        ).fetchone()[0]
                    ),
                ),
                descriptor_object=self._catalog_object(
                    connection,
                    str(row["descriptor_object_id"]),
                ),
                crop_object=self._catalog_object(connection, str(row["crop_object_id"])),
            )
            record = self._visual_record(commit)
            if (
                record.visual_evidence_id != str(row["visual_evidence_id"])
                or record.scope.document_id != UUID(str(row["document_id"]))
                or record.scope.version_id != str(row["version_id"])
                or record.scope.representation_id != str(row["representation_id"])
                or record.evidence_projection_id != str(row["evidence_projection_id"])
                or record.page_number != int(row["page_number"])
                or record.granularity is not VisualGranularity(str(row["granularity"]))
                or record.canonical_context_profile != bool(int(row["canonical_context_profile"]))
                or record.row_fingerprint != str(row["row_fingerprint"])
            ):
                raise ValueError("visual descriptor row drifted")
            return commit
        except (ValidationError, ValueError, TypeError, IndexError) as error:
            raise VisualCatalogIntegrityError("stored visual evidence is invalid") from error

    @staticmethod
    def _visual_record(commit: VisualEvidenceCommit) -> VisualEvidenceRecord:
        descriptor = commit.descriptor
        recipe = descriptor.recipe
        canonical_profile = (
            recipe.renderer.name == "pypdfium2"
            and recipe.renderer.version == "5.12.1"
            and recipe.renderer.profile is not None
            and _PDF_RENDER_PROFILE.fullmatch(recipe.renderer.profile) is not None
            and recipe.encoder.name == "Pillow"
            and recipe.encoder.version == "12.3.0"
            and recipe.encoder.profile is not None
            and _PNG_ENCODER_PROFILE.fullmatch(recipe.encoder.profile) is not None
            and recipe.scale_numerator == 2
            and recipe.scale_denominator == 1
        )
        unvalidated = VisualEvidenceRecord.model_construct(
            visual_evidence_id=descriptor.visual_evidence_id,
            scope=descriptor.page_raster.scope,
            evidence_projection_id=descriptor.evidence_projection_id,
            raster_id=descriptor.page_raster.raster_id,
            raster_record_object=commit.raster_record_object,
            descriptor_object=commit.descriptor_object,
            crop_object=commit.crop_object,
            page_number=descriptor.page_raster.page_number,
            granularity=descriptor.resolved_region.granularity,
            canonical_context_profile=canonical_profile,
            created_at=descriptor.created_at,
            row_fingerprint="sha256:" + "0" * 64,
        )
        return VisualEvidenceRecord(
            visual_evidence_id=descriptor.visual_evidence_id,
            scope=descriptor.page_raster.scope,
            evidence_projection_id=descriptor.evidence_projection_id,
            raster_id=descriptor.page_raster.raster_id,
            raster_record_object=commit.raster_record_object,
            descriptor_object=commit.descriptor_object,
            crop_object=commit.crop_object,
            page_number=descriptor.page_raster.page_number,
            granularity=descriptor.resolved_region.granularity,
            canonical_context_profile=canonical_profile,
            created_at=descriptor.created_at,
            row_fingerprint=visual_record_fingerprint(unvalidated),
        )

    @staticmethod
    def _canonical_model_object(model: VisualPageRaster) -> StoredObject:
        payload = canonical_json_bytes(model.model_dump(mode="json"))
        return StoredObject(
            object_id="sha256:" + hashlib.sha256(payload).hexdigest(),
            byte_length=len(payload),
        )

    @staticmethod
    def _catalog_object(connection: sqlite3.Connection, object_id: str) -> StoredObject:
        row = connection.execute(
            "SELECT byte_length FROM objects WHERE object_id = ?",
            (object_id,),
        ).fetchone()
        if row is None:
            raise VisualCatalogIntegrityError("visual object metadata is missing")
        return StoredObject(object_id=object_id, byte_length=int(row["byte_length"]))

    def commit_context_compilation(
        self,
        commit: ContextCompilationCommit,
    ) -> ContextCompilationRecord:
        """Atomically insert or exactly reuse one compilation and its scope rows."""
        record = commit.record
        created_at = encode_storage_datetime(record.created_at)
        with self._write_connection() as connection:
            self._register_object(connection, record.receipt_object, registered_at=created_at)
            self._register_object(connection, record.bundle_object, registered_at=created_at)
            for scope in commit.scopes:
                root = connection.execute(
                    "SELECT 1 FROM document_representations "
                    "WHERE document_id = ? AND version_id = ? AND representation_id = ?",
                    (
                        str(scope.scope.document_id),
                        scope.scope.version_id,
                        scope.scope.representation_id,
                    ),
                ).fetchone()
                if root is None:
                    raise RepresentationNotFound(
                        "compilation scope root is not a persisted representation"
                    )
            connection.execute(
                "INSERT INTO context_compilations("
                "receipt_id, receipt_object_id, receipt_byte_length, bundle_object_id, "
                "bundle_byte_length, bundle_id, task_digest, algorithm_name, "
                "algorithm_version, algorithm_config_hash, estimator_name, "
                "estimator_version, estimator_unit, estimator_config_hash, policy_digest, "
                "budget_limit, budget_unit, created_at, selected_count, omitted_count, "
                "rejected_count, stale_count, row_fingerprint) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(receipt_id) DO NOTHING",
                self._compilation_row_values(record, created_at),
            )
            for scope in commit.scopes:
                connection.execute(
                    "INSERT INTO context_compilation_scopes("
                    "receipt_id, ordinal, document_id, version_id, representation_id) "
                    "VALUES (?, ?, ?, ?, ?) ON CONFLICT(receipt_id, ordinal) DO NOTHING",
                    (
                        record.receipt_id,
                        scope.ordinal,
                        str(scope.scope.document_id),
                        scope.scope.version_id,
                        scope.scope.representation_id,
                    ),
                )
            persisted = self._load_context_compilation(connection, record.receipt_id)
            if persisted is None:
                raise CatalogError("context compilation insert did not persist")
            if persisted != commit:
                raise ContextCompilationConflict(
                    "context compilation conflicts with the persisted immutable record"
                )
            return persisted.record

    def load_context_compilation(
        self,
        receipt_id: str,
    ) -> ContextCompilationCommit | None:
        """Return one body-free compilation aggregate from a single snapshot."""
        with self._read_connection() as connection:
            return self._load_context_compilation(connection, receipt_id)

    def list_context_compilations(self) -> tuple[ContextCompilationRecord, ...]:
        """Return immutable compilation rows in deterministic identity order."""
        with self._read_connection() as connection:
            rows = connection.execute(
                "SELECT receipt_id FROM context_compilations ORDER BY receipt_id"
            ).fetchall()
            records: list[ContextCompilationRecord] = []
            for row in rows:
                commit = self._load_context_compilation(connection, str(row["receipt_id"]))
                if commit is None:
                    raise CatalogError("context compilation row vanished during listing")
                records.append(commit.record)
            return tuple(records)

    def _load_context_compilation(
        self,
        connection: sqlite3.Connection,
        receipt_id: str,
    ) -> ContextCompilationCommit | None:
        row = connection.execute(
            "SELECT * FROM context_compilations WHERE receipt_id = ?",
            (receipt_id,),
        ).fetchone()
        if row is None:
            return None
        scope_rows = connection.execute(
            "SELECT * FROM context_compilation_scopes WHERE receipt_id = ? ORDER BY ordinal",
            (receipt_id,),
        ).fetchall()
        try:
            record = ContextCompilationRecord.model_validate(
                {
                    "receipt_id": str(row["receipt_id"]),
                    "receipt_object": {
                        "object_id": str(row["receipt_object_id"]),
                        "byte_length": int(row["receipt_byte_length"]),
                    },
                    "bundle_object": {
                        "object_id": str(row["bundle_object_id"]),
                        "byte_length": int(row["bundle_byte_length"]),
                    },
                    "bundle_id": UUID(str(row["bundle_id"])),
                    "task_digest": str(row["task_digest"]),
                    "algorithm": {
                        "name": str(row["algorithm_name"]),
                        "version": str(row["algorithm_version"]),
                        "config_hash": str(row["algorithm_config_hash"]),
                    },
                    "estimator": {
                        "name": str(row["estimator_name"]),
                        "version": str(row["estimator_version"]),
                        "unit": BudgetUnit(str(row["estimator_unit"])),
                        "config_hash": str(row["estimator_config_hash"]),
                    },
                    "policy_digest": str(row["policy_digest"]),
                    "budget_limit": int(row["budget_limit"]),
                    "budget_unit": BudgetUnit(str(row["budget_unit"])),
                    "created_at": decode_storage_datetime(str(row["created_at"])),
                    "selected_count": int(row["selected_count"]),
                    "omitted_count": int(row["omitted_count"]),
                    "rejected_count": int(row["rejected_count"]),
                    "stale_count": int(row["stale_count"]),
                    "row_fingerprint": str(row["row_fingerprint"]),
                }
            )
            commit = ContextCompilationCommit(
                record=record,
                scopes=tuple(
                    ContextCompilationScope(
                        receipt_id=str(scope_row["receipt_id"]),
                        ordinal=int(scope_row["ordinal"]),
                        scope=VersionScope(
                            document_id=UUID(str(scope_row["document_id"])),
                            version_id=str(scope_row["version_id"]),
                            representation_id=str(scope_row["representation_id"]),
                        ),
                    )
                    for scope_row in scope_rows
                ),
            )
        except (ValidationError, ValueError) as error:
            raise CatalogError("context compilation rows failed integrity validation") from error
        return commit

    @staticmethod
    def _compilation_row_values(
        record: ContextCompilationRecord,
        created_at: str,
    ) -> tuple[object, ...]:
        return (
            record.receipt_id,
            record.receipt_object.object_id,
            record.receipt_object.byte_length,
            record.bundle_object.object_id,
            record.bundle_object.byte_length,
            str(record.bundle_id),
            record.task_digest,
            record.algorithm.name,
            record.algorithm.version,
            record.algorithm.config_hash,
            record.estimator.name,
            record.estimator.version,
            record.estimator.unit.value,
            record.estimator.config_hash,
            record.policy_digest,
            record.budget_limit,
            record.budget_unit.value,
            created_at,
            record.selected_count,
            record.omitted_count,
            record.rejected_count,
            record.stale_count,
            record.row_fingerprint,
        )


__all__ = ["_SQLiteCatalogVisualContextMixin"]
