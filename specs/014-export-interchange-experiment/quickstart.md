# Quickstart: Export and Interchange Experiment

## 1. Install and run focused tests

```bash
uv sync --frozen
uv run pytest \
  tests/domain/test_interchange.py \
  tests/contract/test_interchange_port.py \
  tests/integration/test_bagit_interchange.py \
  tests/security/test_interchange_boundaries.py \
  tests/test_interchange_conformance.py
```

All fixtures are synthetic and validation runs without network access.

## 2. Check deterministic vectors

```bash
uv run python scripts/generate_interchange_vectors.py --check
uv run python scripts/validate_interchange_package.py \
  conformance/interchange/v0.1.0/valid/minimal.zip
```

The generator must reproduce normative vector bytes. The independent validator imports
no workspace, SQLite, parser, model or provider adapter.

## 3. Exercise operator commands

```bash
uv run openardp package-export \
  --request /tmp/openardp-synthetic-request.json \
  --destination /tmp/openardp-synthetic.zip \
  --json

uv run openardp package-verify \
  --package /tmp/openardp-synthetic.zip \
  --json

uv run openardp package-import \
  --package /tmp/openardp-synthetic.zip \
  --destination /tmp/openardp-imported-snapshot \
  --json
```

Use only synthetic/permitted assets. The imported directory is a separately
inspectable immutable snapshot, not a live OpenARDP workspace.

## 4. Full quality gate

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv build
uv run python scripts/generate_schemas.py --check
uv run python scripts/generate_interchange_vectors.py --check
uv run python scripts/validate_repository.py
```

## Expected evidence

- BagIt/profile ADR and candidate matrix cover all published criteria.
- Golden valid packages regenerate byte-for-byte.
- Every invalid vector has one stable rejection category.
- Failed verification/import leaves the destination absent or unchanged.
- Output contains no local path, body, secret or legal/trust overclaim.
- Linux, macOS and Windows CI agree before merge and again on `main`.
