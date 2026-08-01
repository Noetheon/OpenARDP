# Quickstart: Visual Evidence Escalation

Commands below describe the delivered F011 surface.

## 1. Install the optional local visual capability

```bash
uv sync --extra docling --extra visual
```

The core install remains local and does not include or invoke a renderer. The visual
extra is exactly locked and performs no model download or network call.

## 2. Initialize or upgrade a workspace

```bash
uv run openardp init --store /absolute/workspace
```

Initialization upgrades a valid revision-7 workspace transactionally to revision 8.
Back up the workspace before upgrading; older binaries reject revision 8 and rollback
requires restoring the backup, not editing migration history.

## 3. Ingest a PDF and list evidence

```bash
uv run openardp ingest /absolute/document.pdf --store /absolute/workspace --json
uv run openardp evidence DOCUMENT_ID --store /absolute/workspace --json
```

Choose an accepted page, picture, table-cell or page-region projection id from the
body-free evidence list.

## 4. Materialize visual evidence explicitly

```bash
uv run openardp visual-materialize DOCUMENT_ID EVIDENCE_PROJECTION_ID \
  --store /absolute/workspace --json
```

The response returns only registered identifiers, dimensions, granularity, warnings and
an opaque CAS handle by default. It never returns a local path. Repeating the exact
request verifies and reuses the existing page/crop/descriptor objects.

Unsupported DOCX/PPTX rendering or absent table/picture geometry returns a stable
unavailable error and does not fabricate evidence.

## 5. Inspect a descriptor

```bash
uv run openardp visual-evidence VISUAL_EVIDENCE_ID \
  --store /absolute/workspace --json
```

Inspection verifies catalog bindings plus descriptor/page/crop objects before returning
the descriptor. Image bytes remain handle-only.

## 6. Compile visual context

Before materialization:

```bash
uv run openardp context "Compare the layout" --document DOCUMENT_ID \
  --budget 12000 --unit bytes --mode visual --include-bundle \
  --store /absolute/workspace --json
```

The bundle reports `visual_evidence_required`. After explicit materialization, the same
current-snapshot request can select a verified `visual_handle`. A newer document head
does not silently reuse the old visual record.

## 7. OCR/caption provider boundary

F011 ships no OCR or caption engine and no CLI flag that silently enables one. Library
integrators may supply an explicit offline `VisualInterpreter`; accepted outputs are
published as F010 derivations with model-derived/untrusted classification and exact crop
dependency. Low-confidence OCR never replaces its crop handle.

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

All unit and integration tests run with network disabled. Provider smoke tests use only
synthetic or redistributable local fixtures.

## 9. Recovery and rollback

- A failure before SQLite commit may leave complete unreachable page/crop/descriptor
  objects; they are harmless F013 recovery candidates.
- A committed visual record is immutable and must never be hand-edited.
- To roll back the feature branch, revert code and restore a pre-revision-8 workspace
  backup. Do not delete migration rows or CAS objects manually.
