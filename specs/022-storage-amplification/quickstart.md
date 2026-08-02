# Quickstart: Validate Storage Amplification Reduction

## Prerequisites

- Python 3.12 through the locked `uv` environment.
- No network access.
- A fresh visible-path output directory with enough free space for the bounded scale run.

## Fresh-workspace behavior

```bash
uv run --locked pytest \
  tests/unit/test_compact_objects.py \
  tests/integration/test_filesystem_cas.py \
  tests/integration/test_document_query.py \
  tests/security/test_storage_compaction_boundaries.py --no-cov
```

Expected: ordinary/compact reads are byte-identical; injected envelope and duplicate faults fail closed; normalized search
coverage and rebuild remain exact.

## Existing-workspace migration

```bash
uv run --locked pytest \
  tests/integration/test_f022_migration.py \
  tests/integration/test_backup_restore.py \
  tests/integration/test_storage_optimization.py --no-cov
```

Expected: revision 10 requires explicit backup-first migration, revision 11 opens without hidden writes, optimization is
idempotent across every injected interruption and the backup restores exact revision-10 evidence.

## Reproduce storage evidence

```bash
uv run --locked python scripts/run_storage_benchmark.py \
  --output /path/to/fresh-storage-result

uv run --locked python scripts/validate_storage_benchmark.py \
  --output /path/to/fresh-storage-result
```

Expected: the validator recomputes `PASS` only when both profiles are at most 15x logical amplification, reduction is at
least 60 percent, the binding reference allocation is at most 55x and all semantic/migration/integrity checks pass.

## Complete gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run python scripts/validate_repository.py
uv build
uv run pre-commit run --all-files
```

All commands must complete offline. See [storage-optimization.md](contracts/storage-optimization.md) for the closed
operation contract and [data-model.md](data-model.md) for physical/logical state semantics.
