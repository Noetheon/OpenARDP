# Internal Service Contract: F012 Watcher and Jobs

This is an internal runtime contract, not a public interchange schema.

## Scanner

```python
class WatchScanner(Protocol):
    def admit(self, root: Path, *, workspace: Path, config: WatchConfig) -> AdmittedWatchRoot: ...
    def scan(self, root: WatchRoot, *, started_at: datetime) -> WatchScan: ...
```

- `admit` performs no implicit discovery and returns only validated exact authority.
- `scan` returns either one complete sorted bounded observation set or an incomplete
  body-free reason with zero observations.
- Implementations never follow links or return document bytes.

## Catalog watcher extension

```python
class WatchCatalog(Protocol):
    def register_watch_root(self, root: WatchRootRegistration) -> WatchRoot: ...
    def reconcile_watch_scan(self, scan: WatchScan, *, now: datetime) -> WatchReconciliation: ...
    def get_watch_target(self, job_id: UUID) -> WatchJobTarget | None: ...
    def list_watch_events(self, root_id: str) -> tuple[WatchEvent, ...]: ...
```

The reconciliation call is one transaction and never accepts partial entries.

## Generic job extensions

```python
def request_job_cancellation(job_id: UUID, *, now: datetime) -> Job: ...
def acknowledge_job_cancellation(
    job_id: UUID,
    *,
    owner_id: str,
    lease_token: str,
    expected_revision: int,
    now: datetime,
) -> Job: ...
```

Existing `fail_job` accepts an optional retry eligibility instant. Existing
`claim_job` filters and orders on `available_at`. Existing complete/fail/renew require
that cancellation is not pending. Raw tokens never leave `JobLease`.

## Ingestion runner

```python
class WatchIngestionRunner(Protocol):
    def ingest(self, path: Path, *, profile: str, cancelled: Callable[[], bool]) -> object: ...
```

The service supplies only a path reconstructed inside an admitted root. A runner must
reuse existing ingestion services and check cancellation at orchestration boundaries;
it must not interpret file content as configuration or commands.

## Failure taxonomy

Stable machine classifications only:

- `watch_root_invalid`, `watch_root_overlap`, `watch_root_unsupported`;
- `scan_incomplete`, `scan_overflow`, `scan_root_changed`;
- `source_changed`, `source_unavailable`, `source_unsupported`;
- `parser_unavailable`, `ingestion_busy`, `ingestion_failed`;
- `job_cancelled`, `job_conflict`, `workspace_incompatible`.

Adapters may chain private exceptions internally, but persisted events and CLI errors
must not include exception strings, roots, locators or filenames.
