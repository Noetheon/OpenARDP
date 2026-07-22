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

## 5. Understand the current boundary

Feature 001 provides the repository baseline only. No product CLI or document-processing capability is implemented yet.
Continue with feature 002 only after feature 001 converges and all checks pass.

For contribution rules, security reporting and evidence, use [CONTRIBUTING.md](CONTRIBUTING.md),
[SECURITY.md](SECURITY.md) and [VALIDATION.md](VALIDATION.md).

The bootstrap/recovery procedure remains documented in [the Spec Kit integration guide](docs/12_SPEC_KIT_INTEGRATION.md)
and [step-by-step guide](docs/13_STEP_BY_STEP_USER_GUIDE.md).
