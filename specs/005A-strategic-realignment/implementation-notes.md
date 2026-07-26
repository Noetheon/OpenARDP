# Implementation Notes: Strategic Realignment and Contract Boundary

**Feature**: `005A-strategic-realignment`  
**Branch**: `codex/f005a-strategic-realignment`  
**Date**: 2026-07-26  
**Rollback/base commit**: `a23c07eb2a22efa7a4004d33cf00ab6cfd6fd027`

## Restated acceptance criteria

1. Describe all delivered behavior through Feature 005 accurately, including non-authoritative lexical search.
2. Position OpenARDP as implementation-first open-source reference software; public contracts remain experimental until evidence supports stabilization.
3. Establish exactly one authoritative 005A–017 roadmap with contracts before the Docling adapter.
4. Amend the constitution without weakening any existing security, engineering, evidence, offline, or cross-platform rule.
5. Add explicit decisions for implementation-first evolution, provider-native representations, non-authoritative indexes, and contracts-before-adapters.
6. Preserve historical specifications and ADRs through explicit amendment, deferral, or supersession rather than deletion.
7. Preserve original evidence, complete provider-native artifacts, thin evidence projections, and verified authoritative records; do not introduce a second full document IR.
8. Document prior art, non-goals, claims discipline, contract lifecycle, benchmarks, release/adoption, operations, privacy, supply chain, and working-name/IP caveats.
9. Integrate every reviewed overlay artifact at a repository-appropriate path while excluding the external blueprint package and platform metadata.
10. Make no runtime, dependency-lock, persisted-identity, command, or public-schema semantic change.
11. Keep every existing quality gate green and add deterministic offline validation for the new governance boundary.
12. Finish with clean Spec Kit analysis and convergence, exact validation evidence, residual risks, and rollback instructions.

## Pre-change baseline

The clean feature worktree was created from the merged F005 commit. The earlier uncommitted F006 work remains isolated in its original worktree and is outside this feature.

| Evidence | Result |
|---|---|
| `git rev-parse HEAD` | `a23c07eb2a22efa7a4004d33cf00ab6cfd6fd027` |
| `git rev-parse HEAD:src` | `7f814bc295e63e6117fe7d58cc8257373134cf42` |
| `git rev-parse HEAD:schemas` | `7cc9af97e2dc0ac883d2e7098f922235caeb2de7` |
| `git rev-parse HEAD:pyproject.toml` | `3ffc0c9f8736e2e891f90a1b499759923f314602` |
| `git rev-parse HEAD:uv.lock` | `a632bc2ae8c26fd0523eb457d50bacac4712bf0a` |
| `uv sync --all-extras --locked` | pass; 35 packages audited |
| `uv run ruff check .` | pass |
| `uv run ruff format --check .` | pass; 65 files already formatted |
| `uv run mypy src` | pass; 32 source files |
| `uv run pytest -q` | pass; 407 tests, 86.44% branch coverage (required ≥85%) |

## Reviewed overlay accounting

The blueprint overlay contains 35 non-platform files. Each is mapped below; no external blueprint container, manifest, duplicate source tree, validator, or `.DS_Store` is a migration output.

