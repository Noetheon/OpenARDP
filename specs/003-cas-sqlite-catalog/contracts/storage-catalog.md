# Internal Contracts: Object Store, Catalog and Persistence Services

**Version**: F003 internal contract 1

These Python-library contracts are provider-neutral application boundaries. They are not public JSON interchange schemas and do not change the F002 schema release.

## Error contract

All errors are typed, deterministic and sanitized. They may contain validated object/document/version/job identifiers and bounded classification codes. They must not contain byte bodies, source locators, lease tokens, raw SQL parameters or document-originated exception text.

### Object-store errors

- `MalformedObjectIdentity`: input is not the canonical SHA-256 ID form.
- `ObjectNotFound`: no canonical regular leaf exists for the requested identity.
- `ObjectCorrupt`: a regular leaf's bytes or length disagree with the requested identity/metadata.
- `UnsafeStoreEntry`: a managed component is a link, junction, directory at a leaf, non-regular entry or malformed tree node.
- `ObjectPublicationError`: staging or atomic publication failed before a confirmed complete result.
- `ObjectDurabilityError`: a complete object is visible but the strongest supported post-publication synchronization did not complete.

### Catalog errors

- `CatalogIncompatible`: file is a foreign schema or migration history is malformed.
- `CatalogTooNew`: installed catalog revision is newer than this reader.
- `MigrationFailed`: a pending migration chain rolled back.
- `DocumentConflict`: an immutable document/source-key identity was reused inconsistently.
- `VersionConflict`: an existing composite version differs from the retried commit.
- `InvalidObjectReference`: an object inventory or reference set is incomplete or inconsistent.

### Job errors

- `JobNotFound`.
- `JobConflict`: idempotency key exists with a different immutable specification.
- `InvalidJobTransition`: requested transition is not valid from current state.
- `LeaseConflict`: owner, token, revision or unexpired lease proof failed.

## `ObjectStore` port

```python
class ObjectStore(Protocol):
    def put_chunks(self, chunks: Iterable[bytes]) -> StoredObject: ...

    def iter_chunks(
        self,
        object_id: str,
        *,
        chunk_size: int = 1024 * 1024,
    ) -> Iterator[bytes]: ...

    def verify(
        self,
        object_id: str,
        *,
        expected_length: int | None = None,
    ) -> StoredObject: ...

    def inventory(self) -> ObjectInventory: ...
```

### `put_chunks`

Preconditions:

- `chunks` yields only bytes-like chunks; empty payload and empty chunks are valid.
- The iterable may be one-shot and must not be replayed.

Postconditions:

- Returns SHA-256 identity and total length of exact concatenated bytes.
- Before return, the canonical leaf is a complete regular file that verifies.
- Concurrent identical calls converge on the same result.
- Existing corruption or unsafe layout is reported, not silently repaired.
- A pre-publication failure exposes no canonical object leaf.
- Temporary files created by the current call are removed on catchable failure; crash residue remains below staging.

### `iter_chunks`

- Validates identity before filesystem access.
- Never follows a managed link or junction.
- Opens read-only and reads with the requested positive bounded chunk size.
- Does not promise integrity before EOF; callers requiring prior trust call `verify` first.

### `verify`

- Hashes and counts the full open stream.
- Confirms a regular stable file before and after reading.
- Compares the digest to `object_id` and, when supplied, the exact length.
- Returns only on verified equality.

### `inventory`

- Scans deterministic sorted entries under the exact fan-out layout.
- Does not follow links or delete anything.
- Returns verified canonical objects and separately sorted anomalies, including staging residue.

## `Catalog` port

```python
class Catalog(Protocol):
    def initialize(self, *, now: datetime) -> int: ...
    def schema_version(self) -> int: ...
    def register_document(
        self,
        source_key: SourceKey,
        *,
        document_id: UUID,
        now: datetime,
    ) -> LogicalDocument: ...
    def commit_source_version(self, commit: SourceVersionCommit) -> DocumentVersion: ...
    def get_version(self, document_id: UUID, version_id: str) -> DocumentVersion | None: ...
    def list_versions(self, document_id: UUID) -> tuple[DocumentVersion, ...]: ...
    def create_job(self, spec: JobSpec) -> Job: ...
    def claim_job(
        self,
        *,
        kind: str | None,
        owner_id: str,
        lease_token: str,
        now: datetime,
        lease_until: datetime,
    ) -> JobLease | None: ...
    def renew_job(
        self,
        job_id: UUID,
        *,
        owner_id: str,
        lease_token: str,
        expected_revision: int,
        now: datetime,
        lease_until: datetime,
    ) -> JobLease: ...
    def complete_job(...same fencing fields...) -> Job: ...
    def fail_job(...same fencing fields..., retryable: bool, failure_code: str) -> Job: ...
    def recover_expired_jobs(self, *, now: datetime) -> RecoveryResult: ...
    def reference_snapshot(self, *, observed_at: datetime) -> ReferenceSnapshot: ...
```

### Catalog initialization

