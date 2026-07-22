# Implementation Plan: Repository Baseline

**Branch**: `main` (feature locator: `001-repository-baseline`) | **Date**: 2026-07-22 | **Spec**:
[spec.md](spec.md)

**Input**: Feature specification from `specs/001-repository-baseline/spec.md`

## Summary

Create a reproducible Python 3.12 repository foundation whose locked environment, importable package skeleton, offline
quality gates, least-privilege cross-platform CI and governance documents are independently verifiable. Remove the
blueprint's premature document models, hashing helpers and CLI so later work packages reintroduce them only through their
own Spec Kit lifecycle. Keep runtime dependencies empty; use the locked development toolchain for repository validation.

## Technical Context

**Language/Version**: Python `>=3.12,<3.13`; `.python-version` selects the 3.12 series; project configuration requires uv
0.11.31

**Primary Dependencies**: No runtime dependencies; Hatchling build backend; development group contains Ruff, mypy, pytest,
pytest-cov, pytest-socket, jsonschema and pre-commit, with exact transitive versions recorded in `uv.lock`

**Storage**: N/A; no runtime state or persistence is introduced

**Testing**: Pytest with strict configuration, branch coverage and an 85 percent failure threshold; pytest-socket blocks
network; repository-contract tests cover package boundaries, metadata, JSON Schema syntax, local Markdown links,
governance artifacts, CI security and pre-commit coverage

**Target Platform**: Current GitHub-hosted Linux, macOS and Windows runners on Python 3.12; local development on the same
operating-system families

**Project Type**: Installable Python library foundation with hexagonal package boundaries and no product CLI

**Performance Goals**: N/A for product runtime; feature 001 makes no latency, throughput, cost or sustainability claim

**Constraints**: Unit tests and documentation checks run without network access; CI has read-only content permission,
non-persistent checkout credentials, immutable action revisions and locked dependency verification; no cloud/model/parser,
database, ingestion or retrieval behavior

**Scale/Scope**: One package, five empty architectural boundary packages, one public package-version constant, one
cross-platform CI matrix and offline repository-contract tests

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

| Article | Pre-design result | Post-design result | Evidence |
|---|---|---|---|
| I — Evidence Preservation | Pass / not invoked | Pass / not invoked | No document or source-file behavior exists. |
| II — Derived Data Is Disposable | Pass / not invoked | Pass / not invoked | No derived artifact, index or embedding exists. |
| III — Local-First and Provider-Neutral | Pass | Pass | Runtime dependency set is empty; test execution is offline and no provider is configured. |
| IV — Untrusted Document Boundary | Pass / not invoked | Pass / not invoked | No parser, document input or tool surface exists. |
| V — Determinism, Identity and Atomicity | Pass / deferred | Pass / deferred | The lock state is deterministic; persisted identity and writes remain outside this feature. |
| VI — Progressive Context Delivery | Pass / not invoked | Pass / not invoked | No retrieval or context behavior exists. |
| VII — Test-First Quality Gates | Pass | Pass | Strict lint, format, mypy, offline pytest, branch coverage, pre-commit and CI are planned and tested. |
| VIII — Measured Claims | Pass | Pass | The plan makes no performance or quality claim beyond reproducible gate outcomes. |
| IX — Simplicity and Incremental Delivery | Pass | Pass | Only the repository baseline remains; premature product scaffold behavior is removed. |
| X — Specification and Decision Governance | Pass | Pass | Spec, research, plan, contracts, tasks, analysis and convergence remain under the active feature. |

No constitutional exception or new ADR is required. Proposed ADRs 0001, 0002 and 0005 are unaffected; accepted blueprint
ADRs 0003 and 0004 remain binding but are not implemented in this baseline.

## Design Decisions

1. Treat `uv.lock`, not open dependency ranges, as the reproducible resolved environment. Use `uv sync --all-extras
   --locked` where drift must fail; `--frozen` is rejected there because it deliberately skips lock freshness validation.
