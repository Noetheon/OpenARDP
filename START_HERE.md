# Start here

OpenARDP is implemented feature by feature. The Spec Kit integration and Constitution are already committed; do not rerun
bootstrap during normal clone setup and do not request the full platform as one feature.

## 1. Read the project rules

Read [AGENTS.md](AGENTS.md), the [Constitution](.specify/memory/constitution.md), the
[feature map](spec-kit/FEATURE_MAP.md) and the active feature's `spec.md`, `plan.md` and `tasks.md`.

## 2. Reproduce the environment

Prerequisites are Git and uv 0.11.31. The repository selects Python 3.12.

```bash
uv sync --all-extras --locked
```

uv stores this derived environment in its disposable cache and attempts to expose the normal `.venv` discovery link. It
can resolve the cached environment directly if a file provider blocks that link; no manual path setting is required.

## 3. Run every mandatory gate

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

## 4. Enable and exercise commit-time checks

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

## 5. Validate the implemented contracts

Feature 002 provides strict Manifest, Block, Derivation, Relation and Context Bundle models plus deterministic public
schemas and identities. Its focused offline acceptance scenarios are in
[the feature quickstart](specs/002-domain-models-schemas/quickstart.md). The shortest schema drift check is:

```bash
uv run --locked python scripts/generate_schemas.py --check
```

These are pure contracts, not document-processing behavior. No parser, persistence, retrieval, context compiler, MCP or
product CLI is implied by the schema check.

Feature 003 additionally provides the local filesystem CAS, SQLite catalog, durable fenced jobs and advisory read-only
reachability as Python library APIs. Its focused offline acceptance commands are in
[the F003 quickstart](specs/003-cas-sqlite-catalog/quickstart.md). The complete focused persistence suite is:

```bash
uv run --locked pytest tests/integration tests/security/test_storage_boundaries.py --no-cov
```

F003 does not parse documents, mark an F002 representation `READY`, index content or delete reachability candidates.
Feature 004 is the next bounded work package in the feature map.

For contribution rules, security reporting and evidence, use [CONTRIBUTING.md](CONTRIBUTING.md),
[SECURITY.md](SECURITY.md) and [VALIDATION.md](VALIDATION.md).

The bootstrap/recovery procedure remains documented in [the Spec Kit integration guide](docs/12_SPEC_KIT_INTEGRATION.md)
and [step-by-step guide](docs/13_STEP_BY_STEP_USER_GUIDE.md).