- Inspects existing schema compatibility before persistent PRAGMA changes.
- Rejects foreign schemas, migration gaps, checksum drift and newer revisions without mutation.
- Applies all pending static revisions in one exclusive transaction.
- Checks foreign-key integrity before commit.
- Repeated initialization is logically idempotent.

### Document registration

- Exact source key is unique.
- Equivalent retries return the original document, even when the caller proposed a different unused UUID after losing a response.
- A document ID already bound to a different source key conflicts.
- No replacement or delete-on-conflict SQL is permitted.

### Source-version commit

- The catalog method expects already physically verified `StoredObject` metadata.
- Every extra reference carries the verified byte length needed to register or compare object metadata.
- It writes object metadata, the composite source version and every extra reference in one immediate transaction.
- Existing equivalent data returns the original result without new rows.
- Reference tuples compare canonically by `(role, ordinal)`; `source_modified_at` is immutable, while `committed_at`
  remains the timestamp of the first successful commit across a lost-response retry.
- Any immutable mismatch rolls back the entire retry.
- Independent readers observe either no composite version or the complete reference set.
- The record is a source-version fact, not a `READY` parser representation.

### Job creation

- `(kind, deduplication_key)` is unique.
- Equivalent retries return the existing job and references.
- Conflicting immutable specifications fail.
- Initial state is `QUEUED`, attempt `0`, revision `0`, with one `ENQUEUED` event.

### Job claim

- The raw lease token is caller-generated and never persisted or logged.
- A lost-response retry with the same owner/token returns its existing unexpired claim.
- Otherwise at most one eligible queued job is selected deterministically by creation time and job ID.
- Claim atomically increments attempt/revision, enters `RUNNING`, stores the token hash and appends `CLAIMED`.

### Renewal and completion

- Require exact owner, token hash, expected revision, `RUNNING` state and `lease_expires_at > now`.
- Renewal requires `lease_until > now`; an already equal-or-later expiry for the same proof is idempotent.
- Completion clears the active lease, records terminal time and appends `COMPLETED`.
- A mutating transition timestamp cannot precede the current durable `updated_at` value.
- A repeated completion with the same last-transition token returns the existing success; a stale different token fails.

### Failure and recovery

- `failure_code` is a bounded machine token, never free-form exception text.
- Retryable failure with attempts left returns to `QUEUED`; otherwise enters `FAILED`.
- Recovery selects only `RUNNING` rows whose expiry is `<= now`.
- It requeues those with attempts left and fails exhausted jobs, appending one event per changed job.
- A repeated recovery run without new expired work is empty and terminal jobs never reactivate.

### Reference snapshot

- Runs in one read transaction on a query-only connection.
- Includes every source-object reference, extra version reference and job reference.
- Does not include unreferenced rows from `objects`.
- Returns deterministically sorted unique identities and the installed schema revision.

## `PersistenceService`

```python
class PersistenceService:
    def register_document(self, source_key: SourceKey, *, now: datetime) -> LogicalDocument: ...

    def persist_source_version(
        self,
        *,
        document_id: UUID,
        source_chunks: Iterable[bytes],
        media_type: str,
        references: Sequence[ObjectReference] = (),
        source_modified_at: datetime | None = None,
        now: datetime,
    ) -> DocumentVersion: ...
```

### Registration

- Generates an RFC 9562 UUIDv7 with injected clock/randomness.
- Retries only a genuine UUID collision; source-key races return the existing document.

### Persist source version

1. Store exact source chunks in CAS.
2. Verify source and each extra referenced object against expected length.
3. Build `SourceVersionCommit`, requiring source object identity equals version ID.
4. Call the atomic catalog method.
5. If step 4 fails, do not delete the complete CAS object.

No parser, normalizer, representation, block, index or CLI behavior is part of this service.

## `ReachabilityService`

```python
class ReachabilityService:
    def analyze(self, *, observed_at: datetime) -> ReachabilityReport: ...
```

1. Capture a catalog reference snapshot.
2. Inventory and verify the managed object store without mutation.
3. Classify verified objects in the snapshot as reachable.
4. Classify verified objects absent from the snapshot as candidates.
5. Add missing referenced IDs and every inventory anomaly as inconsistencies.
6. Return deterministic sorted records.

The service has no delete port and never treats a candidate as approved for reclamation.

## Logging contract

Allowed fields:

- validated object/document/version/job IDs;
- transition state and bounded failure code;
- attempt/revision counts;
- durations and aggregate counts.

Prohibited fields:

- object bytes or decoded body content;
- source locator or filename;
- raw lease token/token material;
- untrusted exception message, SQL parameters or job data.

## Compatibility contract

- Current internal catalog revision: `2`.
- Older supported revision: `1`, upgraded transactionally.
- Revision `>2`, gaps, unknown checksums or foreign tables without migration history are rejected without mutation.
- Migration definitions are append-only once released.
- Persisted ID algorithms remain those defined in F002/ADR 0006; changing them requires a separate ADR and migration analysis.
