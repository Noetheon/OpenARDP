# Implementation Plan: Minimum Relevance and Explicit Abstention

**Branch**: `codex/f026-relevance-abstention` | **Date**: 2026-08-03 | **Spec**: [spec.md](spec.md)

## Summary

Add an opt-in deterministic lexical relevance policy around the existing verified context-candidate sources. A decorator
re-evaluates only CAS-verified candidate bodies, attaches body-free integer relevance facts, and the compiler rejects
below-floor candidates after freshness/trust checks but before budget selection. A zero-candidate or all-below-floor
result emits explicit abstention notices. The default legacy composition and its algorithm identity remain available;
the improved CLI composition and F026 benchmark use a separately identified algorithm profile.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Existing Pydantic v2, SQLite/CAS and stdlib Unicode/regular-expression support; no new package

**Storage**: Existing immutable CAS context bundle and selection receipt; relevance audit facts use the receipt's existing
absolute-URI extension namespace and require no catalog migration

**Testing**: pytest with branch coverage, Ruff, strict mypy, repository validator, schema drift checks, build, pre-commit

**Target Platform**: Linux, macOS and Windows local CLI/library

**Project Type**: Provider-neutral Python library and CLI in a modular local monolith

**Performance Goals**: F026 comparison completes within five minutes; relevance work is linear in verified candidate
body size and remains inside existing discovery/body limits

**Constraints**: Offline, deterministic integer decisions, no benchmark-oracle input, no source mutation, no unverified
index-body authority, no ranking/diversity/CSV/translation implementation

**Scale/Scope**: Existing maximum 32 scopes, 10,000 discoveries, 512 candidates and 8 MiB candidate body bound

**Contract/Version Impact**: Additive experimental algorithm profile and existing extension data only. No application,
workspace, public schema, provider-profile or export-profile version changes; context bundle/receipt versions stay fixed.

**Trust/Operational Impact**: Task and document remain untrusted data. Relevance reads are reverified through CAS; no
network, tool authority or new secret/path output. Integrity, cancellation and resource failures remain fail-closed.

## Constitution Check

| Principle | Plan response | Gate |
|---|---|---|
| Source truth | Relevance changes only disposable candidate eligibility; originals and exact evidence stay authoritative. | PASS |
| Disposable accelerators | Scores are recomputable heuristic facts, never evidence or trust. | PASS |
| Provider neutrality | No provider interface or dependency is introduced; F029 owns query-provider work. | PASS |
| Thin evidence | No new document representation or duplicated body is stored. | PASS |
| Data not instruction | Task/content only influence a pure score and cannot initiate tools. | PASS |
| Determinism | NFC/casefold/token rules, integer weights, floor and policy identity are frozen. | PASS |
| Progressive context | Weak evidence is rejected before budget allocation and explicit abstention is surfaced. | PASS |
| Test-first | Boundary, failure distinction, replay and F025 non-regression tests precede implementation. | PASS |
| Measured claims | Unchanged F025 IDs and unfavorable outcomes remain binding. | PASS |
| Small PR | F026 excludes ranking, diversity, CSV and query expansion. | PASS |
| Cross-platform | No platform-specific tokenizer or floating-point decision is used. | PASS |
| Contract governance | Existing extension mechanism and injected algorithm identity avoid schema/version mutation. | PASS |

Post-design re-check: all gates remain PASS; no ADR exception or new public abstraction is required.

## Architecture and Data Flow

```text
exact task + existing candidate sources
                 |
                 v
       verified candidate discovery
                 |
                 v
  RelevanceFilteringCandidateSource
  - reverify CAS object
  - normalize bounded task/body terms
  - compute integer coverage/floor facts
                 |
                 v
 ContextCompiler freshness/trust/dedupe
                 |
       +---------+----------+
       |                    |
 below floor           meets floor
 rejected receipt      existing budget selection
       |                    |
       +---------+----------+
                 |
 zero survivors -> explicit abstention notices
```

Trust/sensitivity/freshness classification remains authoritative and precedes the relevance reason in the compiler.
The decorator never accepts an accelerator body without verifying and decoding its referenced CAS object.

## Project Structure

```text
specs/026-relevance-abstention/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/context-relevance.md
├── checklists/
└── tasks.md

src/openardp/
├── domain/context_relevance.py
├── domain/context_compilation.py
├── adapters/context_relevance.py
├── services/context_compiler.py
└── interfaces/cli.py

tests/
├── domain/test_context_relevance.py
├── unit/test_context_relevance.py
├── integration/test_context_relevance.py
└── security/test_context_relevance_boundaries.py
```

**Structure Decision**: Keep pure policy/score models in `domain`, verified object adaptation in `adapters`, exhaustive
partition/notice behavior in the existing compiler service and composition only in the CLI/F026 harness. No new port is
justified because F026 has one pure deterministic policy implementation and F029 owns multi-provider abstraction.

## Implementation Phases

### Phase A - Freeze contract and failure distinctions

1. Add pure policy, token-signal and integer-boundary tests.
2. Add receipt-extension and abstention-notice contract tests without changing schema versions.
3. Add trust/integrity/cancellation/truncation tests proving failures are not abstention.

### Phase B - Implement relevance evaluation

1. Implement bounded Unicode normalization, informative signals, exact token/identifier matches and integer floor.
2. Decorate existing verified candidate sources and reverify every scored body.
3. Extend internal candidates with optional relevance observations and project those facts through existing extensions.

### Phase C - Integrate compiler and CLI

1. Apply relevance after freshness/trust/sensitivity/deduplication and before budget selection.
2. Emit explicit bundle/receipt notices only for genuine evidence abstention.
3. Bind the policy to a new injected algorithm identity; retain the legacy default composition for historical replay.
4. Compose the improved profile in CLI context compilation.

### Phase D - Measure and converge

1. Run unchanged F025 unsupported and prior-success questions twice.
2. Validate result identity, privacy and non-regression.
3. Run all repository gates and complete Spec-Kit analysis/convergence.

## Risk Controls

- **Overfitting**: runtime cannot import or receive question fixtures, atoms, expected sources or evaluation labels.
- **False abstention**: previously successful direct questions are a hard non-regression gate; identifiers receive explicit
  deterministic weight rather than length-only removal.
- **Hidden failure**: only successful discovery/classification can emit abstention; exceptions retain typed failures.
- **Receipt ambiguity**: each candidate remains in one exhaustive partition with relevance facts in a namespaced extension.
- **Historical replay**: legacy algorithm identity remains explicit and constructible; F026 is opt-in composition.
- **Platform drift**: use Python-defined Unicode normalization and integer cross-multiplication, not locale or floats.
- **Body leakage**: audit facts contain counts, score and policy identity only.

## Complexity Tracking

No constitution violation or exception is required.
