# Contributing to OpenARDP

OpenARDP is built through small, independently testable changes with documentation proportional to risk. Read
[AGENTS.md](AGENTS.md), the [Constitution](.specify/memory/constitution.md), relevant accepted ADRs and any durable active
feature record before changing behavior or governance.

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

## Change records

Keep records in proportion to what a change can break ([Article XI](.specify/memory/constitution.md)):

- Documentation, tests, refactoring and narrow fixes need only a scoped PR with exact validation results.
- User-visible behavior, contracts, schemas, identity, migrations, security/trust boundaries, providers and default
  dependencies keep a concise `spec.md` (task served, acceptance criteria, decisions) and `implementation-notes.md`
  (commands, results, tradeoffs, rollback).
- Irreversible or architectural decisions need an accepted ADR first.

Spec Kit stages are optional tools, not gates. Name the concrete person or agent task a change improves
([Article XIII](.specify/memory/constitution.md)) and keep agent-facing output compact and verifiable
([Article XIV](.specify/memory/constitution.md)). Correct conflicts in the highest-level source and add tests before
behavior where practical.

## Pull-request expectations

- Keep one bounded feature or maintenance concern per pull request.
- Open active implementation as a draft and push intermediate revisions while it remains draft. Mark it ready only when
  it is a merge candidate; `ready_for_review` starts the complete applicable Linux/macOS/Windows final gate.
- Do not use commit-message CI skip directives on merge candidates. Governance-only skips come only from the reviewed
  fail-closed classifier; unknown or mixed changes always receive the full final gate.
- Explain the user/operator outcome, tests, security impact and compatibility impact.
- Include exact commands and results, not only “tests pass”.
- Update schemas, docs, ADRs and the changelog when their contracts change.
- Keep originals immutable, derived data reproducible and document content outside instruction/tool authority.
- Disclose licenses, model downloads, network behavior and data egress for every future provider integration.

Release evidence is a separate deliberate workflow. It runs for ready release-owned pull requests and version tags, or
through manual dispatch; ordinary changes rely on the complete core three-platform final test gate.

## Dependencies and architecture

Dependencies point inward: `domain` has no I/O; `ports` define provider-neutral contracts; `adapters` perform I/O;
`services` orchestrate use cases; `interfaces` expose them. Do not add an abstraction until two implementations justify it
or an ADR records the immediate need.

Runtime dependencies, cloud calls, persisted identifiers and public schema guarantees are product decisions. Introduce
them only through their mapped feature and, where required, an accepted ADR.

## Security reports

Do not put exploit details, credentials or confidential documents in a public issue. Follow [SECURITY.md](SECURITY.md).
