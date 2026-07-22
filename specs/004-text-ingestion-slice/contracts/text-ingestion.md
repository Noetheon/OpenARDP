# Internal Contracts: Text Parsing, Ingestion, Query and CLI

**Version**: F004 internal contract 1

These contracts extend the provider-neutral Python application boundary. They do not change the public F002 JSON Schema
release and do not authorize source text to initiate side effects.

## Error contract

All public errors are typed and sanitized. They may carry canonical object/document/version/representation/block IDs,
bounded machine codes and counts. They must not contain body text, raw source bytes, lease tokens, SQL parameters,
untrusted parser exceptions or a source locator unless the operator explicitly requested that locator in normal output.

### Source/workspace errors

- `WorkspaceMissing`: marker is absent; commands do not initialize implicitly.
- `WorkspaceIncompatible`: marker/catalog/layout is foreign, malformed or newer.
- `InvalidSourcePath`: path syntax, link/junction, type or descriptor/path agreement is unsafe.
- `UnsupportedTextMedia`: suffix/media contract is not TXT/Markdown.
- `SourceTooLarge`: exact configured byte bound exceeded.
- `SourceChangedDuringSnapshot`: descriptor identity/size/mtime changed during streaming.

### Parser errors

- `TextDecodingError`: strict UTF-8 decoding failed.
- `UnsafeTextContent`: NUL or prohibited text structure encountered.
- `TextResourceLimitExceeded`: line/block bound exceeded.
- `ParserFailure`: sanitized adapter failure classification.

### Representation errors

- `RepresentationBusy`: another unexpired owner holds the claim.
- `RepresentationConflict`: an immutable recipe/scope/ready aggregate differs.
- `RepresentationLeaseConflict`: stale owner/token/revision/expiry proof.
- `RepresentationIncomplete`: requested scope is STAGING/FAILED or aggregate projections are incomplete.
- `RepresentationIntegrityError`: required CAS object is missing, corrupt or semantically inconsistent.
- `DocumentNotFound`, `RepresentationNotFound`, `BlockNotFound`, `AmbiguousBlock`.

## `ParserAdapter` port

```python
@runtime_checkable
class ParserAdapter(Protocol):
    @property
    def recipe(self) -> ParserRecipe: ...

    def supports(self, media_type: str) -> bool: ...

    def parse(
        self,
        chunks: Iterable[bytes],
        *,
        media_type: str,
    ) -> ParsedTextDocument: ...
```

### Preconditions

- `chunks` is one-shot verified source-object input and yields only bytes.
- `media_type` is a validated declared media type.
- The caller has not supplied a path, command, URL or tool capability to the parser.

### Postconditions

- Output is deterministic for equal bytes/media/recipe on every supported platform.
- No network, model call, source write or external link resolution occurs.
- Every block contains exact inclusive line provenance and only source-backed text.
- Warnings are sorted unique machine codes without snippets.
- Unsupported media, invalid UTF-8, NUL and limits fail before any output is committed.

The built-in adapter supports `text/plain` and `text/markdown` under profile `default` only.

### Default isolation wrapper

`IsolatedParserAdapter` implements the same port by spawning a fresh worker. The parent streams chunks over a private IPC
channel, provides media/recipe metadata but no source path, waits at most 30 seconds, validates one strict result envelope
and always joins or terminates the worker. The worker disables socket creation before constructing the pure adapter.
Timeout, abnormal exit, invalid envelope and raw worker exceptions map to bounded parser error codes. POSIX CPU,
file-descriptor and address-space limits are applied where available; portable input, line and block limits remain
authoritative on every platform.

## Local source snapshot adapter

```python
class LocalSource:
    def snapshot_to(
        self,
        object_store: ObjectStore,
        *,
        observed_at: datetime,
    ) -> SourceSnapshot: ...

    def inspect(self, *, observed_at: datetime) -> SourceInspection: ...
```

### `snapshot_to`

1. Validate control-free explicit path and supported suffix.
2. Reject symlink/junction components and non-regular leaves.
3. Open read-only with non-following flags where supported.
4. Compare path and descriptor identity and enforce byte limit before streaming.
5. Stream the same descriptor to `ObjectStore.put_chunks` in bounded chunks.
6. Compare descriptor identity, size and mtime after EOF; reject a changed snapshot.
7. Return canonical path locator, media type, object metadata, UTC mtime and observation time.

