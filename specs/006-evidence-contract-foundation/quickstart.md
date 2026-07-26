# Quickstart: Validate the Evidence Contract Foundation

## Prerequisites

- Repository checkout on the F006 branch.
- Locked Python 3.12 environment.
- No parser, cloud account, network service, catalog, or source document.

## 1. Synchronize and run focused contract checks

```bash
uv sync --all-extras --locked
uv run --locked pytest \
  tests/domain/test_evidence_contracts.py \
  tests/contract/test_evidence_schemas.py \
  tests/security/test_evidence_boundaries.py
```

Expected: all focused tests pass with network disabled.

## 2. Check deterministic schemas

```bash
uv run --locked python scripts/generate_schemas.py --check
```

Expected: all existing and F006 schemas are current; the command writes no file.

## 3. Validate the public conformance corpus

```bash
uv run --locked python scripts/validate_evidence_contracts.py \
  conformance/evidence/v0.1.0/manifest.json
```

Expected: every valid fixture is accepted, every invalid fixture fails for its declared
category, cross-record scenarios and golden identity vectors match, and the summary
contains no document body or raw pointer value.

## 4. Prove adapter independence and contract-surface hygiene

```bash
uv run --locked pytest tests/security/test_evidence_boundaries.py -q
rg -n -i \
  'docling|sqlite|filesystem[_ -]?path|ranking|model[_ -]?prompt|python[_ -]?type' \
  schemas/{native-representation,evidence-reference,evidence-projection,trust-classification}.schema.json
```

Expected: tests pass and the search produces no prohibited contract field or description.

## 5. Prove Feature 005 compatibility

```bash
git diff --exit-code 39e7f8313bdb433f3057c3ad5ebf1b141e1ee2c4 -- \
  schemas/manifest.schema.json \
  schemas/block.schema.json \
  schemas/derivation.schema.json \
  schemas/relation.schema.json \
  schemas/context-bundle.schema.json \
  tests/fixtures/domain/canonicalization-vectors.json
```

Expected: no diff.

## 6. Run the full repository gate

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run --locked python scripts/validate_repository.py
uv build
```

Expected: every command passes offline. Pull-request and post-merge CI repeat the locked
gate on Linux, macOS, and Windows.
