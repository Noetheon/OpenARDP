# Quickstart: F013 Retention and Recovery

The examples use synthetic local data and fresh disjoint paths. Maintenance commands
never discover a workspace or destination implicitly.

```bash
STORE="$(mktemp -d)/workspace"
BACKUP="$(mktemp -d)/backup-a"
RESTORED="$(mktemp -d)/restored-a"

uv run openardp init --store "$STORE"
uv run openardp storage-inventory --store "$STORE" --json
uv run openardp storage-plan --store "$STORE" > plan.json
uv run openardp storage-diagnostics --store "$STORE" --json
```

`storage-plan` is read-only. It publishes a complete content-identified plan value only
when the entire bounded workspace is consistent. The operator reviews that value before
the separate quarantine step:

```bash
uv run openardp storage-quarantine --store "$STORE" --plan plan.json
uv run openardp storage-recover --store "$STORE"
uv run openardp storage-restore --store "$STORE" --batch BATCH_ID
```

Irreversible commit is intentionally distinct and requires the named batch, elapsed
grace and exact acknowledgement:

```bash
uv run openardp storage-commit \
  --store "$STORE" \
  --batch BATCH_ID \
  --acknowledge-irreversible-removal
```

No normal command, timer, recovery or low-space path invokes this operation.

Create and verify a paired backup, then restore it to a fresh absent directory:

```bash
rmdir "$BACKUP" "$RESTORED"
uv run openardp workspace-backup --store "$STORE" --destination "$BACKUP"
uv run openardp workspace-restore --backup "$BACKUP" --destination "$RESTORED"
uv run openardp storage-inventory --store "$RESTORED" --json
uv run openardp index-rebuild --store "$RESTORED"
```

An older supported workspace is never upgraded by `open` or `init`. Migration requires
an absent paired-backup destination:

```bash
uv run openardp workspace-migrate \
  --store /safe/local/revision-9-workspace \
  --backup-destination /safe/local/pre-f013-backup
```

Recovery drill:

1. Populate state A and create `backup-a`.
2. Migrate or add state B to the original workspace.
3. Restore `backup-a` to a fresh `restored-a`.
4. Verify the manifest, inventory and rebuilt search results.
5. Confirm every A fact/object is present and every B-only fact/object is absent.

## Required validation

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
