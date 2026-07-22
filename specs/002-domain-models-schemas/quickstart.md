# Quickstart Validation: Domain Models and Interchange Schemas

## Prerequisites

- CPython 3.12
- Repository `uv` version from `pyproject.toml`
- Locked development environment synchronized from `uv.lock`
- No network access is required after synchronization

```bash
uv sync --all-extras --locked
```

The recurring macOS file-provider warning about an empty `.venv` directory is non-fatal in this workspace; uv uses the configured centralized project environment.

## Scenario 1 — Validate and round-trip every public record

```bash
uv run --locked pytest tests/contract/test_domain_schemas.py -q
```

Expected:

- all five golden JSON files validate against Draft 2020-12 with format checking;
- each file validates through its strict model and round-trips back to schema-valid JSON;
- extensions and exact version/representation provenance remain intact;
- schema-expressible negative cases fail both paths;
- model-semantic cases are classified and fail the model path.

## Scenario 2 — Prove RFC 8785 and identity determinism

```bash
uv run --locked pytest tests/domain/test_identity.py -q
```

Expected:

- official RFC canonicalization and Unicode-sorting vectors match exact bytes/digests;
- unsafe values and duplicate raw JSON keys fail;
- domain-separated identity helpers match golden digests;
- repeated subprocesses with multiple `PYTHONHASHSEED` values produce identical output;
- semantically distinct payload changes alter their identity while documented JCS-equivalent number forms converge.

## Scenario 3 — Prove domain invariants and security labels

```bash
uv run --locked pytest tests/domain/test_models.py tests/domain/test_common.py -q
```

Expected:

- malformed UUID/hash/version/time values fail without scalar coercion;
- document content cannot set `instruction_execution_allowed=true`;
- source/version and all recomputable identity mismatches fail;
- derivation lifecycle, relation endpoint and context-scope invariants fail at the documented layer;
- unknown direct fields fail while JSON-valued extensions round-trip.

## Scenario 4 — Prove committed schemas are reproducible

Run the generator in check mode twice:

```bash
uv run --locked python scripts/generate_schemas.py --check
uv run --locked python scripts/generate_schemas.py --check
git diff --exit-code
```

Expected: both checks report all five schemas current, and the worktree remains unchanged.

Intentional regeneration after a reviewed model change:

```bash
uv run --locked python scripts/generate_schemas.py --write
```

The resulting schema diff must be reviewed together with the model, fixture, compatibility, tests and changelog impact.

## Full repository gate

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run --locked pre-commit run --all-files
uv build
git diff --check
```

Expected: every command exits successfully, tests remain network-blocked, coverage remains above the repository threshold and no F003+ module appears.

## Contract references

- [Feature specification](spec.md)
- [Data model](data-model.md)
- [Domain contract](contracts/domain-contracts.md)
- [`schemas/README.md`](../../schemas/README.md) after implementation