| # | Blueprint overlay path | Reviewed repository destination/treatment |
|---:|---|---|
| 1 | `adrs/ADR-NEW-001-IMPLEMENTATION-FIRST.md` | `docs/adr/0007-implementation-first.md`; reconcile and accept |
| 2 | `adrs/ADR-NEW-002-NATIVE-REPRESENTATION.md` | `docs/adr/0008-preserve-provider-native-representations.md`; reconcile and accept |
| 3 | `adrs/ADR-NEW-003-INDEX-NONAUTHORITATIVE.md` | `docs/adr/0009-indexes-are-non-authoritative.md`; reconcile and accept |
| 4 | `adrs/ADR-NEW-004-CONTRACTS-BEFORE-ADAPTERS.md` | `docs/adr/0010-contracts-before-adapters.md`; reconcile and accept |
| 5 | `codex/MASTER_SESSION_PROMPT.md` | `codex/MASTER_SESSION_PROMPT.md`; add subordination notice |
| 6 | `conformance/README.md` | `conformance/README.md`; experimental guidance |
| 7 | `contracts/README.md` | `contracts/README.md`; experimental guidance |
| 8 | `contracts/example-selection-receipt.json` | same path; illustrative, not a public schema |
| 9 | `docs/00_REVISED_EXECUTIVE_BRIEF.md` | same path; reconcile and link to canonical entry point |
| 10 | `docs/01_VISION_AND_POSITIONING.md` | same path; reconcile and link to canonical entry point |
| 11 | `docs/02_NORMATIVE_SCOPE_CANDIDATE.md` | same path; experimental scope candidate |
| 12 | `docs/03_NON_GOALS.md` | same path |
| 13 | `docs/04_PRIOR_ART_AND_DD.md` | same path; living register |
| 14 | `docs/05_TARGET_ARCHITECTURE.md` | same path; reconcile with accepted ADRs |
| 15 | `docs/06_SECURITY_MODEL_V2.md` | same path; bounded-isolation wording |
| 16 | `docs/07_BENCHMARK_AND_EVIDENCE_PLAN.md` | same path |
| 17 | `docs/08_RELEASE_AND_ADOPTION_STRATEGY.md` | same path |
| 18 | `docs/09_CONTRACT_LIFECYCLE_AND_COMPATIBILITY.md` | same path |
| 19 | `docs/10_OPERATIONS_PRIVACY_SUPPLY_CHAIN.md` | same path |
| 20 | `spec-kit/CONSTITUTION_V3_SOURCE.md` | same path; labelled adoption source pointing to canonical constitution |
| 21 | `spec-kit/FEATURE_MAP_V3.md` | same path; labelled adoption source pointing to canonical map |
| 22 | `spec-kit/OPERATING_PROCEDURE_V3.md` | same path; labelled adoption source pointing to canonical procedure |
| 23 | `spec-kit/feature-prompts/005A-strategic-realignment.md` | same path |
| 24 | `spec-kit/feature-prompts/006-evidence-contract-foundation.md` | same path |
| 25 | `spec-kit/feature-prompts/007-docling-native-adapter.md` | same path |
| 26 | `spec-kit/feature-prompts/008-context-compiler-receipts.md` | same path |
| 27 | `spec-kit/feature-prompts/009-read-only-mcp.md` | same path |
| 28 | `spec-kit/feature-prompts/010-reconciliation-derivation-dag.md` | same path |
| 29 | `spec-kit/feature-prompts/011-visual-evidence-escalation.md` | same path |
| 30 | `spec-kit/feature-prompts/012-local-watcher-and-jobs.md` | same path |
| 31 | `spec-kit/feature-prompts/013-retention-recovery-migrations.md` | same path |
| 32 | `spec-kit/feature-prompts/014-export-interchange-experiment.md` | same path |
| 33 | `spec-kit/feature-prompts/015-benchmark-security-release-gate.md` | same path |
| 34 | `spec-kit/feature-prompts/016-alternate-parser-conformance-spike.md` | same path |
| 35 | `spec-kit/feature-prompts/017-microsoft-graph-design-spike.md` | same path |

## Test-first evidence

- `uv run --locked pytest tests/test_repository_contract.py -q` produced the expected
  red state: 14 prior repository tests passed and six new F005A tests failed because
  Constitution 2.0.0, adoption-source labels, the 005A–017 map/prompts, ADRs 0007–0010,
  experimental contract guidance and corrected entry-point claims did not yet exist.
- The focused module-only invocation also triggered the repository-wide coverage threshold
  because no package module was imported; this is expected for the red test and is avoided
  in later focused runs with `--no-cov`. The authoritative full suite retains coverage.

## Phase evidence

