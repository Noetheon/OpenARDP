# Quickstart: Context Compiler and Selection Receipts

## Install and initialize

```bash
uv sync --all-extras --locked
uv run --locked openardp init --store .openardp --json
```

## Prepare mixed evidence

```bash
uv run --locked openardp ingest notes.md --store .openardp --json
uv run --locked openardp ingest report.docx --store .openardp --json
uv run --locked openardp list --store .openardp --json
```

Capture the two document IDs from the body-free list result.

## Compile bounded context

```bash
uv run --locked openardp context \
  "Which exact controls are documented?" \
  --document DOCUMENT_ID_1 \
  --document DOCUMENT_ID_2 \
  --budget 12000 \
  --unit tokens \
  --mode verification \
  --store .openardp \
  --json
```

Expected:

- one bundle ID and one receipt ID;
- exact sorted source/representation scopes;
- usage plus response reserve no greater than 12,000;
- selected count and body-free omission/rejection/stale counts;
- no network/model/provider execution during compilation.

Use `--include-bundle` only when the bounded evidence payload is intentionally needed.

## Inspect the body-free receipt

```bash
uv run --locked openardp context-receipt RECEIPT_ID \
  --store .openardp \
  --json
```

The output contains task digest, policy, estimator, scopes, accounting and all decision
inventories. It must not contain the task string, evidence bodies or local source paths.

## Stable repeat and replay

Repeat the context command with identical arguments, then run:

```bash
uv run --locked openardp context \
  "Which exact controls are documented?" \
  --replay RECEIPT_ID \
  --unit tokens \
  --store .openardp \
  --json
```

Expected: byte-identical bundle/receipt objects and the same identities. The estimator
unit must match the recording (the default is `bytes`). A different task or estimator
returns a stable mismatch error rather than recompiling silently.

## Explicit index recovery

Context compilation never repairs an index implicitly. If text coverage is reported
drifted:

```bash
uv run --locked openardp reindex --store .openardp --json
```

Review the result, then rerun compilation.

## Required local validation

```bash
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy src
uv run --locked mypy src --platform win32
uv run --locked pytest
uv run --locked python scripts/generate_schemas.py --check
uv run --locked python scripts/validate_evidence_contracts.py \
  conformance/evidence/v0.1.0/manifest.json
uv run --locked python scripts/validate_repository.py
git diff --check
uv build
```

The implementation notes record exact counts, frozen hashes, wheel probes, migration,
tradeoffs, rollback and remote Linux/macOS/Windows evidence.