The method never writes to the source. A complete CAS object created before a race is an unreferenced candidate.

### `inspect`

Performs the same safe read checks and streams SHA-256 without publishing to CAS. It never invokes a parser and is used by
`status`. Missing input is a classified result; unsafe input is an error.

## Catalog extensions

```python
class Catalog(Protocol):
    # F003 methods remain unchanged.

    def get_document(self, document_id: UUID) -> LogicalDocument | None: ...
    def get_document_by_source(self, source_key: SourceKey) -> LogicalDocument | None: ...
    def list_documents(self) -> tuple[LogicalDocument, ...]: ...

    def acquire_representation(
        self,
        scope: RepresentationScope,
        recipe: ParserRecipe,
        *,
        owner_id: str,
        lease_token: str,
        now: datetime,
        lease_until: datetime,
    ) -> RepresentationAcquireResult: ...

    def renew_representation(
        self,
        scope: RepresentationScope,
        *,
        owner_id: str,
        lease_token: str,
        expected_revision: int,
        now: datetime,
        lease_until: datetime,
    ) -> RepresentationLease: ...

    def fail_representation(
        self,
        scope: RepresentationScope,
        *,
        owner_id: str,
        lease_token: str,
        expected_revision: int,
        now: datetime,
        failure_code: str,
    ) -> DocumentRepresentation: ...

    def commit_ready_representation(
        self,
        commit: ReadyRepresentationCommit,
        *,
        owner_id: str | None,
        lease_token: str | None,
        expected_revision: int | None,
        disposition: IngestionDisposition,
    ) -> RepresentationCommitResult: ...

    def load_representation(
        self,
        scope: RepresentationScope,
    ) -> RepresentationAggregate | None: ...

    def record_ready_ingest(
        self,
        scope: RepresentationScope,
        *,
        source_observed_at: datetime,
        ingested_at: datetime,
        disposition: IngestionDisposition,
    ) -> DocumentHeadUpdate: ...

    def get_document_head(self, document_id: UUID) -> DocumentHead | None: ...
    def list_document_summaries(self) -> tuple[DocumentSummary, ...]: ...
    def resolve_ready_representation(
        self,
        document_id: UUID,
        *,
        version_id: str | None,
    ) -> RepresentationAggregate | None: ...
    def find_current_blocks(self, block_id: UUID) -> tuple[RepresentationBlock, ...]: ...
    def list_ingestion_events(self, document_id: UUID) -> tuple[IngestionEvent, ...]: ...
```

### Acquisition

- Absent scope inserts STAGING attempt/revision 1 and stores only the token SHA-256.
- Same owner/token with an unexpired lease returns the existing claim idempotently.
- Another unexpired owner returns BUSY without mutation.
- Expired STAGING or FAILED can be claimed with incremented attempt/revision.
- READY returns READY without mutation; the service must still verify the aggregate physically.
- Recipe fields must recompute the scope identity; immutable mismatches conflict.

### Failure

- Requires exact owner/token/revision and strictly active lease.
- Transitions STAGING to FAILED, clears lease, stores one bounded failure code and no raw exception.
- A stale worker cannot fail READY or a replacement owner's attempt.

### Ready commit

Before the call, the service verifies every CAS object and constructs a fully validated aggregate.

Inside one immediate transaction:

1. load the scoped header;
2. for READY, compare complete immutable data; equal force/concurrent retries converge, differences conflict;
3. otherwise require exact live lease proof;
4. register/compare manifest, native and block object metadata;
5. insert the complete ordered block set;
6. transition the header to READY last and clear lease state;
7. advance the document head only under observation-order rules;
8. append exactly one successful ingestion event;
9. reload and validate the full aggregate;
10. commit.

Faults at any point roll back header, blocks, head and event together. CAS objects are not deleted.

For normal first completion `owner_id`, token and revision are mandatory. For `FORCED_REPARSE` against an existing READY
aggregate they are all null and exact aggregate equality is mandatory. Mixed proof shapes are rejected.

### Ready ingest record

Used after a physically verified cache hit. Requires READY and appends `CACHE_HIT` plus a monotonic head update in one
transaction. It never mutates the representation or block rows.

### Query snapshot

`load_representation` returns header and every block projection from one read transaction. Summary/resolve/find operations
return only metadata needed for the service to select exact CAS objects. Query methods never return body columns because
SQLite stores no body.