| Phase | Evidence |
|---|---|
| Foundation | Constitution mirror is byte-identical; focused constitution/adoption-source/ADR tests passed `3/3`. |
| US1 — claims | Entry-point status/claim contract passes; deterministic searches found no active stale lexical-search claim or unqualified standards claim. |
| US2 — roadmap | Canonical 005A–017 order, predecessor rule and exact active prompt inventory pass; obsolete prompts are absent. |
| US3 — contracts | Experimental guidance, receipt JSON, ADR supersession and native/projection/index boundaries pass. |
| US4 — adoption | Prior art, non-goals, benchmark, release, security, privacy, operations and supply-chain guidance are present and labelled by current/planned status. |
| Repository validation | `39` focused repository/governance tests passed with `--no-cov`; `scripts/validate_repository.py` reported `Repository validation passed.` |
| Runtime neutrality | `git diff --exit-code a23c07e... -- src schemas pyproject.toml uv.lock` produced no diff. |
| Final analysis/convergence | 28 requirements/success criteria, 12 acceptance scenarios, 7 edge cases, 8 plan decisions, 39 tasks and 12 constitution articles checked; zero missing, partial, contradictory or unrequested findings; no convergence tasks appended. |

## Full validation

| Gate | Result |
|---|---|
| `uv run --locked ruff check .` | pass |
| `uv run --locked ruff format --check .` | pass; 65 files already formatted |
| `uv run --locked mypy src` | pass; 32 source files |
| `uv run --locked mypy src --platform win32` | pass; 32 source files |
| `uv run --locked pytest` | pass; 415 tests, 86.45% branch coverage (required ≥85%) |
| `uv run --locked pre-commit run --all-files` after staging | pass; Ruff lint, format, strict mypy and offline pytest hooks |
| `uv run --locked python scripts/validate_repository.py` | pass; zero diagnostics |
| `uv build` | built `openardp-0.0.1.tar.gz` and `openardp-0.0.1-py3-none-any.whl` |
| isolated offline wheel import | pass; source and distribution versions both `0.0.1` |
| Feature selection/order quickstart | pass |
| `git diff --check` | pass |
| receipt JSON parse | pass |
| tracked blueprint/`.DS_Store` hygiene | pass; no match |
| prohibited-claim searches | no active stale lexical-search or unqualified standards claim |
| runtime/schema/dependency diff against `a23c07e` | empty for `src`, `schemas`, `pyproject.toml`, `uv.lock` |

## Tradeoffs and residual risks

- The three version-suffixed v3.1 source files intentionally duplicate concise reviewed inputs for migration provenance.
  Explicit “not authoritative” labels plus offline validator checks mitigate parallel-authority drift.
- Existing canonical documents were reconciled rather than deleted. Their current/planned status labels reduce ambiguity,
  but future capability changes still require synchronized documentation and repository-contract updates.
- External prior-art links and claims are reviewed as content but are not fetched by offline validation; Feature 015 must
  refresh evidence before release-facing claims.
- The illustrative selection receipt is deliberately not registered as a public schema. Feature 006 may change or reject
  its shape through the full compatibility process.
- Constitution 2.0.0 is a governance-major change. It preserves every 1.0.0 obligation while adding stricter representation,
  claim, contract and cross-platform rules; future Spec Kit upgrades must retain the propagated template additions.
- No runtime rollback or data migration risk exists because source, schemas, dependency metadata and lockfile are
  unchanged.
- Remaining external risk is bounded to cross-platform publication evidence; the same locked CI matrix must pass on the
  pull-request head and post-merge `main` before F005A is externally closed.

## Rollback

Revert the isolated F005A commit or merge commit. No runtime data migration, dependency rollback, schema downgrade, or workspace recovery is required.

## Remote verification

- Feature commit: `30c46208ead7c70955044fba16c6e79b4fbfb924`.
- Pull request [#6](https://github.com/Noetheon/OpenARDP/pull/6) merged on 2026-07-26 as
  `75defaba24a64ab79772683d643378305e8d776f`.
- PR-head workflow [30201594632](https://github.com/Noetheon/OpenARDP/actions/runs/30201594632) passed all locked gates on
  Ubuntu (57 s), macOS (37 s) and Windows (1 min 48 s).
- Post-merge `main` workflow
  [30201693013](https://github.com/Noetheon/OpenARDP/actions/runs/30201693013) passed all locked gates on Ubuntu (52 s),
  macOS (1 min 7 s) and Windows (2 min).
- Both workflows ran the 415-test network-blocked suite, distribution builds and tracked-file drift verification.
