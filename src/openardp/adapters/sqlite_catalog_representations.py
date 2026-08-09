"""Text representation, head, and ingestion-event persistence."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from typing import cast
from uuid import UUID

from pydantic import SecretStr

from openardp.adapters.sqlite_catalog_base import _SQLiteCatalogBase
from openardp.adapters.sqlite_catalog_support import (
    _MIN_LEASE_TOKEN_LENGTH,
    _OWNER,
)
from openardp.domain.block import BlockKind
from openardp.domain.ingestion import (
    DocumentHead,
    DocumentHeadUpdate,
    DocumentRepresentation,
    IngestionDisposition,
    IngestionEvent,
    ParserRecipe,
    ReadyRepresentationCommit,
    RepresentationAcquireDisposition,
    RepresentationAcquireResult,
    RepresentationAggregate,
    RepresentationBlock,
    RepresentationCommitResult,
    RepresentationLease,
    RepresentationScope,
    RepresentationState,
)
from openardp.domain.search import SearchIndexEntry, block_text_for_index, indexed_text_hash
from openardp.domain.storage import StoredObject, decode_storage_datetime, encode_storage_datetime
from openardp.ports.catalog import (
    CatalogError,
    RepresentationConflict,
    RepresentationIncomplete,
    RepresentationIntegrityError,
    RepresentationLeaseConflict,
    RepresentationNotFound,
)


class _SQLiteCatalogRepresentationMixin(_SQLiteCatalogBase):
    """Text representation, head, and ingestion-event persistence."""

    def acquire_representation(
        self,
        scope: RepresentationScope,
        recipe: ParserRecipe,
        *,
        owner_id: str,
        lease_token: str,
        now: datetime,
        lease_until: datetime,
    ) -> RepresentationAcquireResult:
        """Claim, reuse or report busy work for one immutable representation scope."""
        self._validate_representation_identity(scope, recipe)
        self._validate_representation_owner(owner_id)
        token_hash = self._representation_token_hash(lease_token)
        now_text = encode_storage_datetime(now)
        lease_text = encode_storage_datetime(lease_until)
        if lease_text <= now_text:
            raise RepresentationLeaseConflict("representation lease must extend beyond now")
        with self._write_connection() as connection:
            if self._load_version(connection, scope.document_id, scope.version_id) is None:
                raise RepresentationNotFound("representation source version does not exist")
            row = self._load_representation_row(connection, scope)
            if row is None:
                connection.execute(
                    "INSERT INTO document_representations("
                    "document_id, version_id, representation_id, parser_name, parser_version, "
                    "parser_profile, parser_config_hash, normalization_schema_version, state, "
                    "attempt_count, revision, active_owner_id, active_lease_token_hash, "
                    "lease_expires_at, last_transition_token_hash, last_failure_code, "
                    "manifest_object_id, native_object_id, block_count, warning_codes_json, "
                    "created_at, updated_at, ready_at) VALUES ("
                    "?, ?, ?, ?, ?, ?, ?, ?, 'STAGING', 1, 1, ?, ?, ?, NULL, NULL, NULL, "
                    "NULL, 0, '[]', ?, ?, NULL)",
                    (
                        str(scope.document_id),
                        scope.version_id,
                        scope.representation_id,
                        recipe.name,
                        recipe.version,
                        recipe.profile,
                        recipe.config_hash,
                        recipe.normalization_schema_version,
                        owner_id,
                        token_hash,
                        lease_text,
                        now_text,
                        now_text,
                    ),
                )
                connection.execute(
                    "INSERT INTO representation_scopes("
                    "document_id, version_id, representation_id) VALUES (?, ?, ?)",
                    (str(scope.document_id), scope.version_id, scope.representation_id),
                )
                representation = self._required_representation(connection, scope).representation
                lease = RepresentationLease(
                    representation=representation,
                    lease_token=SecretStr(lease_token),
                )
                return RepresentationAcquireResult(
                    disposition=RepresentationAcquireDisposition.CLAIMED,
                    representation=representation,
                    lease=lease,
                )

            self._assert_row_recipe(row, recipe)
            representation = self._representation_from_row(row)
            if representation.state is RepresentationState.READY:
                return RepresentationAcquireResult(
                    disposition=RepresentationAcquireDisposition.READY,
                    representation=representation,
                )
            if (
                representation.state is RepresentationState.STAGING
                and str(row["lease_expires_at"]) > now_text
            ):
                if (
                    row["active_owner_id"] == owner_id
                    and row["active_lease_token_hash"] == token_hash
                ):
                    lease = RepresentationLease(
                        representation=representation,
                        lease_token=SecretStr(lease_token),
                    )
                    return RepresentationAcquireResult(
                        disposition=RepresentationAcquireDisposition.CLAIMED,
                        representation=representation,
                        lease=lease,
                    )
                return RepresentationAcquireResult(
                    disposition=RepresentationAcquireDisposition.BUSY,
                    representation=representation,
                )
            if now_text < str(row["updated_at"]):
                raise RepresentationLeaseConflict("representation transition time regressed")
            connection.execute(
                "UPDATE document_representations SET state = 'STAGING', "
                "attempt_count = attempt_count + 1, revision = revision + 1, "
                "active_owner_id = ?, active_lease_token_hash = ?, lease_expires_at = ?, "
                "last_transition_token_hash = NULL, last_failure_code = NULL, "
                "manifest_object_id = NULL, native_object_id = NULL, block_count = 0, "
                "warning_codes_json = '[]', updated_at = ?, ready_at = NULL "
                "WHERE document_id = ? AND version_id = ? AND representation_id = ?",
                (
                    owner_id,
                    token_hash,
                    lease_text,
                    now_text,
                    str(scope.document_id),
                    scope.version_id,
                    scope.representation_id,
                ),
            )
            taken = self._required_representation(connection, scope).representation
            lease = RepresentationLease(
                representation=taken,
                lease_token=SecretStr(lease_token),
            )
            return RepresentationAcquireResult(
                disposition=RepresentationAcquireDisposition.CLAIMED,
                representation=taken,
                lease=lease,
            )

    def renew_representation(
        self,
        scope: RepresentationScope,
        *,
        owner_id: str,
        lease_token: str,
        expected_revision: int,
        now: datetime,
        lease_until: datetime,
    ) -> RepresentationLease:
        """Renew one active representation claim through compare-and-set fencing."""
        self._validate_representation_owner(owner_id)
        token_hash = self._representation_token_hash(lease_token)
        now_text = encode_storage_datetime(now)
        lease_text = encode_storage_datetime(lease_until)
        if lease_text <= now_text:
            raise RepresentationLeaseConflict("representation lease must extend beyond now")
        with self._write_connection() as connection:
            row = self._required_representation_row(connection, scope)
            self._assert_representation_lease(
                row,
                owner_id=owner_id,
                token_hash=token_hash,
                expected_revision=expected_revision,
                now_text=now_text,
            )
            if now_text < str(row["updated_at"]):
                raise RepresentationLeaseConflict("representation transition time regressed")
            connection.execute(
                "UPDATE document_representations SET revision = revision + 1, "
                "lease_expires_at = ?, updated_at = ? WHERE document_id = ? AND "
                "version_id = ? AND representation_id = ? AND revision = ? AND state = 'STAGING'",
                (
                    lease_text,
                    now_text,
                    str(scope.document_id),
                    scope.version_id,
                    scope.representation_id,
                    expected_revision,
                ),
            )
            renewed = self._required_representation(connection, scope).representation
            return RepresentationLease(
                representation=renewed,
                lease_token=SecretStr(lease_token),
            )

    def fail_representation(
        self,
        scope: RepresentationScope,
        *,
        owner_id: str,
        lease_token: str,
        expected_revision: int,
        now: datetime,
        failure_code: str,
    ) -> RepresentationAggregate:
        """Persist one body-free FAILED outcome through fencing proof."""
        self._validate_representation_owner(owner_id)
        self._validate_failure_code(failure_code)
        token_hash = self._representation_token_hash(lease_token)
        now_text = encode_storage_datetime(now)
        with self._write_connection() as connection:
            row = self._required_representation_row(connection, scope)
            if row["state"] == RepresentationState.FAILED.value:
                if (
                    row["last_transition_token_hash"] == token_hash
                    and row["last_failure_code"] == failure_code
                ):
                    return self._required_representation(connection, scope)
                raise RepresentationLeaseConflict("failed representation token does not match")
            self._assert_representation_lease(
                row,
                owner_id=owner_id,
                token_hash=token_hash,
                expected_revision=expected_revision,
                now_text=now_text,
            )
            if now_text < str(row["updated_at"]):
                raise RepresentationLeaseConflict("representation transition time regressed")
            connection.execute(
                "UPDATE document_representations SET state = 'FAILED', revision = revision + 1, "
                "active_owner_id = NULL, active_lease_token_hash = NULL, lease_expires_at = NULL, "
                "last_transition_token_hash = ?, last_failure_code = ?, updated_at = ? "
                "WHERE document_id = ? AND version_id = ? AND representation_id = ? "
                "AND revision = ? AND state = 'STAGING'",
                (
                    token_hash,
                    failure_code,
                    now_text,
                    str(scope.document_id),
                    scope.version_id,
                    scope.representation_id,
                    expected_revision,
                ),
            )
            return self._required_representation(connection, scope)

    def commit_ready_representation(
        self,
        commit: ReadyRepresentationCommit,
        *,
        owner_id: str | None,
        lease_token: str | None,
        expected_revision: int | None,
        disposition: IngestionDisposition,
        _connection: sqlite3.Connection | None = None,
    ) -> RepresentationCommitResult:
        """Atomically publish one complete READY aggregate, head and ingest event."""
        if disposition is IngestionDisposition.CACHE_HIT:
            raise RepresentationConflict("ready commit cannot be a cache hit")
        now_text = encode_storage_datetime(commit.ready_at)
        observed_text = encode_storage_datetime(commit.source_observed_at)
        with self._optional_write_connection(_connection) as connection:
            row = self._required_representation_row(connection, commit.scope)
            self._assert_row_recipe(row, commit.recipe)
            existing = self._required_representation(connection, commit.scope)
            token_hash = (
                self._representation_token_hash(lease_token) if lease_token is not None else None
            )
            if existing.representation.state is RepresentationState.READY:
                if not self._ready_aggregate_matches(existing, commit):
                    raise RepresentationConflict("ready representation differs from candidate")
                if owner_id is not None or expected_revision is not None:
                    if token_hash is None or row["last_transition_token_hash"] != token_hash:
                        raise RepresentationLeaseConflict(
                            "ready representation fencing token does not match"
                        )
                    event = self._last_scope_event(connection, commit.scope)
                    head = self._required_document_head(connection, commit.scope.document_id)
                    return RepresentationCommitResult(
                        aggregate=existing,
                        head=head,
                        event=event,
                    )
                if disposition is not IngestionDisposition.FORCED_REPARSE:
                    raise RepresentationConflict(
                        "forced identical output must use FORCED_REPARSE disposition"
                    )
                head, event = self._advance_head_and_event(
                    connection,
                    commit.scope,
                    source_observed_at=observed_text,
                    ingested_at=now_text,
                    disposition=disposition,
                    parser_invoked=True,
                )
                return RepresentationCommitResult(
                    aggregate=existing,
                    head=head,
                    event=event,
                )

            if owner_id is None or token_hash is None or expected_revision is None:
                raise RepresentationLeaseConflict("ready commit requires representation lease")
            self._validate_representation_owner(owner_id)
            self._assert_representation_lease(
                row,
                owner_id=owner_id,
                token_hash=token_hash,
                expected_revision=expected_revision,
                now_text=now_text,
            )
            version = self._load_version(
                connection,
                commit.scope.document_id,
                commit.scope.version_id,
            )
            if version is None or version.source != commit.native_object:
                raise RepresentationIntegrityError(
                    "native representation object does not match source version"
                )
            for value in (commit.manifest_object, commit.native_object):
                self._register_object(connection, value, registered_at=now_text)
            for item in commit.blocks:
                self._register_object(connection, item.object, registered_at=now_text)
            self._fault_point("after_representation_objects")
            for item in commit.blocks:
                connection.execute(
                    "INSERT INTO representation_blocks("
                    "scope_key, ordinal, block_id, object_id, "
                    "parent_id, kind, sibling_order, line_start, line_end) "
                    "SELECT scope_key, ?, ?, ?, ?, ?, ?, ?, ? FROM representation_scopes "
                    "WHERE document_id = ? AND version_id = ? AND representation_id = ?",
                    (
                        item.ordinal,
                        str(item.block.block_id),
                        item.object.object_id,
                        str(item.block.parent_id) if item.block.parent_id is not None else None,
                        item.block.kind.value,
                        item.block.order,
                        item.line_start,
                        item.line_end,
                        str(commit.scope.document_id),
                        commit.scope.version_id,
                        commit.scope.representation_id,
                    ),
                )
                self._fault_point("after_representation_block")
            for item in commit.blocks:
                text = block_text_for_index(item.block.text)
                entry = SearchIndexEntry(
                    scope=commit.scope,
                    ordinal=item.ordinal,
                    block_id=item.block.block_id,
                    kind=item.block.kind,
                    trust_zone=item.block.trust.zone,
                    line_start=item.line_start,
                    line_end=item.line_end,
                    page=None,
                    slide=None,
                    text_hash=indexed_text_hash(text),
                    indexed_at=commit.ready_at,
                )
                self._insert_search_entry(connection, entry, text)
                self._fault_point("after_search_index_entry")
            self._fault_point("after_search_index")
            warnings_json = json.dumps(
                list(commit.warning_codes),
                ensure_ascii=False,
                separators=(",", ":"),
            )
            connection.execute(
                "UPDATE document_representations SET state = 'READY', revision = revision + 1, "
                "active_owner_id = NULL, active_lease_token_hash = NULL, lease_expires_at = NULL, "
                "last_transition_token_hash = ?, last_failure_code = NULL, "
                "manifest_object_id = ?, native_object_id = ?, block_count = ?, "
                "warning_codes_json = ?, updated_at = ?, ready_at = ? WHERE document_id = ? "
                "AND version_id = ? AND representation_id = ? AND revision = ? "
                "AND state = 'STAGING'",
                (
                    token_hash,
                    commit.manifest_object.object_id,
                    commit.native_object.object_id,
                    len(commit.blocks),
                    warnings_json,
                    now_text,
                    now_text,
                    str(commit.scope.document_id),
                    commit.scope.version_id,
                    commit.scope.representation_id,
                    expected_revision,
                ),
            )
            self._fault_point("after_representation_ready")
            aggregate = self._required_representation(connection, commit.scope)
            if not self._ready_aggregate_matches(aggregate, commit):
                raise RepresentationIntegrityError("ready representation verification failed")
            head, event = self._advance_head_and_event(
                connection,
                commit.scope,
                source_observed_at=observed_text,
                ingested_at=now_text,
                disposition=disposition,
                parser_invoked=True,
            )
            self._fault_point("before_representation_commit")
            return RepresentationCommitResult(aggregate=aggregate, head=head, event=event)

    def load_representation(
        self,
        scope: RepresentationScope,
    ) -> RepresentationAggregate | None:
        """Load one representation header and all projections from one snapshot."""
        with self._read_connection() as connection:
            row = self._load_representation_row(connection, scope)
            return self._representation_aggregate(connection, row) if row is not None else None

    def record_ready_ingest(
        self,
        scope: RepresentationScope,
        *,
        source_observed_at: datetime,
        ingested_at: datetime,
        disposition: IngestionDisposition,
    ) -> DocumentHeadUpdate:
        """Append a verified READY cache observation and update its current head."""
        if disposition is not IngestionDisposition.CACHE_HIT:
            raise RepresentationConflict("ready reuse must use CACHE_HIT disposition")
        with self._write_connection() as connection:
            aggregate = self._required_representation(connection, scope)
            if aggregate.representation.state is not RepresentationState.READY:
                raise RepresentationIncomplete("representation is not ready")
            head, event = self._advance_head_and_event(
                connection,
                scope,
                source_observed_at=encode_storage_datetime(source_observed_at),
                ingested_at=encode_storage_datetime(ingested_at),
                disposition=disposition,
                parser_invoked=False,
            )
            return DocumentHeadUpdate(head=head, event=event)

    @staticmethod
    def _validate_representation_identity(
        scope: RepresentationScope,
        recipe: ParserRecipe,
    ) -> None:
        if recipe.representation_id_for(scope.version_id) != scope.representation_id:
            raise RepresentationConflict("representation recipe identity does not match scope")

    def _load_representation_row(
        self,
        connection: sqlite3.Connection,
        scope: RepresentationScope,
    ) -> sqlite3.Row | None:
        return cast(
            sqlite3.Row | None,
            connection.execute(
                "SELECT r.*, mo.byte_length AS manifest_byte_length, "
                "no.byte_length AS native_byte_length FROM document_representations AS r "
                "LEFT JOIN objects AS mo ON mo.object_id = r.manifest_object_id "
                "LEFT JOIN objects AS no ON no.object_id = r.native_object_id "
                "WHERE r.document_id = ? AND r.version_id = ? AND r.representation_id = ?",
                (str(scope.document_id), scope.version_id, scope.representation_id),
            ).fetchone(),
        )

    def _required_representation_row(
        self,
        connection: sqlite3.Connection,
        scope: RepresentationScope,
    ) -> sqlite3.Row:
        row = self._load_representation_row(connection, scope)
        if row is None:
            raise RepresentationNotFound("representation does not exist")
        return row

    def _representation_from_row(self, row: sqlite3.Row) -> DocumentRepresentation:
        manifest_id = row["manifest_object_id"]
        native_id = row["native_object_id"]
        ready_at = row["ready_at"]
        lease_expires_at = row["lease_expires_at"]
        return DocumentRepresentation(
            scope=RepresentationScope(
                document_id=UUID(str(row["document_id"])),
                version_id=str(row["version_id"]),
                representation_id=str(row["representation_id"]),
            ),
            recipe=ParserRecipe(
                name=str(row["parser_name"]),
                version=str(row["parser_version"]),
                profile=str(row["parser_profile"]),
                config_hash=str(row["parser_config_hash"]),
                normalization_schema_version=str(row["normalization_schema_version"]),
            ),
            state=RepresentationState(str(row["state"])),
            attempt_count=int(row["attempt_count"]),
            revision=int(row["revision"]),
            active_owner_id=(
                str(row["active_owner_id"]) if row["active_owner_id"] is not None else None
            ),
            lease_expires_at=(
                decode_storage_datetime(str(lease_expires_at))
                if lease_expires_at is not None
                else None
            ),
            last_failure_code=(
                str(row["last_failure_code"]) if row["last_failure_code"] is not None else None
            ),
            manifest_object=(
                StoredObject(
                    object_id=str(manifest_id),
                    byte_length=int(row["manifest_byte_length"]),
                )
                if manifest_id is not None and row["manifest_byte_length"] is not None
                else None
            ),
            native_object=(
                StoredObject(
                    object_id=str(native_id),
                    byte_length=int(row["native_byte_length"]),
                )
                if native_id is not None and row["native_byte_length"] is not None
                else None
            ),
            block_count=int(row["block_count"]),
            warning_codes=self._warning_codes(str(row["warning_codes_json"])),
            created_at=decode_storage_datetime(str(row["created_at"])),
            updated_at=decode_storage_datetime(str(row["updated_at"])),
            ready_at=(decode_storage_datetime(str(ready_at)) if ready_at is not None else None),
        )

    def _representation_aggregate(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
    ) -> RepresentationAggregate:
        representation = self._representation_from_row(row)
        block_rows = connection.execute(
            "SELECT b.*, o.byte_length FROM representation_block_projection AS b "
            "JOIN objects AS o ON o.object_id = b.object_id WHERE b.document_id = ? "
            "AND b.version_id = ? AND b.representation_id = ? ORDER BY b.ordinal",
            (
                str(representation.scope.document_id),
                representation.scope.version_id,
                representation.scope.representation_id,
            ),
        ).fetchall()
        blocks = tuple(self._block_projection_from_row(item) for item in block_rows)
        try:
            return RepresentationAggregate(representation=representation, blocks=blocks)
        except ValueError as error:
            raise RepresentationIntegrityError(
                "representation projection is inconsistent"
            ) from error

    def _required_representation(
        self,
        connection: sqlite3.Connection,
        scope: RepresentationScope,
    ) -> RepresentationAggregate:
        return self._representation_aggregate(
            connection,
            self._required_representation_row(connection, scope),
        )

    @staticmethod
    def _block_projection_from_row(row: sqlite3.Row) -> RepresentationBlock:
        return RepresentationBlock(
            scope=RepresentationScope(
                document_id=UUID(str(row["document_id"])),
                version_id=str(row["version_id"]),
                representation_id=str(row["representation_id"]),
            ),
            block_id=UUID(str(row["block_id"])),
            object=StoredObject(
                object_id=str(row["object_id"]),
                byte_length=int(row["byte_length"]),
            ),
            ordinal=int(row["ordinal"]),
            parent_id=(UUID(str(row["parent_id"])) if row["parent_id"] is not None else None),
            kind=BlockKind(str(row["kind"])),
            order=int(row["sibling_order"]),
            line_start=int(row["line_start"]),
            line_end=int(row["line_end"]),
        )

    @staticmethod
    def _warning_codes(payload: str) -> tuple[str, ...]:
        try:
            value = json.loads(payload)
        except json.JSONDecodeError as error:
            raise RepresentationIntegrityError(
                "representation warning metadata is invalid"
            ) from error
        if (
            not isinstance(value, list)
            or any(not isinstance(item, str) for item in value)
            or value != sorted(set(value))
        ):
            raise RepresentationIntegrityError("representation warning metadata is invalid")
        return tuple(value)

    @staticmethod
    def _assert_row_recipe(row: sqlite3.Row, recipe: ParserRecipe) -> None:
        actual = (
            str(row["parser_name"]),
            str(row["parser_version"]),
            str(row["parser_profile"]),
            str(row["parser_config_hash"]),
            str(row["normalization_schema_version"]),
        )
        expected = (
            recipe.name,
            recipe.version,
            recipe.profile,
            recipe.config_hash,
            recipe.normalization_schema_version,
        )
        if actual != expected:
            raise RepresentationConflict("representation recipe differs from persisted facts")

    @staticmethod
    def _ready_aggregate_matches(
        aggregate: RepresentationAggregate,
        commit: ReadyRepresentationCommit,
    ) -> bool:
        representation = aggregate.representation
        expected_blocks = tuple(
            RepresentationBlock(
                scope=commit.scope,
                block_id=item.block.block_id,
                object=item.object,
                ordinal=item.ordinal,
                parent_id=item.block.parent_id,
                kind=item.block.kind,
                order=item.block.order,
                line_start=item.line_start,
                line_end=item.line_end,
            )
            for item in commit.blocks
        )
        return (
            representation.scope == commit.scope
            and representation.recipe == commit.recipe
            and representation.state is RepresentationState.READY
            and representation.manifest_object == commit.manifest_object
            and representation.native_object == commit.native_object
            and representation.block_count == len(commit.blocks)
            and representation.warning_codes == commit.warning_codes
            and aggregate.blocks == expected_blocks
        )

    @staticmethod
    def _validate_representation_owner(owner_id: str) -> None:
        if _OWNER.fullmatch(owner_id) is None:
            raise RepresentationLeaseConflict("representation owner identifier is invalid")

    @staticmethod
    def _representation_token_hash(lease_token: str) -> str:
        if not isinstance(lease_token, str) or len(lease_token) < _MIN_LEASE_TOKEN_LENGTH:
            raise RepresentationLeaseConflict("representation lease token is too short")
        return "sha256:" + hashlib.sha256(lease_token.encode("utf-8")).hexdigest()

    @staticmethod
    def _assert_representation_lease(
        row: sqlite3.Row,
        *,
        owner_id: str,
        token_hash: str,
        expected_revision: int,
        now_text: str,
    ) -> None:
        if row["state"] != RepresentationState.STAGING.value:
            raise RepresentationLeaseConflict("representation is not staging")
        if row["active_owner_id"] != owner_id or row["active_lease_token_hash"] != token_hash:
            raise RepresentationLeaseConflict("representation lease owner or token does not match")
        if str(row["lease_expires_at"]) <= now_text:
            raise RepresentationLeaseConflict("representation lease has expired")
        if int(row["revision"]) != expected_revision:
            raise RepresentationLeaseConflict("representation revision is stale")

    def _advance_head_and_event(
        self,
        connection: sqlite3.Connection,
        scope: RepresentationScope,
        *,
        source_observed_at: str,
        ingested_at: str,
        disposition: IngestionDisposition,
        parser_invoked: bool,
    ) -> tuple[DocumentHead, IngestionEvent]:
        if ingested_at < source_observed_at:
            raise RepresentationConflict("ingestion time precedes source observation")
        row = connection.execute(
            "SELECT * FROM document_heads WHERE document_id = ?",
            (str(scope.document_id),),
        ).fetchone()
        head_advanced = False
        if row is None:
            connection.execute(
                "INSERT INTO document_heads(document_id, version_id, representation_id, "
                "source_observed_at, last_ingested_at, last_disposition, revision) "
                "VALUES (?, ?, ?, ?, ?, ?, 1)",
                (
                    str(scope.document_id),
                    scope.version_id,
                    scope.representation_id,
                    source_observed_at,
                    ingested_at,
                    disposition.value,
                ),
            )
            head_advanced = True
        else:
            current_scope = self._head_from_row(row).scope
            current_observed = str(row["source_observed_at"])
            if source_observed_at == current_observed and scope != current_scope:
                raise RepresentationConflict("equal source observation has different scope")
            should_update = source_observed_at > current_observed or (
                source_observed_at == current_observed
                and scope == current_scope
                and ingested_at > str(row["last_ingested_at"])
            )
            if should_update:
                connection.execute(
                    "UPDATE document_heads SET version_id = ?, representation_id = ?, "
                    "source_observed_at = ?, last_ingested_at = ?, last_disposition = ?, "
                    "revision = revision + 1 WHERE document_id = ?",
                    (
                        scope.version_id,
                        scope.representation_id,
                        source_observed_at,
                        ingested_at,
                        disposition.value,
                        str(scope.document_id),
                    ),
                )
                head_advanced = True
        self._fault_point("after_document_head")
        sequence = int(
            connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM ingestion_events WHERE document_id = ?",
                (str(scope.document_id),),
            ).fetchone()[0]
        )
        connection.execute(
            "INSERT INTO ingestion_events(document_id, sequence, version_id, "
            "representation_id, disposition, parser_invoked, head_advanced, occurred_at, "
            "source_observed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(scope.document_id),
                sequence,
                scope.version_id,
                scope.representation_id,
                disposition.value,
                int(parser_invoked),
                int(head_advanced),
                ingested_at,
                source_observed_at,
            ),
        )
        self._fault_point("after_ingestion_event")
        head = self._required_document_head(connection, scope.document_id)
        event_row = connection.execute(
            "SELECT * FROM ingestion_events WHERE document_id = ? AND sequence = ?",
            (str(scope.document_id), sequence),
        ).fetchone()
        if event_row is None:
            raise CatalogError("ingestion event did not become visible")
        return head, self._ingestion_event_from_row(event_row)

    def _append_ingestion_event_without_head(
        self,
        connection: sqlite3.Connection,
        scope: RepresentationScope,
        *,
        source_observed_at: str,
        ingested_at: str,
        disposition: IngestionDisposition,
    ) -> IngestionEvent:
        """Append a parser-invoked observation while preserving the current head."""
        if ingested_at < source_observed_at:
            raise RepresentationConflict("ingestion time precedes source observation")
        self._required_rich_representation(connection, scope)
        sequence = int(
            connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM ingestion_events WHERE document_id = ?",
                (str(scope.document_id),),
            ).fetchone()[0]
        )
        connection.execute(
            "INSERT INTO ingestion_events(document_id, sequence, version_id, "
            "representation_id, disposition, parser_invoked, head_advanced, occurred_at, "
            "source_observed_at) VALUES (?, ?, ?, ?, ?, 1, 0, ?, ?)",
            (
                str(scope.document_id),
                sequence,
                scope.version_id,
                scope.representation_id,
                disposition.value,
                ingested_at,
                source_observed_at,
            ),
        )
        row = connection.execute(
            "SELECT * FROM ingestion_events WHERE document_id = ? AND sequence = ?",
            (str(scope.document_id), sequence),
        ).fetchone()
        if row is None:
            raise CatalogError("ingestion event did not become visible")
        self._fault_point("after_ingestion_event")
        return self._ingestion_event_from_row(row)

    def _required_document_head(
        self,
        connection: sqlite3.Connection,
        document_id: UUID,
    ) -> DocumentHead:
        row = connection.execute(
            "SELECT * FROM document_heads WHERE document_id = ?",
            (str(document_id),),
        ).fetchone()
        if row is None:
            raise RepresentationIncomplete("document head does not exist")
        return self._head_from_row(row)

    @staticmethod
    def _head_from_row(row: sqlite3.Row) -> DocumentHead:
        return DocumentHead(
            scope=RepresentationScope(
                document_id=UUID(str(row["document_id"])),
                version_id=str(row["version_id"]),
                representation_id=str(row["representation_id"]),
            ),
            source_observed_at=decode_storage_datetime(str(row["source_observed_at"])),
            last_ingested_at=decode_storage_datetime(str(row["last_ingested_at"])),
            last_disposition=IngestionDisposition(str(row["last_disposition"])),
            revision=int(row["revision"]),
        )

    @staticmethod
    def _ingestion_event_from_row(row: sqlite3.Row) -> IngestionEvent:
        scope = RepresentationScope(
            document_id=UUID(str(row["document_id"])),
            version_id=str(row["version_id"]),
            representation_id=str(row["representation_id"]),
        )
        return IngestionEvent(
            document_id=scope.document_id,
            sequence=int(row["sequence"]),
            scope=scope,
            disposition=IngestionDisposition(str(row["disposition"])),
            parser_invoked=bool(row["parser_invoked"]),
            head_advanced=bool(row["head_advanced"]),
            occurred_at=decode_storage_datetime(str(row["occurred_at"])),
            source_observed_at=decode_storage_datetime(str(row["source_observed_at"])),
        )

    def _last_scope_event(
        self,
        connection: sqlite3.Connection,
        scope: RepresentationScope,
    ) -> IngestionEvent:
        row = connection.execute(
            "SELECT * FROM ingestion_events WHERE document_id = ? AND version_id = ? "
            "AND representation_id = ? AND parser_invoked = 1 ORDER BY sequence DESC LIMIT 1",
            (str(scope.document_id), scope.version_id, scope.representation_id),
        ).fetchone()
        if row is None:
            raise RepresentationIncomplete("representation commit event is missing")
        return self._ingestion_event_from_row(row)


__all__ = ["_SQLiteCatalogRepresentationMixin"]
