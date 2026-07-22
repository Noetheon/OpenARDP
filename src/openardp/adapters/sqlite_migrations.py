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

MIGRATIONS = (MIGRATION_1, MIGRATION_2)
CURRENT_SCHEMA_VERSION = MIGRATIONS[-1].version

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "MIGRATIONS",
    "MIGRATION_1",
    "MIGRATION_2",
    "Migration",
]
