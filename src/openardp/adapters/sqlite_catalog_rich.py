"""Provider-native rich-attempt persistence."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from uuid import UUID

from openardp.adapters.sqlite_catalog_base import _SQLiteCatalogBase
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.ingestion import IngestionDisposition, IngestionEvent, RepresentationScope
from openardp.domain.rich_ingestion import (
    ReadyRichRepresentationCommit,
    RichAttemptAppendResult,
    RichAttemptCommit,
    RichAttemptOutcome,
    RichEvidenceBundle,
    RichParseAttempt,
    RichRepresentationArtifacts,
    RichRepresentationCommitResult,
)
from openardp.domain.storage import encode_storage_datetime
from openardp.ports.catalog import (
    RepresentationConflict,
    RepresentationIncomplete,
    RepresentationIntegrityError,
)


class _SQLiteCatalogRichMixin(_SQLiteCatalogBase):
    """Provider-native rich-attempt persistence."""

    def commit_ready_rich_representation(
        self,
        commit: ReadyRichRepresentationCommit,
        *,
        owner_id: str,
        lease_token: str,
        expected_revision: int,
        disposition: IngestionDisposition,
    ) -> RichRepresentationCommitResult:
        """Atomically publish one base READY aggregate and its canonical rich attempt."""
        with self._write_connection() as connection:
            base_result = self.commit_ready_representation(
                commit.base,
                owner_id=owner_id,
                lease_token=lease_token,
                expected_revision=expected_revision,
                disposition=disposition,
                _connection=connection,
            )
            self._persist_rich_attempt(
                connection,
                commit.rich,
                event_sequence=base_result.event.sequence,
            )
            accepted = connection.execute(
                "SELECT accepted_attempt_id FROM rich_accepted_representations "
                "WHERE document_id = ? AND version_id = ? AND representation_id = ?",
                (
                    str(commit.base.scope.document_id),
                    commit.base.scope.version_id,
                    commit.base.scope.representation_id,
                ),
            ).fetchone()
            if accepted is None:
                connection.execute(
                    "INSERT INTO rich_accepted_representations("
                    "document_id, version_id, representation_id, accepted_attempt_id) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        str(commit.base.scope.document_id),
                        commit.base.scope.version_id,
                        commit.base.scope.representation_id,
                        str(commit.rich.attempt.attempt_id),
                    ),
                )
            elif str(accepted["accepted_attempt_id"]) != str(commit.rich.attempt.attempt_id):
                raise RepresentationConflict("accepted rich attempt differs from candidate")
            artifacts = self._required_rich_representation(connection, commit.base.scope)
            if (
                artifacts.accepted_attempt != commit.rich.attempt
                or artifacts.bundle != commit.rich.bundle
            ):
                raise RepresentationIntegrityError("rich representation verification failed")
            self._fault_point("before_rich_representation_commit")
            return RichRepresentationCommitResult(
                artifacts=artifacts,
                head=base_result.head,
                event=base_result.event,
            )

    def append_rich_attempt(
        self,
        commit: RichAttemptCommit,
        *,
        source_observed_at: datetime,
        occurred_at: datetime,
    ) -> RichAttemptAppendResult:
        """Atomically retain one non-canonical attempt without replacing accepted data."""
        if commit.attempt.outcome is RichAttemptOutcome.CANONICAL:
            raise RepresentationConflict("appended rich attempt cannot be canonical")
        observed_text = encode_storage_datetime(source_observed_at)
        occurred_text = encode_storage_datetime(occurred_at)
        with self._write_connection() as connection:
            accepted = self._required_accepted_attempt_id(connection, commit.attempt.scope)
            existing = self._load_rich_attempt_commit(
                connection,
                commit.attempt.attempt_id,
            )
            if existing is not None:
                if existing != commit:
                    raise RepresentationConflict("rich attempt identity has conflicting facts")
                event = self._rich_attempt_event(connection, commit.attempt.attempt_id)
                return RichAttemptAppendResult(
                    attempt=existing.attempt,
                    accepted_attempt_id=accepted,
                    event=event,
                )

            if commit.attempt.outcome is RichAttemptOutcome.CONVERGED:
                _head, event = self._advance_head_and_event(
                    connection,
                    commit.attempt.scope,
                    source_observed_at=observed_text,
                    ingested_at=occurred_text,
                    disposition=IngestionDisposition.CONVERGED,
                    parser_invoked=True,
                )
            else:
                event = self._append_ingestion_event_without_head(
                    connection,
                    commit.attempt.scope,
                    source_observed_at=observed_text,
                    ingested_at=occurred_text,
                    disposition=IngestionDisposition.FORCED_REPARSE,
                )
            self._persist_rich_attempt(
                connection,
                commit,
                event_sequence=event.sequence,
            )
            self._fault_point("before_rich_attempt_commit")
            return RichAttemptAppendResult(
                attempt=commit.attempt,
                accepted_attempt_id=accepted,
                event=event,
            )

    def load_rich_representation(
        self,
        scope: RepresentationScope,
    ) -> RichRepresentationArtifacts | None:
        """Load one accepted rich aggregate from a single read snapshot."""
        with self._read_connection() as connection:
            return self._rich_representation(connection, scope)

    def get_rich_attempt(self, attempt_id: UUID) -> RichParseAttempt | None:
        """Return one append-only rich attempt or no result."""
        with self._read_connection() as connection:
            commit = self._load_rich_attempt_commit(connection, attempt_id)
            return commit.attempt if commit is not None else None

    def list_rich_attempts(
        self,
        scope: RepresentationScope,
    ) -> tuple[RichParseAttempt, ...]:
        """Return one scope's immutable attempts in deterministic creation order."""
        with self._read_connection() as connection:
            rows = connection.execute(
                "SELECT attempt_json FROM rich_parse_attempts WHERE document_id = ? "
                "AND version_id = ? AND representation_id = ? "
                "ORDER BY created_at, attempt_id",
                (str(scope.document_id), scope.version_id, scope.representation_id),
            ).fetchall()
            try:
                return tuple(
                    RichParseAttempt.model_validate_json(str(row["attempt_json"])) for row in rows
                )
            except ValueError as error:
                raise RepresentationIntegrityError("rich attempt metadata is invalid") from error

    def _persist_rich_attempt(
        self,
        connection: sqlite3.Connection,
        commit: RichAttemptCommit,
        *,
        event_sequence: int,
    ) -> None:
        existing = self._load_rich_attempt_commit(connection, commit.attempt.attempt_id)
        if existing is not None:
            if existing != commit:
                raise RepresentationConflict("rich attempt identity has conflicting facts")
            existing_event = self._rich_attempt_event(connection, commit.attempt.attempt_id)
            if existing_event.sequence != event_sequence:
                raise RepresentationConflict("rich attempt event differs from candidate")
            return

        created_at = encode_storage_datetime(commit.attempt.created_at)
        objects = (
            commit.attempt.descriptor_object,
            commit.attempt.provider_native_object,
            commit.attempt.native_record_object,
            commit.attempt.evidence_bundle_object,
            *(
                value
                for record in commit.bundle.records
                for value in (
                    record.reference_object,
                    record.projection_object,
                    record.retrieval_object,
                )
            ),
        )
        for value in objects:
            self._register_object(connection, value, registered_at=created_at)
        self._fault_point("after_rich_objects")

        attempt_json = canonical_json_bytes(commit.attempt.model_dump(mode="json")).decode("utf-8")
        bundle_json = commit.bundle.canonical_bytes.decode("utf-8")
        attempt = commit.attempt
        connection.execute(
            "INSERT INTO rich_parse_attempts("
            "attempt_id, document_id, version_id, representation_id, outcome, "
            "descriptor_object_id, provider_native_object_id, native_record_object_id, "
            "evidence_bundle_object_id, projection_count, attempt_json, bundle_json, "
            "event_sequence, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(attempt.attempt_id),
                str(attempt.scope.document_id),
                attempt.scope.version_id,
                attempt.scope.representation_id,
                attempt.outcome.value,
                attempt.descriptor_object.object_id,
                attempt.provider_native_object.object_id,
                attempt.native_record_object.object_id,
                attempt.evidence_bundle_object.object_id,
                attempt.projection_count,
                attempt_json,
                bundle_json,
                event_sequence,
                created_at,
            ),
        )
        for record in commit.bundle.records:
            connection.execute(
                "INSERT INTO rich_attempt_evidence("
                "attempt_id, ordinal, reference_object_id, projection_object_id, "
                "retrieval_object_id) VALUES (?, ?, ?, ?, ?)",
                (
                    str(attempt.attempt_id),
                    record.ordinal,
                    record.reference_object.object_id,
                    record.projection_object.object_id,
                    record.retrieval_object.object_id,
                ),
            )
            self._fault_point("after_rich_evidence")

    def _load_rich_attempt_commit(
        self,
        connection: sqlite3.Connection,
        attempt_id: UUID,
    ) -> RichAttemptCommit | None:
        row = connection.execute(
            "SELECT * FROM rich_parse_attempts WHERE attempt_id = ?",
            (str(attempt_id),),
        ).fetchone()
        if row is None:
            return None
        try:
            commit = RichAttemptCommit(
                attempt=RichParseAttempt.model_validate_json(str(row["attempt_json"])),
                bundle=RichEvidenceBundle.model_validate_json(str(row["bundle_json"])),
            )
        except ValueError as error:
            raise RepresentationIntegrityError("rich attempt metadata is invalid") from error
        attempt = commit.attempt
        expected_row = (
            str(attempt.attempt_id),
            str(attempt.scope.document_id),
            attempt.scope.version_id,
            attempt.scope.representation_id,
            attempt.outcome.value,
            attempt.descriptor_object.object_id,
            attempt.provider_native_object.object_id,
            attempt.native_record_object.object_id,
            attempt.evidence_bundle_object.object_id,
            attempt.projection_count,
            encode_storage_datetime(attempt.created_at),
        )
        observed_row = (
            str(row["attempt_id"]),
            str(row["document_id"]),
            str(row["version_id"]),
            str(row["representation_id"]),
            str(row["outcome"]),
            str(row["descriptor_object_id"]),
            str(row["provider_native_object_id"]),
            str(row["native_record_object_id"]),
            str(row["evidence_bundle_object_id"]),
            int(row["projection_count"]),
            str(row["created_at"]),
        )
        if (
            observed_row != expected_row
            or str(row["attempt_json"]).encode("utf-8")
            != canonical_json_bytes(attempt.model_dump(mode="json"))
            or str(row["bundle_json"]).encode("utf-8") != commit.bundle.canonical_bytes
        ):
            raise RepresentationIntegrityError("rich attempt catalog facts are inconsistent")
        evidence = connection.execute(
            "SELECT ordinal, reference_object_id, projection_object_id, retrieval_object_id "
            "FROM rich_attempt_evidence WHERE attempt_id = ? ORDER BY ordinal",
            (str(attempt_id),),
        ).fetchall()
        expected = tuple(
            (
                record.ordinal,
                record.reference_object.object_id,
                record.projection_object.object_id,
                record.retrieval_object.object_id,
            )
            for record in commit.bundle.records
        )
        observed = tuple(
            (
                int(item["ordinal"]),
                str(item["reference_object_id"]),
                str(item["projection_object_id"]),
                str(item["retrieval_object_id"]),
            )
            for item in evidence
        )
        if observed != expected:
            raise RepresentationIntegrityError("rich attempt evidence inventory is incomplete")
        return commit

    def _rich_representation(
        self,
        connection: sqlite3.Connection,
        scope: RepresentationScope,
    ) -> RichRepresentationArtifacts | None:
        row = connection.execute(
            "SELECT accepted_attempt_id FROM rich_accepted_representations "
            "WHERE document_id = ? AND version_id = ? AND representation_id = ?",
            (str(scope.document_id), scope.version_id, scope.representation_id),
        ).fetchone()
        if row is None:
            return None
        accepted_id = UUID(str(row["accepted_attempt_id"]))
        commit = self._load_rich_attempt_commit(connection, accepted_id)
        if commit is None:
            raise RepresentationIntegrityError("accepted rich attempt is missing")
        aggregate = self._required_representation(connection, scope)
        try:
            return RichRepresentationArtifacts(
                aggregate=aggregate,
                accepted_attempt_id=accepted_id,
                accepted_attempt=commit.attempt,
                bundle=commit.bundle,
            )
        except ValueError as error:
            raise RepresentationIntegrityError(
                "accepted rich representation is inconsistent"
            ) from error

    def _required_rich_representation(
        self,
        connection: sqlite3.Connection,
        scope: RepresentationScope,
    ) -> RichRepresentationArtifacts:
        artifacts = self._rich_representation(connection, scope)
        if artifacts is None:
            raise RepresentationIncomplete("rich representation is not complete")
        return artifacts

    def _required_accepted_attempt_id(
        self,
        connection: sqlite3.Connection,
        scope: RepresentationScope,
    ) -> UUID:
        row = connection.execute(
            "SELECT accepted_attempt_id FROM rich_accepted_representations "
            "WHERE document_id = ? AND version_id = ? AND representation_id = ?",
            (str(scope.document_id), scope.version_id, scope.representation_id),
        ).fetchone()
        if row is None:
            raise RepresentationIncomplete("accepted rich attempt does not exist")
        return UUID(str(row["accepted_attempt_id"]))

    def _rich_attempt_event(
        self,
        connection: sqlite3.Connection,
        attempt_id: UUID,
    ) -> IngestionEvent:
        row = connection.execute(
            "SELECT e.* FROM rich_parse_attempts AS a "
            "JOIN ingestion_events AS e ON e.document_id = a.document_id "
            "AND e.sequence = a.event_sequence WHERE a.attempt_id = ?",
            (str(attempt_id),),
        ).fetchone()
        if row is None:
            raise RepresentationIntegrityError("rich attempt event is missing")
        return self._ingestion_event_from_row(row)


__all__ = ["_SQLiteCatalogRichMixin"]
