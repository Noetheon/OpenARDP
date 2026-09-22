# Implementation Plan: Secure development test runner

**Branch**: `codex/pytest-security-update` | **Date**: 2026-09-23 | **Spec**: [spec.md](spec.md)

**Input**: High-assurance supply-chain maintenance requirement in `spec.md`.

## Summary

Raise only the pytest dev-group floor from vulnerable 8.x to the first patched 9.0.3 release, retain the existing major-version upper bound pattern, and regenerate the lock while holding all other package versions fixed. Verify plugin compatibility and all unchanged local quality gates. Record unaffected optional advisories honestly. No runtime, schema, pilot or release decision change.

## Technical Context

**Language/Version**: Python >=3.12,<3.13.

**Primary Dependencies**: pytest in dev group; pytest-cov 6.3.0 and pytest-socket 0.8.0 remain unchanged; uv 0.11.31 resolves/locks.

**Storage**: None; only dependency metadata changes.

**Testing**: Existing Ruff, Ruff format, strict mypy, pytest with socket denial and branch coverage >=85%, repository validation, lock/audit checks.

**Target Platform**: Linux, macOS and Windows in repository CI; local implementation check on macOS.

**Project Type**: Python package and CLI with optional extras.

**Performance Goals**: No performance claim or benchmark change.

**Constraints**: No unrelated package-version drift, plugin removal, test weakening, runtime requirement edit, optional-extra edit, networked unit test or full dependency-graph clean claim.

**Scale/Scope**: One dev requirement, one locked package version and hashes, one maintenance record.

**Contract/Version Impact**: None for application, workspace, public contract, provider profile and export profile; contributor dev environment moves to pytest 9.

**Trust/Operational Impact**: Removes a known local-test-runner tmpdir advisory from the dev environment. Existing optional model advisories are unaffected; no network operation is enabled in product or tests. Contributors resync the lock. CI must validate all three platforms before merge.

## Constitution Check

- Article III local-first/provider independence: pass; dev-only dependency, no product egress.
- Article VIII test gates: pass if full unchanged suite, socket denial and coverage floor pass.
- Article IX claims: pass if only pytest advisory closure is claimed after audit; optional advisories remain disclosed.
- Article XI high assurance: full lifecycle, supply-chain/license review and locked gates required. This plan provides them.
- Article XII ADR: not required. The change introduces no architecture, public contract, persisted identity, release decision or exceptional dependency policy.

Re-check after design: no new data or interface contracts; all five gates remain satisfiable without exception.

## Project Structure

### Working documentation

```text
specs/039-pytest-security-maintenance/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   ├── requirements.md
│   └── supply-chain.md
├── tasks.md
└── implementation-notes.md
```

### Changed repository surfaces

```text
pyproject.toml             # pytest dev constraint only
uv.lock                   # pytest resolution and distribution hashes only
spec-kit/FEATURE_MAP.md   # maintenance record outside product roadmap
specs/039-pytest-security-maintenance/  # high-assurance evidence
```

The temporary `.specify/feature.json` locator points to F039 during the lifecycle, then returns to F038 after convergence because the prospective F038 human pilot remains the active product continuation. The contract test's F038 locator assertion therefore remains valid. No application code or test assertions change.

**Structure Decision**: Preserve the existing Python package/CLI and committed lock. No new component is needed.

## Complexity Tracking

None. No constitution exception or additional abstraction is proposed.
