# Contributing to OpenARDP

OpenARDP is built in small, independently testable Spec Kit features. Read [AGENTS.md](AGENTS.md), the
[Constitution](.specify/memory/constitution.md), the relevant accepted ADRs and the active feature artifacts before making
a production-relevant change.

## Prerequisites

- Git
- uv 0.11.31
- A checkout on Linux, macOS or Windows

The project selects Python 3.12 through `.python-version`; a newer global Python is not the project runtime.

## Set up the locked environment

```bash
uv sync --all-extras --locked
```

If `pyproject.toml` and `uv.lock` disagree, do not bypass the failure with `--frozen`. Update dependencies intentionally,
review the lock diff and commit both artifacts together. The exact uv pin bounds the enabled `centralized-project-envs`
preview; no per-shell environment override is required.

## Mandatory quality gates

Run all four before requesting review:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

Pytest includes branch coverage, an 85 percent failure threshold, offline repository/documentation validation and a socket
block. Unit fixtures must be synthetic or legally redistributable.

## Commit-time checks

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

The local hooks call the same locked Ruff, format, mypy and pytest gates; they do not resolve an independent toolchain.

## Spec Kit lifecycle

Production-relevant features follow the order in [spec-kit/FEATURE_MAP.md](spec-kit/FEATURE_MAP.md):

```text
specify → clarify → plan → checklist → tasks → analyze → implement → converge
```

- Correct conflicts in the highest-level originating artifact.
- Do not implement while analysis has an unresolved critical or high finding.
- Work only on the active feature and selected task phase.
- Add tests before behavior where practical, then mark only completed tasks.
- Do not start a dependent feature until the current one converges.

## Pull-request expectations

- Keep one bounded feature or maintenance concern per pull request.
- Explain the user/operator outcome, tests, security impact and compatibility impact.
- Include exact commands and results, not only “tests pass”.
- Update schemas, docs, ADRs and the changelog when their contracts change.
- Keep originals immutable, derived data reproducible and document content outside instruction/tool authority.
- Disclose licenses, model downloads, network behavior and data egress for every future provider integration.

## Dependencies and architecture

Dependencies point inward: `domain` has no I/O; `ports` define provider-neutral contracts; `adapters` perform I/O;
`services` orchestrate use cases; `interfaces` expose them. Do not add an abstraction until two implementations justify it
or an ADR records the immediate need.

Runtime dependencies, cloud calls, persisted identifiers and public schema guarantees are product decisions. Introduce
them only through their mapped feature and, where required, an accepted ADR.

## Security reports

Do not put exploit details, credentials or confidential documents in a public issue. Follow [SECURITY.md](SECURITY.md).
