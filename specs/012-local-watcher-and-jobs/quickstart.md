# Quickstart: Local Watcher and Stable Jobs

Commands below are validated against the delivered F012 CLI. Paths must name their
canonical directory components; a symlinked alias such as `/tmp` on some macOS systems
is intentionally rejected, while the corresponding canonical `/private/tmp` path is
accepted.

## 1. Prepare disjoint locations

```bash
mkdir -p /absolute/openardp-workspace /absolute/documents
uv run openardp init --store /absolute/openardp-workspace
```

The watched root and workspace must not overlap in either direction. Back up an existing
revision-8 workspace before initialization upgrades it to revision 9.

## 2. Run one deterministic foreground cycle

```bash
uv run openardp watch /absolute/documents \
  --store /absolute/openardp-workspace \
  --once \
  --stability-ms 2000 \
  --json
```

The first observation is normally a candidate. After the file remains unchanged across
the stability window, another cycle schedules and processes bounded work. Output is
body/path-free and reports opaque root/job ids and counts.

## 3. Run continuous foreground polling

```bash
uv run openardp watch /absolute/documents \
  --store /absolute/openardp-workspace \
  --poll-ms 2000 \
  --stability-ms 5000
```

Stop with Ctrl-C. This is not a daemon and does not install a service. It opens no
network listener and does not add MCP write tools. Interrupt exits with status 130.

## 4. Configure rich ingestion explicitly

```bash
uv run openardp watch /absolute/documents \
  --store /absolute/openardp-workspace \
  --once \
  --docling-model-root /absolute/models \
  --docling-model-manifest /absolute/models/manifest.json \
  --json
```

The exact same two model arguments and local Docling recipe used by explicit ingestion
apply. F012 never downloads a model. Without an explicit compatible local model bundle,
rich jobs return a stable unavailable classification.

## 5. Inspect and cancel jobs

```bash
uv run openardp jobs --store /absolute/openardp-workspace --limit 50 --json
uv run openardp job-cancel JOB_ID --store /absolute/openardp-workspace --json
```

Inspection excludes raw paths, filenames, deduplication keys, owners, tokens and
document content. Queued cancellation is immediate; running cancellation is fenced and
cooperative. It does not erase evidence already committed before cancellation.

## 6. Rename and deletion

Moving a file within the root tombstones its old path-addressed locator and treats the
new locator as a fresh candidate, even when a redacted rename hint is available.
Deletion creates a durable watcher tombstone only. OpenARDP does not delete originals,
CAS objects, versions or derived evidence in F012.

## 7. Recovery and backpressure

Every cycle recovers expired leases before scanning. Retry eligibility is persisted.
If a scan or queue bound is reached, the root is marked for rescan and later bounded
cycles converge; partial scans never infer deletions.

## 8. Validation

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv build
uv run python scripts/generate_schemas.py --check
uv run python scripts/validate_evidence_contracts.py \
  conformance/evidence/v0.1.0/manifest.json
uv run python scripts/validate_repository.py
```

## 9. Rollback

Stop foreground watchers, revert F012 code and restore the complete paired pre-revision-
9 workspace backup. Do not hand-edit SQLite constraints, migration rows, job states or
CAS objects.
