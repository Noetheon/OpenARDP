"""Immutable checksummed SQLite schema migrations for the local catalog."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Migration:
    """One append-only ordered catalog schema revision."""

    version: int
    name: str
    statements: tuple[str, ...]

    @property
    def checksum(self) -> str:
        """Return a stable SHA-256 identity over revision metadata and statements."""
        payload = (
            f"openardp-sqlite-migration-v1\n{self.version}\n{self.name}\n"
            + "\n-- statement --\n".join(self.statements)
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(payload).hexdigest()


MIGRATION_1 = Migration(
    version=1,
    name="objects-documents-source-versions",
    statements=(
        """
        CREATE TABLE schema_migrations (
            version INTEGER PRIMARY KEY CHECK (version >= 1),
            name TEXT NOT NULL UNIQUE CHECK (length(name) BETWEEN 1 AND 128),
            checksum TEXT NOT NULL CHECK (
                length(checksum) = 71
                AND substr(checksum, 1, 7) = 'sha256:'
                AND substr(checksum, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            applied_at TEXT NOT NULL CHECK (length(applied_at) = 27)
        ) STRICT
        """,
        """
        CREATE TABLE objects (
            object_id TEXT PRIMARY KEY CHECK (
                length(object_id) = 71
                AND substr(object_id, 1, 7) = 'sha256:'
                AND substr(object_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            byte_length INTEGER NOT NULL CHECK (byte_length >= 0),
            registered_at TEXT NOT NULL CHECK (length(registered_at) = 27)
        ) STRICT
        """,
        """
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY CHECK (length(document_id) = 36),
            connector TEXT NOT NULL COLLATE BINARY CHECK (length(connector) BETWEEN 1 AND 128),
            source_locator TEXT NOT NULL COLLATE BINARY CHECK (
                length(source_locator) BETWEEN 1 AND 8192
            ),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            UNIQUE (connector, source_locator)
        ) STRICT
        """,
        """
        CREATE TABLE document_versions (
            document_id TEXT NOT NULL,
            version_id TEXT NOT NULL,
            source_object_id TEXT NOT NULL,
            media_type TEXT NOT NULL CHECK (length(media_type) BETWEEN 1 AND 255),
            source_modified_at TEXT NULL CHECK (
                source_modified_at IS NULL OR length(source_modified_at) = 27
            ),
            committed_at TEXT NOT NULL CHECK (length(committed_at) = 27),
            PRIMARY KEY (document_id, version_id),
            FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE RESTRICT,
            FOREIGN KEY (source_object_id) REFERENCES objects(object_id) ON DELETE RESTRICT,
            CHECK (version_id = source_object_id)
        ) STRICT
        """,
        """
        CREATE TABLE version_object_references (
            document_id TEXT NOT NULL,
            version_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK (
                length(role) BETWEEN 1 AND 64 AND role GLOB '[a-z]*'
            ),
            ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
            object_id TEXT NOT NULL,
            media_type TEXT NULL CHECK (
                media_type IS NULL OR length(media_type) BETWEEN 1 AND 255
            ),
            PRIMARY KEY (document_id, version_id, role, ordinal),
            FOREIGN KEY (document_id, version_id)
                REFERENCES document_versions(document_id, version_id) ON DELETE RESTRICT,
            FOREIGN KEY (object_id) REFERENCES objects(object_id) ON DELETE RESTRICT
        ) STRICT
        """,
        "CREATE INDEX version_object_references_object_id_idx "
        "ON version_object_references(object_id)",
    ),
)

MIGRATION_2 = Migration(
    version=2,
    name="recoverable-jobs",
    statements=(
        """
        CREATE TABLE jobs (
            job_id TEXT PRIMARY KEY CHECK (length(job_id) = 36),
            kind TEXT NOT NULL CHECK (length(kind) BETWEEN 1 AND 128),
            deduplication_key TEXT NOT NULL CHECK (
                length(deduplication_key) BETWEEN 1 AND 1024
            ),
            state TEXT NOT NULL CHECK (state IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED')),
            attempt_count INTEGER NOT NULL CHECK (attempt_count >= 0),
            max_attempts INTEGER NOT NULL CHECK (max_attempts BETWEEN 1 AND 100),
            revision INTEGER NOT NULL CHECK (revision >= 0),
            active_owner_id TEXT NULL CHECK (
                active_owner_id IS NULL OR length(active_owner_id) BETWEEN 1 AND 255
            ),
            active_lease_token_hash TEXT NULL CHECK (
                active_lease_token_hash IS NULL OR (
                    length(active_lease_token_hash) = 71
                    AND substr(active_lease_token_hash, 1, 7) = 'sha256:'
                    AND substr(active_lease_token_hash, 8) NOT GLOB '*[^0-9a-f]*'
                )
            ),
            lease_expires_at TEXT NULL CHECK (
                lease_expires_at IS NULL OR length(lease_expires_at) = 27
            ),
            last_transition_token_hash TEXT NULL CHECK (
                last_transition_token_hash IS NULL OR (
                    length(last_transition_token_hash) = 71
                    AND substr(last_transition_token_hash, 1, 7) = 'sha256:'
                    AND substr(last_transition_token_hash, 8) NOT GLOB '*[^0-9a-f]*'
                )
            ),
            last_failure_code TEXT NULL CHECK (
                last_failure_code IS NULL OR length(last_failure_code) BETWEEN 1 AND 128
            ),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            updated_at TEXT NOT NULL CHECK (length(updated_at) = 27),
            terminal_at TEXT NULL CHECK (terminal_at IS NULL OR length(terminal_at) = 27),
            UNIQUE (kind, deduplication_key),
            CHECK (attempt_count <= max_attempts),
            CHECK (
                (state = 'RUNNING' AND active_owner_id IS NOT NULL
                    AND active_lease_token_hash IS NOT NULL AND lease_expires_at IS NOT NULL
                    AND terminal_at IS NULL)
                OR
                (state = 'QUEUED' AND active_owner_id IS NULL
                    AND active_lease_token_hash IS NULL AND lease_expires_at IS NULL
                    AND terminal_at IS NULL)
                OR
                (state IN ('SUCCEEDED', 'FAILED') AND active_owner_id IS NULL
                    AND active_lease_token_hash IS NULL AND lease_expires_at IS NULL
                    AND terminal_at IS NOT NULL)
            )
        ) STRICT
        """,
        """
        CREATE TABLE job_events (
            job_id TEXT NOT NULL,
            sequence INTEGER NOT NULL CHECK (sequence >= 1),
            event_type TEXT NOT NULL CHECK (length(event_type) BETWEEN 1 AND 64),
            from_state TEXT NULL CHECK (
                from_state IS NULL OR from_state IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED')
            ),
            to_state TEXT NOT NULL CHECK (
                to_state IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED')
            ),
            occurred_at TEXT NOT NULL CHECK (length(occurred_at) = 27),
            attempt_count INTEGER NOT NULL CHECK (attempt_count >= 0),
            owner_id TEXT NULL CHECK (owner_id IS NULL OR length(owner_id) BETWEEN 1 AND 255),
            failure_code TEXT NULL CHECK (
                failure_code IS NULL OR length(failure_code) BETWEEN 1 AND 128
            ),
            PRIMARY KEY (job_id, sequence),
            FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        CREATE TABLE job_object_references (
            job_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK (length(role) BETWEEN 1 AND 64 AND role GLOB '[a-z]*'),
            ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
            object_id TEXT NOT NULL,
            media_type TEXT NULL CHECK (
                media_type IS NULL OR length(media_type) BETWEEN 1 AND 255
            ),
            PRIMARY KEY (job_id, role, ordinal),
            FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE RESTRICT,
            FOREIGN KEY (object_id) REFERENCES objects(object_id) ON DELETE RESTRICT
        ) STRICT
        """,
        "CREATE INDEX jobs_queue_idx ON jobs(state, created_at, job_id)",
        "CREATE INDEX jobs_lease_idx ON jobs(state, lease_expires_at, job_id)",
        "CREATE UNIQUE INDEX jobs_active_lease_token_idx ON jobs(active_lease_token_hash) "
        "WHERE active_lease_token_hash IS NOT NULL",
        "CREATE INDEX job_object_references_object_id_idx ON job_object_references(object_id)",
    ),
)

MIGRATION_3 = Migration(
    version=3,
    name="document-representations-and-heads",
    statements=(
        """
        CREATE TABLE document_representations (
            document_id TEXT NOT NULL,
            version_id TEXT NOT NULL,
            representation_id TEXT NOT NULL,
            parser_name TEXT NOT NULL CHECK (length(parser_name) BETWEEN 1 AND 255),
            parser_version TEXT NOT NULL CHECK (length(parser_version) BETWEEN 1 AND 255),
            parser_profile TEXT NOT NULL CHECK (length(parser_profile) BETWEEN 1 AND 255),
            parser_config_hash TEXT NOT NULL CHECK (
                length(parser_config_hash) = 71
                AND substr(parser_config_hash, 1, 7) = 'sha256:'
                AND substr(parser_config_hash, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            normalization_schema_version TEXT NOT NULL CHECK (
                length(normalization_schema_version) BETWEEN 1 AND 64
            ),
            state TEXT NOT NULL CHECK (state IN ('STAGING', 'READY', 'FAILED')),
            attempt_count INTEGER NOT NULL CHECK (attempt_count >= 1),
            revision INTEGER NOT NULL CHECK (revision >= 1),
            active_owner_id TEXT NULL CHECK (
                active_owner_id IS NULL OR length(active_owner_id) BETWEEN 1 AND 255
            ),
            active_lease_token_hash TEXT NULL CHECK (
                active_lease_token_hash IS NULL OR (
                    length(active_lease_token_hash) = 71
                    AND substr(active_lease_token_hash, 1, 7) = 'sha256:'
                    AND substr(active_lease_token_hash, 8) NOT GLOB '*[^0-9a-f]*'
                )
            ),
            lease_expires_at TEXT NULL CHECK (
                lease_expires_at IS NULL OR length(lease_expires_at) = 27
            ),
            last_transition_token_hash TEXT NULL CHECK (
                last_transition_token_hash IS NULL OR (
                    length(last_transition_token_hash) = 71
                    AND substr(last_transition_token_hash, 1, 7) = 'sha256:'
                    AND substr(last_transition_token_hash, 8) NOT GLOB '*[^0-9a-f]*'
                )
            ),
            last_failure_code TEXT NULL CHECK (
                last_failure_code IS NULL OR length(last_failure_code) BETWEEN 1 AND 128
            ),
            manifest_object_id TEXT NULL,
            native_object_id TEXT NULL,
            block_count INTEGER NOT NULL CHECK (block_count BETWEEN 0 AND 100000),
            warning_codes_json TEXT NOT NULL CHECK (length(warning_codes_json) >= 2),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            updated_at TEXT NOT NULL CHECK (length(updated_at) = 27),
            ready_at TEXT NULL CHECK (ready_at IS NULL OR length(ready_at) = 27),
            PRIMARY KEY (document_id, version_id, representation_id),
            FOREIGN KEY (document_id, version_id)
                REFERENCES document_versions(document_id, version_id) ON DELETE RESTRICT,
            FOREIGN KEY (manifest_object_id) REFERENCES objects(object_id) ON DELETE RESTRICT,
            FOREIGN KEY (native_object_id) REFERENCES objects(object_id) ON DELETE RESTRICT,
            CHECK (
                (state = 'STAGING' AND active_owner_id IS NOT NULL
                    AND active_lease_token_hash IS NOT NULL AND lease_expires_at IS NOT NULL
                    AND last_failure_code IS NULL AND manifest_object_id IS NULL
                    AND native_object_id IS NULL AND block_count = 0
                    AND warning_codes_json = '[]' AND ready_at IS NULL)
                OR
                (state = 'FAILED' AND active_owner_id IS NULL
                    AND active_lease_token_hash IS NULL AND lease_expires_at IS NULL
                    AND last_failure_code IS NOT NULL AND manifest_object_id IS NULL
                    AND native_object_id IS NULL AND block_count = 0
                    AND warning_codes_json = '[]' AND ready_at IS NULL)
                OR
                (state = 'READY' AND active_owner_id IS NULL
                    AND active_lease_token_hash IS NULL AND lease_expires_at IS NULL
                    AND last_failure_code IS NULL AND manifest_object_id IS NOT NULL
                    AND native_object_id IS NOT NULL AND ready_at IS NOT NULL)
            )
        ) STRICT
        """,
        """
        CREATE TABLE representation_blocks (
            document_id TEXT NOT NULL,
            version_id TEXT NOT NULL,
            representation_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL CHECK (ordinal BETWEEN 0 AND 99999),
            block_id TEXT NOT NULL CHECK (length(block_id) = 36),
            object_id TEXT NOT NULL,
            parent_id TEXT NULL CHECK (parent_id IS NULL OR length(parent_id) = 36),
            kind TEXT NOT NULL CHECK (length(kind) BETWEEN 1 AND 64),
            sibling_order INTEGER NOT NULL CHECK (sibling_order >= 0),
            line_start INTEGER NOT NULL CHECK (line_start >= 1),
            line_end INTEGER NOT NULL CHECK (line_end >= line_start),
            PRIMARY KEY (document_id, version_id, representation_id, ordinal),
            UNIQUE (document_id, version_id, representation_id, block_id),
            FOREIGN KEY (document_id, version_id, representation_id)
                REFERENCES document_representations(
                    document_id, version_id, representation_id
                ) ON DELETE RESTRICT,
            FOREIGN KEY (object_id) REFERENCES objects(object_id) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        CREATE TABLE document_heads (
            document_id TEXT PRIMARY KEY,
            version_id TEXT NOT NULL,
            representation_id TEXT NOT NULL,
            source_observed_at TEXT NOT NULL CHECK (length(source_observed_at) = 27),
            last_ingested_at TEXT NOT NULL CHECK (length(last_ingested_at) = 27),
            last_disposition TEXT NOT NULL CHECK (
                last_disposition IN ('COMMITTED', 'CACHE_HIT', 'FORCED_REPARSE', 'CONVERGED')
            ),
            revision INTEGER NOT NULL CHECK (revision >= 1),
            FOREIGN KEY (document_id, version_id, representation_id)
                REFERENCES document_representations(
                    document_id, version_id, representation_id
                ) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        CREATE TABLE ingestion_events (
            document_id TEXT NOT NULL,
            sequence INTEGER NOT NULL CHECK (sequence >= 1),
            version_id TEXT NOT NULL,
            representation_id TEXT NOT NULL,
            disposition TEXT NOT NULL CHECK (
                disposition IN ('COMMITTED', 'CACHE_HIT', 'FORCED_REPARSE', 'CONVERGED')
            ),
            parser_invoked INTEGER NOT NULL CHECK (parser_invoked IN (0, 1)),
            head_advanced INTEGER NOT NULL CHECK (head_advanced IN (0, 1)),
            occurred_at TEXT NOT NULL CHECK (length(occurred_at) = 27),
            source_observed_at TEXT NOT NULL CHECK (length(source_observed_at) = 27),
            PRIMARY KEY (document_id, sequence),
            FOREIGN KEY (document_id, version_id, representation_id)
                REFERENCES document_representations(
                    document_id, version_id, representation_id
                ) ON DELETE RESTRICT
        ) STRICT
        """,
        "CREATE INDEX document_representations_state_lease_idx "
        "ON document_representations(state, lease_expires_at)",
        "CREATE UNIQUE INDEX document_representations_active_token_idx "
        "ON document_representations(active_lease_token_hash) "
        "WHERE active_lease_token_hash IS NOT NULL",
        "CREATE INDEX representation_blocks_block_id_idx ON representation_blocks(block_id)",
        "CREATE INDEX representation_blocks_object_id_idx ON representation_blocks(object_id)",
        "CREATE INDEX ingestion_events_scope_idx "
        "ON ingestion_events(document_id, version_id, representation_id)",
    ),
)

MIGRATION_4 = Migration(
    version=4,
    name="lexical-block-search",
    statements=(
        """
        CREATE VIRTUAL TABLE block_search_index USING fts5(
            block_text,
            content='',
            contentless_delete=1,
            tokenize='unicode61 remove_diacritics 0'
        )
        """,
        """
        CREATE TABLE block_search_entries (
            entry_id INTEGER PRIMARY KEY,
            document_id TEXT NOT NULL CHECK (length(document_id) = 36),
            version_id TEXT NOT NULL CHECK (
                length(version_id) = 71
                AND substr(version_id, 1, 7) = 'sha256:'
                AND substr(version_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            representation_id TEXT NOT NULL CHECK (
                length(representation_id) = 71
                AND substr(representation_id, 1, 7) = 'sha256:'
                AND substr(representation_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            ordinal INTEGER NOT NULL CHECK (ordinal BETWEEN 0 AND 99999),
            block_id TEXT NOT NULL CHECK (length(block_id) = 36),
            kind TEXT NOT NULL CHECK (length(kind) BETWEEN 1 AND 64),
            trust_zone TEXT NOT NULL CHECK (length(trust_zone) BETWEEN 1 AND 64),
            page INTEGER NULL CHECK (page IS NULL OR page >= 0),
            slide INTEGER NULL CHECK (slide IS NULL OR slide >= 0),
            line_start INTEGER NOT NULL CHECK (line_start >= 1),
            line_end INTEGER NOT NULL CHECK (line_end >= line_start),
            text_hash TEXT NOT NULL CHECK (
                length(text_hash) = 71
                AND substr(text_hash, 1, 7) = 'sha256:'
                AND substr(text_hash, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            indexed_at TEXT NOT NULL CHECK (length(indexed_at) = 27),
            UNIQUE (document_id, version_id, representation_id, ordinal),
            UNIQUE (document_id, version_id, representation_id, block_id),
            FOREIGN KEY (document_id, version_id, representation_id)
                REFERENCES document_representations(
                    document_id, version_id, representation_id
                ) ON DELETE RESTRICT
        ) STRICT
        """,
        "CREATE INDEX block_search_entries_block_id_idx ON block_search_entries(block_id)",
        "CREATE INDEX block_search_entries_scope_idx "
        "ON block_search_entries(document_id, version_id, representation_id)",
    ),
)

MIGRATION_5 = Migration(
    version=5,
    name="rich-representation-attempts",
    statements=(
        """
        CREATE TABLE rich_parse_attempts (
            attempt_id TEXT PRIMARY KEY CHECK (length(attempt_id) = 36),
            document_id TEXT NOT NULL CHECK (length(document_id) = 36),
            version_id TEXT NOT NULL CHECK (
                length(version_id) = 71
                AND substr(version_id, 1, 7) = 'sha256:'
                AND substr(version_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            representation_id TEXT NOT NULL CHECK (
                length(representation_id) = 71
                AND substr(representation_id, 1, 7) = 'sha256:'
                AND substr(representation_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            outcome TEXT NOT NULL CHECK (outcome IN ('CANONICAL', 'CONVERGED', 'DIVERGED')),
            descriptor_object_id TEXT NOT NULL,
            provider_native_object_id TEXT NOT NULL,
            native_record_object_id TEXT NOT NULL,
            evidence_bundle_object_id TEXT NOT NULL,
            projection_count INTEGER NOT NULL CHECK (
                projection_count BETWEEN 0 AND 1000000
            ),
            attempt_json TEXT NOT NULL CHECK (length(attempt_json) >= 2),
            bundle_json TEXT NOT NULL CHECK (length(bundle_json) >= 2),
            event_sequence INTEGER NOT NULL CHECK (event_sequence >= 1),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            FOREIGN KEY (document_id, version_id, representation_id)
                REFERENCES document_representations(
                    document_id, version_id, representation_id
                ) ON DELETE RESTRICT,
            FOREIGN KEY (descriptor_object_id)
                REFERENCES objects(object_id) ON DELETE RESTRICT,
            FOREIGN KEY (provider_native_object_id)
                REFERENCES objects(object_id) ON DELETE RESTRICT,
            FOREIGN KEY (native_record_object_id)
                REFERENCES objects(object_id) ON DELETE RESTRICT,
            FOREIGN KEY (evidence_bundle_object_id)
                REFERENCES objects(object_id) ON DELETE RESTRICT,
            FOREIGN KEY (document_id, event_sequence)
                REFERENCES ingestion_events(document_id, sequence) ON DELETE RESTRICT,
            UNIQUE (document_id, event_sequence)
        ) STRICT
        """,
        """
        CREATE TABLE rich_attempt_evidence (
            attempt_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL CHECK (ordinal BETWEEN 0 AND 1000000),
            reference_object_id TEXT NOT NULL,
            projection_object_id TEXT NOT NULL,
            retrieval_object_id TEXT NOT NULL,
            PRIMARY KEY (attempt_id, ordinal),
            FOREIGN KEY (attempt_id)
                REFERENCES rich_parse_attempts(attempt_id) ON DELETE RESTRICT,
            FOREIGN KEY (reference_object_id)
                REFERENCES objects(object_id) ON DELETE RESTRICT,
            FOREIGN KEY (projection_object_id)
                REFERENCES objects(object_id) ON DELETE RESTRICT,
            FOREIGN KEY (retrieval_object_id)
                REFERENCES objects(object_id) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        CREATE TABLE rich_accepted_representations (
            document_id TEXT NOT NULL,
            version_id TEXT NOT NULL,
            representation_id TEXT NOT NULL,
            accepted_attempt_id TEXT NOT NULL UNIQUE,
            PRIMARY KEY (document_id, version_id, representation_id),
            FOREIGN KEY (document_id, version_id, representation_id)
                REFERENCES document_representations(
                    document_id, version_id, representation_id
                ) ON DELETE RESTRICT,
            FOREIGN KEY (accepted_attempt_id)
                REFERENCES rich_parse_attempts(attempt_id) ON DELETE RESTRICT
        ) STRICT
        """,
        "CREATE INDEX rich_parse_attempts_scope_idx ON rich_parse_attempts("
        "document_id, version_id, representation_id, created_at, attempt_id)",
        "CREATE INDEX rich_parse_attempts_descriptor_idx "
        "ON rich_parse_attempts(descriptor_object_id)",
        "CREATE INDEX rich_parse_attempts_native_idx "
        "ON rich_parse_attempts(provider_native_object_id)",
        "CREATE INDEX rich_parse_attempts_bundle_idx "
        "ON rich_parse_attempts(evidence_bundle_object_id)",
        "CREATE INDEX rich_attempt_evidence_reference_idx "
        "ON rich_attempt_evidence(reference_object_id)",
        "CREATE INDEX rich_attempt_evidence_projection_idx "
        "ON rich_attempt_evidence(projection_object_id)",
        "CREATE INDEX rich_attempt_evidence_retrieval_idx "
        "ON rich_attempt_evidence(retrieval_object_id)",
    ),
)

MIGRATION_6 = Migration(
    version=6,
    name="context-compilations",
    statements=(
        """
        CREATE TABLE context_compilations (
            receipt_id TEXT PRIMARY KEY CHECK (
                length(receipt_id) = 71
                AND substr(receipt_id, 1, 7) = 'sha256:'
                AND substr(receipt_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            receipt_object_id TEXT NOT NULL,
            receipt_byte_length INTEGER NOT NULL CHECK (receipt_byte_length >= 0),
            bundle_object_id TEXT NOT NULL,
            bundle_byte_length INTEGER NOT NULL CHECK (bundle_byte_length >= 0),
            bundle_id TEXT NOT NULL CHECK (length(bundle_id) = 36),
            task_digest TEXT NOT NULL CHECK (
                length(task_digest) = 71
                AND substr(task_digest, 1, 7) = 'sha256:'
                AND substr(task_digest, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            algorithm_name TEXT NOT NULL CHECK (length(algorithm_name) BETWEEN 1 AND 128),
            algorithm_version TEXT NOT NULL CHECK (length(algorithm_version) BETWEEN 1 AND 64),
            algorithm_config_hash TEXT NOT NULL CHECK (
                length(algorithm_config_hash) = 71
                AND substr(algorithm_config_hash, 1, 7) = 'sha256:'
                AND substr(algorithm_config_hash, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            estimator_name TEXT NOT NULL CHECK (length(estimator_name) BETWEEN 1 AND 128),
            estimator_version TEXT NOT NULL CHECK (length(estimator_version) BETWEEN 1 AND 64),
            estimator_unit TEXT NOT NULL CHECK (
                estimator_unit IN ('bytes', 'characters', 'tokens')
            ),
            estimator_config_hash TEXT NOT NULL CHECK (
                length(estimator_config_hash) = 71
                AND substr(estimator_config_hash, 1, 7) = 'sha256:'
                AND substr(estimator_config_hash, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            policy_digest TEXT NOT NULL CHECK (
                length(policy_digest) = 71
                AND substr(policy_digest, 1, 7) = 'sha256:'
                AND substr(policy_digest, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            budget_limit INTEGER NOT NULL CHECK (budget_limit BETWEEN 1 AND 16777216),
            budget_unit TEXT NOT NULL CHECK (budget_unit IN ('bytes', 'characters', 'tokens')),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            selected_count INTEGER NOT NULL CHECK (selected_count BETWEEN 0 AND 12000),
            omitted_count INTEGER NOT NULL CHECK (omitted_count BETWEEN 0 AND 12000),
            rejected_count INTEGER NOT NULL CHECK (rejected_count BETWEEN 0 AND 12000),
            stale_count INTEGER NOT NULL CHECK (stale_count BETWEEN 0 AND 12000),
            row_fingerprint TEXT NOT NULL CHECK (
                length(row_fingerprint) = 71
                AND substr(row_fingerprint, 1, 7) = 'sha256:'
                AND substr(row_fingerprint, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            FOREIGN KEY (receipt_object_id) REFERENCES objects(object_id) ON DELETE RESTRICT,
            FOREIGN KEY (bundle_object_id) REFERENCES objects(object_id) ON DELETE RESTRICT,
            CHECK (receipt_id = receipt_object_id)
        ) STRICT
        """,
        """
        CREATE TABLE context_compilation_scopes (
            receipt_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL CHECK (ordinal BETWEEN 0 AND 31),
            document_id TEXT NOT NULL CHECK (length(document_id) = 36),
            version_id TEXT NOT NULL CHECK (
                length(version_id) = 71
                AND substr(version_id, 1, 7) = 'sha256:'
                AND substr(version_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            representation_id TEXT NOT NULL CHECK (
                length(representation_id) = 71
                AND substr(representation_id, 1, 7) = 'sha256:'
                AND substr(representation_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            PRIMARY KEY (receipt_id, ordinal),
            UNIQUE (receipt_id, document_id, version_id, representation_id),
            FOREIGN KEY (receipt_id)
                REFERENCES context_compilations(receipt_id) ON DELETE RESTRICT,
            FOREIGN KEY (document_id, version_id, representation_id)
                REFERENCES document_representations(
                    document_id, version_id, representation_id
                ) ON DELETE RESTRICT
        ) STRICT
        """,
        "CREATE INDEX context_compilations_receipt_object_idx "
        "ON context_compilations(receipt_object_id)",
        "CREATE INDEX context_compilations_bundle_object_idx "
        "ON context_compilations(bundle_object_id)",
        "CREATE INDEX context_compilation_scopes_scope_idx "
        "ON context_compilation_scopes(document_id, version_id, representation_id)",
    ),
)

MIGRATION_7 = Migration(
    version=7,
    name="reconciliation-derivation-dag",
    statements=(
        """
        CREATE TABLE reconciliation_runs (
            run_id TEXT PRIMARY KEY CHECK (
                length(run_id) = 71 AND substr(run_id, 1, 7) = 'sha256:'
                AND substr(run_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            document_id TEXT NOT NULL CHECK (length(document_id) = 36),
            previous_version_id TEXT NOT NULL CHECK (
                length(previous_version_id) = 71
                AND substr(previous_version_id, 1, 7) = 'sha256:'
                AND substr(previous_version_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            previous_representation_id TEXT NOT NULL CHECK (
                length(previous_representation_id) = 71
                AND substr(previous_representation_id, 1, 7) = 'sha256:'
                AND substr(previous_representation_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            current_version_id TEXT NOT NULL CHECK (
                length(current_version_id) = 71
                AND substr(current_version_id, 1, 7) = 'sha256:'
                AND substr(current_version_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            current_representation_id TEXT NOT NULL CHECK (
                length(current_representation_id) = 71
                AND substr(current_representation_id, 1, 7) = 'sha256:'
                AND substr(current_representation_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            algorithm_version TEXT NOT NULL CHECK (
                length(algorithm_version) BETWEEN 1 AND 128
            ),
            config_hash TEXT NOT NULL CHECK (
                length(config_hash) = 71 AND substr(config_hash, 1, 7) = 'sha256:'
                AND substr(config_hash, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            result_fingerprint TEXT NOT NULL CHECK (
                length(result_fingerprint) = 71
                AND substr(result_fingerprint, 1, 7) = 'sha256:'
                AND substr(result_fingerprint, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            matched_count INTEGER NOT NULL CHECK (matched_count BETWEEN 0 AND 100000),
            reusable_count INTEGER NOT NULL CHECK (
                reusable_count BETWEEN 0 AND matched_count
            ),
            new_count INTEGER NOT NULL CHECK (new_count BETWEEN 0 AND 100000),
            ambiguous_count INTEGER NOT NULL CHECK (
                ambiguous_count BETWEEN 0 AND new_count
            ),
            comparison_count INTEGER NOT NULL CHECK (
                comparison_count BETWEEN 0 AND 1000000
            ),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            UNIQUE (document_id, current_version_id, current_representation_id),
            FOREIGN KEY (document_id, previous_version_id, previous_representation_id)
                REFERENCES document_representations(
                    document_id, version_id, representation_id
                ) ON DELETE RESTRICT,
            FOREIGN KEY (document_id, current_version_id, current_representation_id)
                REFERENCES document_representations(
                    document_id, version_id, representation_id
                ) ON DELETE RESTRICT,
            CHECK (
                previous_version_id != current_version_id
                OR previous_representation_id != current_representation_id
            )
        ) STRICT
        """,
        """
        CREATE TABLE block_lineages (
            lineage_id TEXT PRIMARY KEY CHECK (
                length(lineage_id) = 71 AND substr(lineage_id, 1, 7) = 'sha256:'
                AND substr(lineage_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            document_id TEXT NOT NULL CHECK (length(document_id) = 36),
            origin_version_id TEXT NOT NULL CHECK (
                length(origin_version_id) = 71
                AND substr(origin_version_id, 1, 7) = 'sha256:'
                AND substr(origin_version_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            origin_representation_id TEXT NOT NULL CHECK (
                length(origin_representation_id) = 71
                AND substr(origin_representation_id, 1, 7) = 'sha256:'
                AND substr(origin_representation_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            origin_block_id TEXT NOT NULL CHECK (length(origin_block_id) = 36),
            introduced_by_run_id TEXT NOT NULL,
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            UNIQUE (lineage_id, document_id),
            FOREIGN KEY (
                document_id, origin_version_id, origin_representation_id, origin_block_id
            ) REFERENCES representation_blocks(
                document_id, version_id, representation_id, block_id
            ) ON DELETE RESTRICT,
            FOREIGN KEY (introduced_by_run_id)
                REFERENCES reconciliation_runs(run_id) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        CREATE TABLE block_lineage_members (
            document_id TEXT NOT NULL CHECK (length(document_id) = 36),
            version_id TEXT NOT NULL CHECK (
                length(version_id) = 71 AND substr(version_id, 1, 7) = 'sha256:'
                AND substr(version_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            representation_id TEXT NOT NULL CHECK (
                length(representation_id) = 71
                AND substr(representation_id, 1, 7) = 'sha256:'
                AND substr(representation_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            block_id TEXT NOT NULL CHECK (length(block_id) = 36),
            lineage_id TEXT NOT NULL,
            canonical_hash TEXT NOT NULL CHECK (
                length(canonical_hash) = 71 AND substr(canonical_hash, 1, 7) = 'sha256:'
                AND substr(canonical_hash, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            binding_digest TEXT NOT NULL CHECK (
                length(binding_digest) = 71
                AND substr(binding_digest, 1, 7) = 'sha256:'
                AND substr(binding_digest, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            introduced_by_run_id TEXT NOT NULL,
            PRIMARY KEY (document_id, version_id, representation_id, block_id),
            UNIQUE (lineage_id, version_id, representation_id),
            FOREIGN KEY (document_id, version_id, representation_id, block_id)
                REFERENCES representation_blocks(
                    document_id, version_id, representation_id, block_id
                ) ON DELETE RESTRICT,
            FOREIGN KEY (lineage_id, document_id)
                REFERENCES block_lineages(lineage_id, document_id) ON DELETE RESTRICT,
            FOREIGN KEY (introduced_by_run_id)
                REFERENCES reconciliation_runs(run_id) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        CREATE TABLE reconciliation_relations (
            relation_id TEXT PRIMARY KEY CHECK (
                length(relation_id) = 71 AND substr(relation_id, 1, 7) = 'sha256:'
                AND substr(relation_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            run_id TEXT NOT NULL,
            relation_object_id TEXT NOT NULL,
            method TEXT NOT NULL CHECK (
                method IN ('native_id', 'exact_content', 'asset_or_table', 'similarity', 'sequence')
            ),
            confidence_ppm INTEGER NOT NULL CHECK (
                confidence_ppm BETWEEN 0 AND 1000000
            ),
            reusable INTEGER NOT NULL CHECK (reusable IN (0, 1)),
            document_id TEXT NOT NULL CHECK (length(document_id) = 36),
            previous_version_id TEXT NOT NULL,
            previous_representation_id TEXT NOT NULL,
            previous_block_id TEXT NOT NULL,
            current_version_id TEXT NOT NULL,
            current_representation_id TEXT NOT NULL,
            current_block_id TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES reconciliation_runs(run_id) ON DELETE RESTRICT,
            FOREIGN KEY (relation_object_id) REFERENCES objects(object_id) ON DELETE RESTRICT,
            FOREIGN KEY (
                document_id, previous_version_id, previous_representation_id,
                previous_block_id
            ) REFERENCES block_lineage_members(
                document_id, version_id, representation_id, block_id
            ) ON DELETE RESTRICT,
            FOREIGN KEY (
                document_id, current_version_id, current_representation_id,
                current_block_id
            ) REFERENCES block_lineage_members(
                document_id, version_id, representation_id, block_id
            ) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        CREATE TABLE derivation_slots (
            slot_id TEXT PRIMARY KEY CHECK (
                length(slot_id) = 71 AND substr(slot_id, 1, 7) = 'sha256:'
                AND substr(slot_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            namespace TEXT NOT NULL CHECK (length(namespace) BETWEEN 1 AND 128),
            subject_digest TEXT NOT NULL CHECK (
                length(subject_digest) = 71
                AND substr(subject_digest, 1, 7) = 'sha256:'
                AND substr(subject_digest, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            purpose TEXT NOT NULL CHECK (length(purpose) BETWEEN 1 AND 128),
            current_artifact_id TEXT NULL,
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            updated_at TEXT NOT NULL CHECK (length(updated_at) = 27),
            UNIQUE (namespace, subject_digest, purpose),
            FOREIGN KEY (slot_id, current_artifact_id)
                REFERENCES derivation_nodes(slot_id, artifact_id)
                ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED
        ) STRICT
        """,
        """
        CREATE TABLE derivation_nodes (
            artifact_id TEXT PRIMARY KEY CHECK (
                length(artifact_id) = 71 AND substr(artifact_id, 1, 7) = 'sha256:'
                AND substr(artifact_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            slot_id TEXT NOT NULL,
            state TEXT NOT NULL CHECK (
                state IN ('CURRENT', 'STALE', 'FAILED', 'SUPERSEDED')
            ),
            record_object_id TEXT NOT NULL,
            record_json TEXT NOT NULL CHECK (length(record_json) BETWEEN 2 AND 1048576),
            output_object_id TEXT NULL,
            generator_name TEXT NOT NULL CHECK (length(generator_name) BETWEEN 1 AND 255),
            generator_version TEXT NOT NULL CHECK (
                length(generator_version) BETWEEN 1 AND 255
            ),
            generator_profile TEXT NULL CHECK (
                generator_profile IS NULL OR length(generator_profile) BETWEEN 1 AND 255
            ),
            model_id TEXT NULL CHECK (model_id IS NULL OR length(model_id) BETWEEN 1 AND 1024),
            config_hash TEXT NOT NULL CHECK (
                length(config_hash) = 71 AND substr(config_hash, 1, 7) = 'sha256:'
                AND substr(config_hash, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            prompt_hash TEXT NULL CHECK (
                prompt_hash IS NULL OR (
                    length(prompt_hash) = 71 AND substr(prompt_hash, 1, 7) = 'sha256:'
                    AND substr(prompt_hash, 8) NOT GLOB '*[^0-9a-f]*'
                )
            ),
            revision INTEGER NOT NULL CHECK (revision >= 1),
            record_created_at TEXT NOT NULL CHECK (length(record_created_at) = 27),
            record_completed_at TEXT NOT NULL CHECK (length(record_completed_at) = 27),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            updated_at TEXT NOT NULL CHECK (length(updated_at) = 27),
            failure_code TEXT NULL CHECK (
                failure_code IS NULL OR length(failure_code) BETWEEN 1 AND 128
            ),
            row_fingerprint TEXT NOT NULL CHECK (
                length(row_fingerprint) = 71
                AND substr(row_fingerprint, 1, 7) = 'sha256:'
                AND substr(row_fingerprint, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            UNIQUE (slot_id, artifact_id),
            FOREIGN KEY (slot_id) REFERENCES derivation_slots(slot_id) ON DELETE RESTRICT,
            FOREIGN KEY (record_object_id) REFERENCES objects(object_id) ON DELETE RESTRICT,
            FOREIGN KEY (output_object_id) REFERENCES objects(object_id) ON DELETE RESTRICT,
            CHECK (
                (state = 'FAILED' AND output_object_id IS NULL AND failure_code IS NOT NULL)
                OR
                (state != 'FAILED' AND output_object_id IS NOT NULL AND failure_code IS NULL)
            )
        ) STRICT
        """,
        """
        CREATE TABLE derivation_dependencies (
            artifact_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL CHECK (ordinal BETWEEN 0 AND 100000),
            kind TEXT NOT NULL CHECK (
                kind IN ('EVIDENCE_BINDING', 'OBJECT', 'DERIVATION_OUTPUT')
            ),
            input_digest TEXT NOT NULL CHECK (
                length(input_digest) = 71 AND substr(input_digest, 1, 7) = 'sha256:'
                AND substr(input_digest, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            producer_artifact_id TEXT NULL,
            PRIMARY KEY (artifact_id, ordinal),
            UNIQUE (artifact_id, input_digest),
            FOREIGN KEY (artifact_id) REFERENCES derivation_nodes(artifact_id)
                ON DELETE RESTRICT,
            FOREIGN KEY (producer_artifact_id) REFERENCES derivation_nodes(artifact_id)
                ON DELETE RESTRICT,
            CHECK (
                (kind = 'DERIVATION_OUTPUT' AND producer_artifact_id IS NOT NULL)
                OR
                (kind != 'DERIVATION_OUTPUT' AND producer_artifact_id IS NULL)
            )
        ) STRICT
        """,
        """
        CREATE TABLE derivation_events (
            artifact_id TEXT NOT NULL,
            sequence INTEGER NOT NULL CHECK (sequence >= 1),
            from_state TEXT NULL CHECK (
                from_state IS NULL OR from_state IN ('CURRENT', 'STALE', 'FAILED', 'SUPERSEDED')
            ),
            to_state TEXT NOT NULL CHECK (
                to_state IN ('CURRENT', 'STALE', 'FAILED', 'SUPERSEDED')
            ),
            reason TEXT NOT NULL CHECK (
                reason IN ('published', 'generation_failed', 'dependency_inactive',
                           'reactivated', 'slot_replaced')
            ),
            run_id TEXT NULL,
            occurred_at TEXT NOT NULL CHECK (length(occurred_at) = 27),
            PRIMARY KEY (artifact_id, sequence),
            FOREIGN KEY (artifact_id) REFERENCES derivation_nodes(artifact_id)
                ON DELETE RESTRICT,
            FOREIGN KEY (run_id) REFERENCES reconciliation_runs(run_id) ON DELETE RESTRICT,
            CHECK (from_state IS NULL OR from_state != to_state)
        ) STRICT
        """,
        "CREATE INDEX block_lineage_members_binding_idx ON block_lineage_members(binding_digest)",
        "CREATE INDEX block_lineage_members_lineage_idx "
        "ON block_lineage_members(lineage_id, version_id, representation_id)",
        "CREATE INDEX reconciliation_relations_object_idx "
        "ON reconciliation_relations(relation_object_id)",
        "CREATE UNIQUE INDEX derivation_nodes_current_slot_idx "
        "ON derivation_nodes(slot_id) WHERE state = 'CURRENT'",
        "CREATE INDEX derivation_dependencies_input_idx "
        "ON derivation_dependencies(kind, input_digest)",
        "CREATE INDEX derivation_dependencies_producer_idx "
        "ON derivation_dependencies(producer_artifact_id) "
        "WHERE producer_artifact_id IS NOT NULL",
    ),
)

MIGRATION_8 = Migration(
    version=8,
    name="visual-evidence",
    statements=(
        """
        CREATE TABLE visual_page_rasters (
            raster_id TEXT PRIMARY KEY CHECK (
                length(raster_id) = 71 AND substr(raster_id, 1, 7) = 'sha256:'
                AND substr(raster_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            document_id TEXT NOT NULL CHECK (length(document_id) = 36),
            version_id TEXT NOT NULL,
            representation_id TEXT NOT NULL,
            page_number INTEGER NOT NULL CHECK (page_number BETWEEN 1 AND 10000),
            recipe_config_hash TEXT NOT NULL CHECK (
                length(recipe_config_hash) = 71
                AND substr(recipe_config_hash, 1, 7) = 'sha256:'
                AND substr(recipe_config_hash, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            raster_record_object_id TEXT NOT NULL,
            raster_object_id TEXT NOT NULL,
            raster_json TEXT NOT NULL CHECK (length(raster_json) BETWEEN 2 AND 1048576),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            UNIQUE (document_id, version_id, representation_id, page_number, recipe_config_hash),
            FOREIGN KEY (document_id, version_id, representation_id)
                REFERENCES rich_accepted_representations(
                    document_id, version_id, representation_id
                ) ON DELETE RESTRICT,
            FOREIGN KEY (raster_record_object_id)
                REFERENCES objects(object_id) ON DELETE RESTRICT,
            FOREIGN KEY (raster_object_id)
                REFERENCES objects(object_id) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        CREATE TABLE visual_evidence (
            visual_evidence_id TEXT PRIMARY KEY CHECK (
                length(visual_evidence_id) = 71
                AND substr(visual_evidence_id, 1, 7) = 'sha256:'
                AND substr(visual_evidence_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            document_id TEXT NOT NULL CHECK (length(document_id) = 36),
            version_id TEXT NOT NULL,
            representation_id TEXT NOT NULL,
            evidence_projection_id TEXT NOT NULL,
            raster_id TEXT NOT NULL,
            descriptor_object_id TEXT NOT NULL,
            crop_object_id TEXT NOT NULL,
            page_number INTEGER NOT NULL CHECK (page_number BETWEEN 1 AND 10000),
            granularity TEXT NOT NULL CHECK (
                granularity IN ('page_exact', 'region_exact', 'cell_exact', 'table_fallback')
            ),
            canonical_context_profile INTEGER NOT NULL CHECK (
                canonical_context_profile IN (0, 1)
            ),
            descriptor_json TEXT NOT NULL CHECK (
                length(descriptor_json) BETWEEN 2 AND 1048576
            ),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            row_fingerprint TEXT NOT NULL CHECK (
                length(row_fingerprint) = 71
                AND substr(row_fingerprint, 1, 7) = 'sha256:'
                AND substr(row_fingerprint, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            UNIQUE (evidence_projection_id, raster_id),
            FOREIGN KEY (raster_id)
                REFERENCES visual_page_rasters(raster_id) ON DELETE RESTRICT,
            FOREIGN KEY (descriptor_object_id)
                REFERENCES objects(object_id) ON DELETE RESTRICT,
            FOREIGN KEY (crop_object_id)
                REFERENCES objects(object_id) ON DELETE RESTRICT,
            FOREIGN KEY (document_id, version_id, representation_id)
                REFERENCES rich_accepted_representations(
                    document_id, version_id, representation_id
                ) ON DELETE RESTRICT
        ) STRICT
        """,
        "CREATE INDEX visual_page_rasters_scope_idx ON visual_page_rasters("
        "document_id, version_id, representation_id, page_number)",
        "CREATE INDEX visual_page_rasters_record_object_idx "
        "ON visual_page_rasters(raster_record_object_id)",
        "CREATE INDEX visual_page_rasters_raster_object_idx "
        "ON visual_page_rasters(raster_object_id)",
        "CREATE INDEX visual_evidence_scope_idx ON visual_evidence("
        "document_id, version_id, representation_id, evidence_projection_id)",
        "CREATE INDEX visual_evidence_descriptor_object_idx "
        "ON visual_evidence(descriptor_object_id)",
        "CREATE INDEX visual_evidence_crop_object_idx ON visual_evidence(crop_object_id)",
    ),
)

MIGRATION_9 = Migration(
    version=9,
    name="local-watcher-and-cancellable-jobs",
    statements=(
        "DROP INDEX jobs_queue_idx",
        "DROP INDEX jobs_lease_idx",
        "DROP INDEX jobs_active_lease_token_idx",
        "DROP INDEX job_object_references_object_id_idx",
        "ALTER TABLE job_events RENAME TO job_events_v2",
        "ALTER TABLE job_object_references RENAME TO job_object_references_v2",
        "ALTER TABLE jobs RENAME TO jobs_v2",
        """
        CREATE TABLE jobs (
            job_id TEXT PRIMARY KEY CHECK (length(job_id) = 36),
            kind TEXT NOT NULL CHECK (length(kind) BETWEEN 1 AND 128),
            deduplication_key TEXT NOT NULL CHECK (
                length(deduplication_key) BETWEEN 1 AND 1024
            ),
            state TEXT NOT NULL CHECK (
                state IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED')
            ),
            attempt_count INTEGER NOT NULL CHECK (attempt_count >= 0),
            max_attempts INTEGER NOT NULL CHECK (max_attempts BETWEEN 1 AND 100),
            revision INTEGER NOT NULL CHECK (revision >= 0),
            available_at TEXT NOT NULL CHECK (length(available_at) = 27),
            active_owner_id TEXT NULL CHECK (
                active_owner_id IS NULL OR length(active_owner_id) BETWEEN 1 AND 255
            ),
            active_lease_token_hash TEXT NULL CHECK (
                active_lease_token_hash IS NULL OR (
                    length(active_lease_token_hash) = 71
                    AND substr(active_lease_token_hash, 1, 7) = 'sha256:'
                    AND substr(active_lease_token_hash, 8) NOT GLOB '*[^0-9a-f]*'
                )
            ),
            lease_expires_at TEXT NULL CHECK (
                lease_expires_at IS NULL OR length(lease_expires_at) = 27
            ),
            cancellation_requested_at TEXT NULL CHECK (
                cancellation_requested_at IS NULL OR length(cancellation_requested_at) = 27
            ),
            last_transition_token_hash TEXT NULL CHECK (
                last_transition_token_hash IS NULL OR (
                    length(last_transition_token_hash) = 71
                    AND substr(last_transition_token_hash, 1, 7) = 'sha256:'
                    AND substr(last_transition_token_hash, 8) NOT GLOB '*[^0-9a-f]*'
                )
            ),
            last_failure_code TEXT NULL CHECK (
                last_failure_code IS NULL OR length(last_failure_code) BETWEEN 1 AND 128
            ),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            updated_at TEXT NOT NULL CHECK (length(updated_at) = 27),
            terminal_at TEXT NULL CHECK (terminal_at IS NULL OR length(terminal_at) = 27),
            UNIQUE (kind, deduplication_key),
            CHECK (attempt_count <= max_attempts),
            CHECK (available_at >= created_at),
            CHECK (
                cancellation_requested_at IS NULL OR (
                    state = 'RUNNING' AND cancellation_requested_at >= created_at
                    AND cancellation_requested_at <= updated_at
                )
            ),
            CHECK (
                (state = 'RUNNING' AND active_owner_id IS NOT NULL
                    AND active_lease_token_hash IS NOT NULL AND lease_expires_at IS NOT NULL
                    AND terminal_at IS NULL)
                OR
                (state = 'QUEUED' AND active_owner_id IS NULL
                    AND active_lease_token_hash IS NULL AND lease_expires_at IS NULL
                    AND cancellation_requested_at IS NULL AND terminal_at IS NULL)
                OR
                (state IN ('SUCCEEDED', 'FAILED', 'CANCELLED')
                    AND active_owner_id IS NULL AND active_lease_token_hash IS NULL
                    AND lease_expires_at IS NULL AND cancellation_requested_at IS NULL
                    AND terminal_at IS NOT NULL)
            )
        ) STRICT
        """,
        """
        INSERT INTO jobs(
            job_id, kind, deduplication_key, state, attempt_count, max_attempts, revision,
            available_at, active_owner_id, active_lease_token_hash, lease_expires_at,
            cancellation_requested_at, last_transition_token_hash, last_failure_code,
            created_at, updated_at, terminal_at
        ) SELECT
            job_id, kind, deduplication_key, state, attempt_count, max_attempts, revision,
            created_at, active_owner_id, active_lease_token_hash, lease_expires_at,
            NULL, last_transition_token_hash, last_failure_code, created_at, updated_at,
            terminal_at
        FROM jobs_v2
        """,
        """
        CREATE TABLE job_events (
            job_id TEXT NOT NULL,
            sequence INTEGER NOT NULL CHECK (sequence >= 1),
            event_type TEXT NOT NULL CHECK (length(event_type) BETWEEN 1 AND 64),
            from_state TEXT NULL CHECK (
                from_state IS NULL OR from_state IN (
                    'QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED'
                )
            ),
            to_state TEXT NOT NULL CHECK (
                to_state IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED')
            ),
            occurred_at TEXT NOT NULL CHECK (length(occurred_at) = 27),
            attempt_count INTEGER NOT NULL CHECK (attempt_count >= 0),
            owner_id TEXT NULL CHECK (owner_id IS NULL OR length(owner_id) BETWEEN 1 AND 255),
            failure_code TEXT NULL CHECK (
                failure_code IS NULL OR length(failure_code) BETWEEN 1 AND 128
            ),
            PRIMARY KEY (job_id, sequence),
            FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        INSERT INTO job_events(
            job_id, sequence, event_type, from_state, to_state, occurred_at,
            attempt_count, owner_id, failure_code
        ) SELECT job_id, sequence, event_type, from_state, to_state, occurred_at,
            attempt_count, owner_id, failure_code FROM job_events_v2
        """,
        """
        CREATE TABLE job_object_references (
            job_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK (length(role) BETWEEN 1 AND 64 AND role GLOB '[a-z]*'),
            ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
            object_id TEXT NOT NULL,
            media_type TEXT NULL CHECK (
                media_type IS NULL OR length(media_type) BETWEEN 1 AND 255
            ),
            PRIMARY KEY (job_id, role, ordinal),
            FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE RESTRICT,
            FOREIGN KEY (object_id) REFERENCES objects(object_id) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        INSERT INTO job_object_references(job_id, role, ordinal, object_id, media_type)
        SELECT job_id, role, ordinal, object_id, media_type FROM job_object_references_v2
        """,
        "DROP TABLE job_events_v2",
        "DROP TABLE job_object_references_v2",
        "DROP TABLE jobs_v2",
        "CREATE INDEX jobs_queue_idx ON jobs(state, available_at, created_at, job_id)",
        "CREATE INDEX jobs_lease_idx ON jobs(state, lease_expires_at, job_id)",
        "CREATE UNIQUE INDEX jobs_active_lease_token_idx ON jobs(active_lease_token_hash) "
        "WHERE active_lease_token_hash IS NOT NULL",
        "CREATE INDEX job_object_references_object_id_idx ON job_object_references(object_id)",
        """
        CREATE TABLE watch_roots (
            root_id TEXT PRIMARY KEY CHECK (
                length(root_id) = 71 AND substr(root_id, 1, 7) = 'sha256:'
                AND substr(root_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            root_path TEXT NOT NULL CHECK (length(root_path) BETWEEN 1 AND 8192),
            root_path_digest TEXT NOT NULL CHECK (
                length(root_path_digest) = 71 AND substr(root_path_digest, 1, 7) = 'sha256:'
                AND substr(root_path_digest, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            device_id TEXT NOT NULL CHECK (length(device_id) BETWEEN 1 AND 128),
            file_id TEXT NOT NULL CHECK (length(file_id) BETWEEN 1 AND 128),
            config_json TEXT NOT NULL CHECK (length(config_json) BETWEEN 2 AND 65536),
            config_hash TEXT NOT NULL CHECK (
                length(config_hash) = 71 AND substr(config_hash, 1, 7) = 'sha256:'
                AND substr(config_hash, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            generation INTEGER NOT NULL CHECK (generation >= 0),
            rescan_required INTEGER NOT NULL CHECK (rescan_required IN (0, 1)),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            updated_at TEXT NOT NULL CHECK (length(updated_at) = 27)
        ) STRICT
        """,
        """
        CREATE TABLE watch_observations (
            root_id TEXT NOT NULL,
            locator_digest TEXT NOT NULL CHECK (
                length(locator_digest) = 71 AND substr(locator_digest, 1, 7) = 'sha256:'
                AND substr(locator_digest, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            relative_locator TEXT NOT NULL CHECK (length(relative_locator) BETWEEN 1 AND 8192),
            state TEXT NOT NULL CHECK (state IN ('CANDIDATE', 'STABLE', 'TOMBSTONED')),
            fingerprint_json TEXT NULL CHECK (
                fingerprint_json IS NULL OR length(fingerprint_json) BETWEEN 2 AND 4096
            ),
            first_observed_at TEXT NOT NULL CHECK (length(first_observed_at) = 27),
            last_observed_at TEXT NOT NULL CHECK (length(last_observed_at) = 27),
            stable_since TEXT NULL CHECK (stable_since IS NULL OR length(stable_since) = 27),
            last_generation INTEGER NOT NULL CHECK (last_generation >= 0),
            last_scheduled_key TEXT NULL CHECK (
                last_scheduled_key IS NULL OR (
                    length(last_scheduled_key) = 71
                    AND substr(last_scheduled_key, 1, 7) = 'sha256:'
                    AND substr(last_scheduled_key, 8) NOT GLOB '*[^0-9a-f]*'
                )
            ),
            revision INTEGER NOT NULL CHECK (revision >= 1),
            row_fingerprint TEXT NOT NULL CHECK (
                length(row_fingerprint) = 71 AND substr(row_fingerprint, 1, 7) = 'sha256:'
                AND substr(row_fingerprint, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            PRIMARY KEY (root_id, locator_digest),
            UNIQUE (root_id, relative_locator),
            FOREIGN KEY (root_id) REFERENCES watch_roots(root_id) ON DELETE RESTRICT,
            CHECK ((state = 'TOMBSTONED') = (fingerprint_json IS NULL))
        ) STRICT
        """,
        """
        CREATE TABLE watch_job_targets (
            job_id TEXT PRIMARY KEY CHECK (length(job_id) = 36),
            root_id TEXT NOT NULL,
            locator_digest TEXT NOT NULL,
            relative_locator TEXT NOT NULL CHECK (length(relative_locator) BETWEEN 1 AND 8192),
            fingerprint_json TEXT NOT NULL CHECK (length(fingerprint_json) BETWEEN 2 AND 4096),
            parser_profile TEXT NOT NULL CHECK (length(parser_profile) BETWEEN 1 AND 255),
            deduplication_key TEXT NOT NULL UNIQUE CHECK (
                length(deduplication_key) = 71
                AND substr(deduplication_key, 1, 7) = 'sha256:'
                AND substr(deduplication_key, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE RESTRICT,
            FOREIGN KEY (root_id, locator_digest)
                REFERENCES watch_observations(root_id, locator_digest) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        CREATE TABLE watch_events (
            root_id TEXT NOT NULL,
            sequence INTEGER NOT NULL CHECK (sequence >= 1),
            event_type TEXT NOT NULL CHECK (length(event_type) BETWEEN 1 AND 64),
            locator_digest TEXT NULL CHECK (
                locator_digest IS NULL OR (
                    length(locator_digest) = 71 AND substr(locator_digest, 1, 7) = 'sha256:'
                    AND substr(locator_digest, 8) NOT GLOB '*[^0-9a-f]*'
                )
            ),
            job_id TEXT NULL CHECK (job_id IS NULL OR length(job_id) = 36),
            generation INTEGER NOT NULL CHECK (generation >= 0),
            occurred_at TEXT NOT NULL CHECK (length(occurred_at) = 27),
            entry_count INTEGER NOT NULL CHECK (entry_count >= 0),
            scheduled_count INTEGER NOT NULL CHECK (scheduled_count >= 0),
            tombstone_count INTEGER NOT NULL CHECK (tombstone_count >= 0),
            PRIMARY KEY (root_id, sequence),
            FOREIGN KEY (root_id) REFERENCES watch_roots(root_id) ON DELETE RESTRICT,
            FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE RESTRICT
        ) STRICT
        """,
        "CREATE INDEX watch_observations_state_idx ON watch_observations(root_id, state)",
        "CREATE INDEX watch_job_targets_root_idx ON watch_job_targets(root_id, created_at, job_id)",
        "CREATE INDEX watch_events_job_idx ON watch_events(job_id) WHERE job_id IS NOT NULL",
    ),
)

MIGRATION_10 = Migration(
    version=10,
    name="retention-recovery-maintenance",
    statements=(
        """
        CREATE TABLE retention_holds (
            hold_id TEXT PRIMARY KEY CHECK (
                length(hold_id) = 71 AND substr(hold_id, 1, 7) = 'sha256:'
                AND substr(hold_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            object_id TEXT NOT NULL CHECK (
                length(object_id) = 71 AND substr(object_id, 1, 7) = 'sha256:'
                AND substr(object_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            reason TEXT NOT NULL CHECK (length(reason) BETWEEN 1 AND 64),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            expires_at TEXT NULL CHECK (expires_at IS NULL OR length(expires_at) = 27),
            released_at TEXT NULL CHECK (released_at IS NULL OR length(released_at) = 27),
            CHECK (expires_at IS NULL OR expires_at > created_at),
            CHECK (released_at IS NULL OR released_at >= created_at)
        ) STRICT
        """,
        "CREATE INDEX retention_holds_active_idx "
        "ON retention_holds(object_id, expires_at, hold_id) WHERE released_at IS NULL",
        """
        CREATE TABLE quarantine_batches (
            batch_id TEXT PRIMARY KEY CHECK (length(batch_id) = 36),
            plan_id TEXT NOT NULL UNIQUE CHECK (
                length(plan_id) = 71 AND substr(plan_id, 1, 7) = 'sha256:'
                AND substr(plan_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            policy_id TEXT NOT NULL CHECK (length(policy_id) = 71),
            root_snapshot_id TEXT NOT NULL CHECK (length(root_snapshot_id) = 71),
            inventory_id TEXT NOT NULL CHECK (length(inventory_id) = 71),
            state TEXT NOT NULL CHECK (state IN (
                'PREPARED', 'QUARANTINED', 'PARTIALLY_RESTORED', 'RESTORED',
                'COMMITTING', 'COMMITTED', 'BLOCKED'
            )),
            quarantined_at TEXT NOT NULL CHECK (length(quarantined_at) = 27),
            not_before TEXT NOT NULL CHECK (length(not_before) = 27),
            entry_count INTEGER NOT NULL CHECK (entry_count >= 0),
            byte_count INTEGER NOT NULL CHECK (byte_count >= 0),
            terminal_at TEXT NULL CHECK (terminal_at IS NULL OR length(terminal_at) = 27),
            CHECK (not_before >= quarantined_at)
        ) STRICT
        """,
        """
        CREATE TABLE quarantine_entries (
            batch_id TEXT NOT NULL,
            object_id TEXT NOT NULL,
            byte_length INTEGER NOT NULL CHECK (byte_length >= 0),
            reason TEXT NOT NULL CHECK (length(reason) BETWEEN 1 AND 64),
            state TEXT NOT NULL CHECK (state IN (
                'PLANNED', 'QUARANTINED', 'RESTORED', 'COMMITTED_REMOVED',
                'CONFLICT_RETAINED'
            )),
            quarantined_at TEXT NULL CHECK (
                quarantined_at IS NULL OR length(quarantined_at) = 27
            ),
            restored_at TEXT NULL CHECK (restored_at IS NULL OR length(restored_at) = 27),
            committed_at TEXT NULL CHECK (committed_at IS NULL OR length(committed_at) = 27),
            PRIMARY KEY (batch_id, object_id),
            FOREIGN KEY (batch_id) REFERENCES quarantine_batches(batch_id) ON DELETE RESTRICT
        ) STRICT
        """,
        "CREATE UNIQUE INDEX quarantine_entries_one_recoverable_idx "
        "ON quarantine_entries(object_id) WHERE state IN ('PLANNED', 'QUARANTINED')",
        """
        CREATE TABLE maintenance_operations (
            operation_id TEXT PRIMARY KEY CHECK (length(operation_id) = 36),
            kind TEXT NOT NULL CHECK (kind IN (
                'QUARANTINE', 'RESTORE', 'COMMIT', 'BACKUP', 'MIGRATE', 'INDEX_REBUILD'
            )),
            subject_id TEXT NOT NULL CHECK (
                length(subject_id) = 71 AND substr(subject_id, 1, 7) = 'sha256:'
                AND substr(subject_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            state TEXT NOT NULL CHECK (state IN (
                'PREPARED', 'APPLYING', 'SUCCEEDED', 'FAILED', 'BLOCKED'
            )),
            acknowledgement_digest TEXT NULL CHECK (
                acknowledgement_digest IS NULL OR length(acknowledgement_digest) = 71
            ),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            updated_at TEXT NOT NULL CHECK (length(updated_at) = 27),
            terminal_at TEXT NULL CHECK (terminal_at IS NULL OR length(terminal_at) = 27),
            failure_code TEXT NULL CHECK (
                failure_code IS NULL OR length(failure_code) BETWEEN 1 AND 64
            ),
            CHECK (updated_at >= created_at),
            CHECK ((state IN ('PREPARED', 'APPLYING')) = (terminal_at IS NULL))
        ) STRICT
        """,
        "CREATE UNIQUE INDEX maintenance_operations_one_active_idx "
        "ON maintenance_operations((1)) WHERE state IN ('PREPARED', 'APPLYING')",
        """
        CREATE TABLE maintenance_operation_entries (
            operation_id TEXT NOT NULL,
            sequence INTEGER NOT NULL CHECK (sequence >= 1),
            object_id TEXT NOT NULL CHECK (length(object_id) = 71),
            byte_length INTEGER NOT NULL CHECK (byte_length >= 0),
            action TEXT NOT NULL CHECK (action IN (
                'MOVE_TO_QUARANTINE', 'MOVE_TO_ACTIVE', 'DELETE', 'RESTORE_CONFLICT', 'COPY'
            )),
            source_state TEXT NOT NULL CHECK (source_state IN ('ACTIVE', 'QUARANTINE', 'NONE')),
            destination_state TEXT NOT NULL CHECK (
                destination_state IN ('ACTIVE', 'QUARANTINE', 'NONE')
            ),
            outcome TEXT NULL CHECK (
                outcome IS NULL OR outcome IN ('MOVED', 'REMOVED', 'RETAINED', 'COPIED')
            ),
            PRIMARY KEY (operation_id, sequence),
            UNIQUE (operation_id, object_id),
            FOREIGN KEY (operation_id)
                REFERENCES maintenance_operations(operation_id) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        CREATE TABLE maintenance_events (
            operation_id TEXT NOT NULL,
            sequence INTEGER NOT NULL CHECK (sequence >= 1),
            event_type TEXT NOT NULL CHECK (length(event_type) BETWEEN 1 AND 64),
            object_id TEXT NULL CHECK (object_id IS NULL OR length(object_id) = 71),
            entry_count INTEGER NOT NULL CHECK (entry_count >= 0),
            byte_count INTEGER NOT NULL CHECK (byte_count >= 0),
            occurred_at TEXT NOT NULL CHECK (length(occurred_at) = 27),
            PRIMARY KEY (operation_id, sequence),
            FOREIGN KEY (operation_id)
                REFERENCES maintenance_operations(operation_id) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        CREATE TABLE migration_backups (
            target_revision INTEGER PRIMARY KEY CHECK (target_revision >= 1),
            source_revision INTEGER NOT NULL CHECK (source_revision >= 1),
            manifest_id TEXT NOT NULL UNIQUE CHECK (
                length(manifest_id) = 71 AND substr(manifest_id, 1, 7) = 'sha256:'
                AND substr(manifest_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            verified INTEGER NOT NULL CHECK (verified = 1),
            CHECK (target_revision > source_revision)
        ) STRICT
        """,
    ),
)

MIGRATION_11 = Migration(
    version=11,
    name="normalized-block-storage",
    statements=(
        "DROP INDEX representation_blocks_block_id_idx",
        "DROP INDEX representation_blocks_object_id_idx",
        "ALTER TABLE representation_blocks RENAME TO lineage_block_keys",
        """
        CREATE TABLE representation_scopes (
            scope_key INTEGER PRIMARY KEY,
            document_id TEXT NOT NULL CHECK (length(document_id) = 36),
            version_id TEXT NOT NULL CHECK (
                length(version_id) = 71 AND substr(version_id, 1, 7) = 'sha256:'
                AND substr(version_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            representation_id TEXT NOT NULL CHECK (
                length(representation_id) = 71
                AND substr(representation_id, 1, 7) = 'sha256:'
                AND substr(representation_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            UNIQUE (document_id, version_id, representation_id),
            FOREIGN KEY (document_id, version_id, representation_id)
                REFERENCES document_representations(
                    document_id, version_id, representation_id
                ) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        INSERT INTO representation_scopes(document_id, version_id, representation_id)
        SELECT document_id, version_id, representation_id
        FROM document_representations
        ORDER BY document_id, version_id, representation_id
        """,
        """
        CREATE TABLE representation_blocks (
            entry_id INTEGER PRIMARY KEY,
            scope_key INTEGER NOT NULL,
            ordinal INTEGER NOT NULL CHECK (ordinal BETWEEN 0 AND 99999),
            block_id TEXT NOT NULL CHECK (length(block_id) = 36),
            object_id TEXT NOT NULL,
            parent_id TEXT NULL CHECK (parent_id IS NULL OR length(parent_id) = 36),
            kind TEXT NOT NULL CHECK (length(kind) BETWEEN 1 AND 64),
            sibling_order INTEGER NOT NULL CHECK (sibling_order >= 0),
            line_start INTEGER NOT NULL CHECK (line_start >= 1),
            line_end INTEGER NOT NULL CHECK (line_end >= line_start),
            trust_zone TEXT NULL CHECK (
                trust_zone IS NULL OR length(trust_zone) BETWEEN 1 AND 64
            ),
            page INTEGER NULL CHECK (page IS NULL OR page >= 0),
            slide INTEGER NULL CHECK (slide IS NULL OR slide >= 0),
            text_hash TEXT NULL CHECK (
                text_hash IS NULL OR (
                    length(text_hash) = 71 AND substr(text_hash, 1, 7) = 'sha256:'
                    AND substr(text_hash, 8) NOT GLOB '*[^0-9a-f]*'
                )
            ),
            indexed_at TEXT NULL CHECK (indexed_at IS NULL OR length(indexed_at) = 27),
            UNIQUE (scope_key, ordinal),
            UNIQUE (scope_key, block_id),
            FOREIGN KEY (scope_key) REFERENCES representation_scopes(scope_key)
                ON DELETE RESTRICT,
            FOREIGN KEY (object_id) REFERENCES objects(object_id) ON DELETE RESTRICT,
            CHECK (
                (trust_zone IS NULL AND text_hash IS NULL AND indexed_at IS NULL
                    AND page IS NULL AND slide IS NULL)
                OR
                (trust_zone IS NOT NULL AND text_hash IS NOT NULL AND indexed_at IS NOT NULL)
            )
        ) STRICT
        """,
        """
        WITH maximum AS (
            SELECT coalesce(max(entry_id), 0) AS value FROM block_search_entries
        ), source AS (
            SELECT l.*, s.scope_key, e.entry_id AS search_entry_id,
                   e.trust_zone, e.page, e.slide, e.text_hash, e.indexed_at,
                   row_number() OVER (
                       ORDER BY l.document_id, l.version_id, l.representation_id, l.ordinal
                   ) AS sequence
            FROM lineage_block_keys AS l
            JOIN representation_scopes AS s
              ON s.document_id = l.document_id AND s.version_id = l.version_id
             AND s.representation_id = l.representation_id
            LEFT JOIN block_search_entries AS e
              ON e.document_id = l.document_id AND e.version_id = l.version_id
             AND e.representation_id = l.representation_id AND e.ordinal = l.ordinal
        )
        INSERT INTO representation_blocks(
            entry_id, scope_key, ordinal, block_id, object_id, parent_id, kind,
            sibling_order, line_start, line_end, trust_zone, page, slide, text_hash,
            indexed_at
        )
        SELECT coalesce(source.search_entry_id, maximum.value + source.sequence),
               source.scope_key, source.ordinal, source.block_id, source.object_id,
               source.parent_id, source.kind, source.sibling_order, source.line_start,
               source.line_end, source.trust_zone, source.page, source.slide,
               source.text_hash, source.indexed_at
        FROM source CROSS JOIN maximum
        ORDER BY source.sequence
        """,
        """
        DELETE FROM lineage_block_keys
        WHERE NOT EXISTS (
            SELECT 1 FROM block_lineages AS l
            WHERE l.document_id = lineage_block_keys.document_id
              AND l.origin_version_id = lineage_block_keys.version_id
              AND l.origin_representation_id = lineage_block_keys.representation_id
              AND l.origin_block_id = lineage_block_keys.block_id
        ) AND NOT EXISTS (
            SELECT 1 FROM block_lineage_members AS m
            WHERE m.document_id = lineage_block_keys.document_id
              AND m.version_id = lineage_block_keys.version_id
              AND m.representation_id = lineage_block_keys.representation_id
              AND m.block_id = lineage_block_keys.block_id
        )
        """,
        "DROP INDEX block_search_entries_block_id_idx",
        "DROP INDEX block_search_entries_scope_idx",
        "DROP TABLE block_search_entries",
        "CREATE INDEX representation_blocks_object_id_idx ON representation_blocks(object_id)",
        """
        CREATE VIEW representation_block_projection AS
        SELECT b.entry_id, s.document_id, s.version_id, s.representation_id,
               b.scope_key, b.ordinal, b.block_id, b.object_id, b.parent_id, b.kind,
               b.sibling_order, b.line_start, b.line_end, b.trust_zone, b.page,
               b.slide, b.text_hash, b.indexed_at
        FROM representation_blocks AS b
        JOIN representation_scopes AS s ON s.scope_key = b.scope_key
        """,
        "ALTER TABLE maintenance_operation_entries RENAME TO maintenance_operation_entries_v10",
        "ALTER TABLE maintenance_events RENAME TO maintenance_events_v10",
        "DROP INDEX maintenance_operations_one_active_idx",
        "ALTER TABLE maintenance_operations RENAME TO maintenance_operations_v10",
        """
        CREATE TABLE maintenance_operations (
            operation_id TEXT PRIMARY KEY CHECK (length(operation_id) = 36),
            kind TEXT NOT NULL CHECK (kind IN (
                'QUARANTINE', 'RESTORE', 'COMMIT', 'BACKUP', 'MIGRATE', 'INDEX_REBUILD',
                'STORAGE_OPTIMIZE'
            )),
            subject_id TEXT NOT NULL CHECK (
                length(subject_id) = 71 AND substr(subject_id, 1, 7) = 'sha256:'
                AND substr(subject_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            state TEXT NOT NULL CHECK (state IN (
                'PREPARED', 'APPLYING', 'SUCCEEDED', 'FAILED', 'BLOCKED'
            )),
            acknowledgement_digest TEXT NULL CHECK (
                acknowledgement_digest IS NULL OR length(acknowledgement_digest) = 71
            ),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            updated_at TEXT NOT NULL CHECK (length(updated_at) = 27),
            terminal_at TEXT NULL CHECK (terminal_at IS NULL OR length(terminal_at) = 27),
            failure_code TEXT NULL CHECK (
                failure_code IS NULL OR length(failure_code) BETWEEN 1 AND 64
            ),
            CHECK (updated_at >= created_at),
            CHECK ((state IN ('PREPARED', 'APPLYING')) = (terminal_at IS NULL))
        ) STRICT
        """,
        """
        INSERT INTO maintenance_operations(
            operation_id, kind, subject_id, state, acknowledgement_digest,
            created_at, updated_at, terminal_at, failure_code
        )
        SELECT operation_id, kind, subject_id, state, acknowledgement_digest,
               created_at, updated_at, terminal_at, failure_code
        FROM maintenance_operations_v10
        ORDER BY operation_id
        """,
        "CREATE UNIQUE INDEX maintenance_operations_one_active_idx "
        "ON maintenance_operations((1)) WHERE state IN ('PREPARED', 'APPLYING')",
        """
        CREATE TABLE maintenance_operation_entries (
            operation_id TEXT NOT NULL,
            sequence INTEGER NOT NULL CHECK (sequence >= 1),
            object_id TEXT NOT NULL CHECK (length(object_id) = 71),
            byte_length INTEGER NOT NULL CHECK (byte_length >= 0),
            action TEXT NOT NULL CHECK (action IN (
                'MOVE_TO_QUARANTINE', 'MOVE_TO_ACTIVE', 'DELETE', 'RESTORE_CONFLICT', 'COPY'
            )),
            source_state TEXT NOT NULL CHECK (source_state IN ('ACTIVE', 'QUARANTINE', 'NONE')),
            destination_state TEXT NOT NULL CHECK (
                destination_state IN ('ACTIVE', 'QUARANTINE', 'NONE')
            ),
            outcome TEXT NULL CHECK (
                outcome IS NULL OR outcome IN ('MOVED', 'REMOVED', 'RETAINED', 'COPIED')
            ),
            PRIMARY KEY (operation_id, sequence),
            UNIQUE (operation_id, object_id),
            FOREIGN KEY (operation_id)
                REFERENCES maintenance_operations(operation_id) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        INSERT INTO maintenance_operation_entries(
            operation_id, sequence, object_id, byte_length, action,
            source_state, destination_state, outcome
        )
        SELECT operation_id, sequence, object_id, byte_length, action,
               source_state, destination_state, outcome
        FROM maintenance_operation_entries_v10
        ORDER BY operation_id, sequence
        """,
        """
        CREATE TABLE maintenance_events (
            operation_id TEXT NOT NULL,
            sequence INTEGER NOT NULL CHECK (sequence >= 1),
            event_type TEXT NOT NULL CHECK (length(event_type) BETWEEN 1 AND 64),
            object_id TEXT NULL CHECK (object_id IS NULL OR length(object_id) = 71),
            entry_count INTEGER NOT NULL CHECK (entry_count >= 0),
            byte_count INTEGER NOT NULL CHECK (byte_count >= 0),
            occurred_at TEXT NOT NULL CHECK (length(occurred_at) = 27),
            PRIMARY KEY (operation_id, sequence),
            FOREIGN KEY (operation_id)
                REFERENCES maintenance_operations(operation_id) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        INSERT INTO maintenance_events(
            operation_id, sequence, event_type, object_id, entry_count, byte_count, occurred_at
        )
        SELECT operation_id, sequence, event_type, object_id, entry_count, byte_count, occurred_at
        FROM maintenance_events_v10
        ORDER BY operation_id, sequence
        """,
        "DROP TABLE maintenance_operation_entries_v10",
        "DROP TABLE maintenance_events_v10",
        "DROP TABLE maintenance_operations_v10",
    ),
)

MIGRATIONS = (
    MIGRATION_1,
    MIGRATION_2,
    MIGRATION_3,
    MIGRATION_4,
    MIGRATION_5,
    MIGRATION_6,
    MIGRATION_7,
    MIGRATION_8,
    MIGRATION_9,
    MIGRATION_10,
    MIGRATION_11,
)
CURRENT_SCHEMA_VERSION = MIGRATIONS[-1].version

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "MIGRATIONS",
    "MIGRATION_1",
    "MIGRATION_2",
    "MIGRATION_3",
    "MIGRATION_4",
    "MIGRATION_5",
    "MIGRATION_6",
    "MIGRATION_7",
    "MIGRATION_8",
    "MIGRATION_9",
    "MIGRATION_10",
    "MIGRATION_11",
    "Migration",
]