2. Put development tools in the standard `dev` dependency group, which uv includes by default, while retaining the
   blueprint's documented `--all-extras` setup command for forward compatibility with later optional adapters. Enable
   only uv's `centralized-project-envs` preview so the standard `.venv` discovery link points to a disposable environment
   outside file-provider-managed workspace paths; the exact uv pin bounds the preview contract.
3. Keep `src/openardp/__init__.py`, a `py.typed` marker and the five architecture-boundary `__init__.py` modules. Delete
   `core.py`, domain models, the placeholder CLI and their tests because they implement work packages 1 and 3 prematurely.
4. Enforce source docstrings with Ruff and strict types with mypy. Repository tests remain fully typed but are exempt from
   public-API docstring rules.
5. Use pytest-socket as the test-runner network guard and verify the guard with a synthetic blocked-socket test.
6. Use a standard-library repository validator for local Markdown paths/anchors and governance consistency; test its
   negative cases under pytest instead of relying on a one-off external link checker.
7. Use local pre-commit hooks that call the locked project toolchain; do not create a second independently resolved hook
   environment.
8. Pin `actions/checkout` v7.0.1 and `astral-sh/setup-uv` v9.0.0 to verified full commit revisions, disable checkout
   credential persistence, disable the action cache for the first deterministic baseline and keep permissions read-only.
9. Adopt the Apache-2.0 text already declared and recommended by project metadata while retaining the blueprint's explicit
   ownership and trademark release caveat.

See [research.md](research.md) for rationale and rejected alternatives.

## Project Structure

### Documentation (this feature)

```text
specs/001-repository-baseline/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── implementation-notes.md
├── checklists/
│   ├── requirements.md
│   └── repository-baseline.md
├── contracts/
│   └── repository-baseline.md
└── tasks.md
```

### Repository root

```text
.github/workflows/ci.yml
.pre-commit-config.yaml
.python-version
AGENTS.md
CHANGELOG.md
CONTRIBUTING.md
LICENSE
README.md
SECURITY.md
START_HERE.md
VALIDATION.md
pyproject.toml
uv.lock
scripts/validate_repository.py
src/openardp/
├── __init__.py
├── py.typed
├── adapters/__init__.py
├── domain/__init__.py
├── interfaces/__init__.py
├── ports/__init__.py
└── services/__init__.py
tests/
├── test_package.py
└── test_repository_contract.py
```

**Structure Decision**: Retain the documented modular-monolith package boundaries as empty, documented namespaces. This
provides an installable target for tooling without inventing interfaces before two implementations justify them. Baseline
tests live in one flat test suite because no domain/unit/integration hierarchy is warranted yet. Repository validation is
a development script outside the installed package.

## Validation Strategy

1. Generate the lock with the project-required uv version and synchronize all declared environments with `--locked`.
2. Run Ruff lint and format checks, strict mypy and offline pytest with branch coverage.
3. Validate the pre-commit configuration, then execute all hooks against all tracked files.
4. Prove negative cases through repository-contract assertions: network socket blocked; mutable CI actions rejected;
   product modules/entry points absent; malformed, missing, non-portable and escaping Markdown targets reported; metadata,
   license and version consistent.
5. Build wheel and source distributions, install the wheel into an isolated environment and smoke-test the public import.
6. Re-run every gate and confirm `git diff --check` plus `git status --short` reveal only intended files.
7. Record macOS results locally, then retain the successful GitHub-hosted Ubuntu, macOS and Windows run URL and head SHA
   as the authoritative cross-platform execution evidence.

## Trade-offs and Risks

- Exact uv pinning improves reproducibility but requires an explicit maintenance change for tool upgrades.
- Static repository tests prove workflow configuration and pinning locally; GitHub Actions run `29926478593` supplies the
  corresponding observed runner-image evidence for all three operating-system families.
- Apache-2.0 consistency can be established locally; public release still requires ownership, employer-IP, naming and
  trademark clearance.
- Offline local-link validation does not establish availability or correctness of external references.
- Removing premature scaffold behavior intentionally reduces apparent functionality now, but prevents unreviewed domain
  and identity contracts from becoming accidental compatibility obligations.
