# Quickstart: Docling Native Adapter

## Install

Core-only contract consumers:

```bash
uv sync --locked
```

Rich-parser development/runtime:

```bash
uv sync --all-extras --locked
```

The `docling` extra is local but not model-free for the PDF pipeline. OpenARDP does not
download models.

## Initialize

```bash
uv run --locked openardp init --store .openardp
```

## Ingest DOCX or PPTX

```bash
uv run --locked openardp ingest example.docx --store .openardp --json
uv run --locked openardp ingest slides.pptx --store .openardp --json
```

Expected JSON identifies source/representation/native artifacts and evidence count but
does not print document bodies or local absolute paths.

Repeat unchanged input:

```bash
uv run --locked openardp ingest example.docx --store .openardp --json
```

Expected: `cache_hit=true` and `parser_invoked=false` after full integrity validation.

## Ingest PDF offline

Prepare/review a local model bundle outside the repository and create its strict
manifest. Then:

```bash
uv run --locked openardp ingest report.pdf \
  --store .openardp \
  --docling-model-root /local/reviewed/docling-models \
  --docling-model-manifest /local/reviewed/docling-models/openardp-model-bundle.json \
  --json
```

No URL is accepted. Missing or inconsistent assets fail before provider execution.

## Inspect evidence

```bash
uv run --locked openardp evidence DOCUMENT_ID --store .openardp --json
uv run --locked openardp get-evidence PROJECTION_ID --store .openardp --json
```

The first command is body-free and bounded. The second intentionally returns one exact
verified retrieval body; native payloads remain available through the programmatic
object-scoped service rather than being dumped by default.

## Forced reparse

```bash
uv run --locked openardp ingest example.docx --store .openardp --force --json
```

The result reports whether native bytes converged. Existing objects are never rewritten.

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
uv build
```

All unit/integration tests run with sockets denied. Actual DOCX/PPTX smoke fixtures are
synthetic. PDF provider execution requires separately provisioned reviewed model assets;
the no-assets failure path is mandatory in the default gate.