### Reachability extension

The F003 reference snapshot includes all non-null representation manifest/native IDs and every block object ID. Historical
representations remain roots; document heads/events add no object references.

## `IngestionService`

```python
class IngestionService:
    def ingest(
        self,
        source: Path,
        *,
        profile: str = "default",
        force: bool = False,
    ) -> IngestionResult: ...
```

### Normal path

1. Safely snapshot source once into CAS.
2. Register/reuse `SourceKey("local", canonical_path)`.
3. Reuse an existing exact F003 source version without recommitting observed mtime; otherwise commit it.
4. Derive recipe/scope and acquire representation.
5. READY + not forced: verify the complete aggregate, append CACHE_HIT, parser calls zero.
6. BUSY: return/raise retryable busy; do not parse.
7. CLAIMED or forced READY: parse CAS chunks, create deterministic blocks/manifest, publish canonical records and commit.
8. On parser/normalization failure while claimed, record only a sanitized FAILED classification and re-raise a typed error.

The product composition always supplies the isolated adapter. Direct pure-adapter use is limited to adapter unit tests.

### Source and time rules

- Parser input is always `object_store.iter_chunks(version_id)`, never the source path.
- Manifest creation time is the immutable source version's first commit time, making concurrent/forced output deterministic.
- `source_observed_at` orders head updates and `ingested_at` cannot precede it.
- Existing source-version `source_modified_at` is never changed on same-byte re-observation.

## `DocumentQueryService`

```python
class DocumentQueryService:
    def list_documents(self) -> tuple[DocumentSummary, ...]: ...
    def status(self, target: str) -> SourceStatus: ...
    def outline(
        self,
        document_id: UUID,
        *,
        version_id: str | None = None,
    ) -> tuple[OutlineItem, ...]: ...
    def get(self, block_id: UUID) -> ContentBlock: ...
```

- `list_documents` is deterministic and body-free.
- `status` hashes a safely opened current source without publishing or parsing and compares it to the head; source missing
  is a status, while unsafe/corrupt state is an error.
- `outline` resolves one exact READY scope, verifies only title/heading/list structural block objects and returns bounded
  labels plus hierarchy/provenance. It does not load paragraph/code bodies.
- `get` considers current heads, requires one unambiguous matching block handle, verifies/deserializes the exact block
  object and cross-checks every catalog projection. It never reads the current source path.

## Workspace contract

```python
class LocalWorkspace:
    @classmethod
    def initialize(cls, root: Path, *, now: datetime) -> LocalWorkspace: ...

    @classmethod
    def open(cls, root: Path) -> LocalWorkspace: ...
```

Marker version 1 contains only fixed layout names and a format identifier. It is canonical JSON, written atomically only
after the CAS/catalog are valid. `open` requires the marker and current supported catalog revision. Neither method searches
parent directories or performs network access.

## CLI contract

```text
openardp init [--store PATH] [--json]
openardp ingest PATH [--profile default] [--force] [--store PATH] [--json]
openardp list [--store PATH] [--json]
openardp status PATH|DOCUMENT_ID [--store PATH] [--json]
openardp outline DOCUMENT_ID [--version VERSION] [--store PATH] [--json]
openardp get BLOCK_ID [--store PATH] [--json]
```

Every JSON invocation emits exactly one UTF-8 line on stdout:

```json
{
  "schema_version": "0.1.0",
  "ok": true,
  "command": "ingest",
  "data": {}
}
```

or

```json
{
  "schema_version": "0.1.0",
  "ok": false,
  "command": "ingest",
  "error": {"code": "representation_busy", "message": "representation is busy"}
}
```

Unknown/internal exceptions are mapped to one generic message and exit 1; their raw text is not printed. Non-`get`
responses omit complete block text. Human wording is not a compatibility contract; command semantics, exit class and JSON
shape are.

## Logging and output contract

Allowed by default:

- validated document/version/representation/block/object IDs;
- parser name/version/profile and bounded warning/failure codes;
- states, cache disposition, counts, timings and exit classification.

Prohibited by default:

- source/block body text or parser-native payload;
- source path in error logs;
- raw parser exception or SQL values;
- raw lease token/hash;
- document text interpreted as terminal control, command, path, URL or instruction.

Only successful explicit `get` returns one body record, still labelled untrusted data with instruction execution disabled.
