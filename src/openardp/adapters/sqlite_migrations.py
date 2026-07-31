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

MIGRATIONS = (
    MIGRATION_1,
    MIGRATION_2,
    MIGRATION_3,
    MIGRATION_4,
    MIGRATION_5,
    MIGRATION_6,
    MIGRATION_7,
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
    "Migration",
]
