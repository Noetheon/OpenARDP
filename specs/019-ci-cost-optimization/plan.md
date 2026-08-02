# Implementation Plan: CI Cost and Latency Optimization

**Branch**: `codex/f019-ci-cost-latency` | **Date**: 2026-08-02 | **Spec**: [spec.md](spec.md)

## Summary

Replace the seven-job all-events CI topology with event- and scope-aware lanes that preserve the authoritative final
standard. A deterministic standard-library classifier fails closed, a single Ubuntu lane owns platform-independent
gates and branch coverage, macOS and Windows retain the complete test inventory without redundant coverage, draft
iterations run only preflight, `main` avoids a post-merge matrix duplicate, and unchanged F015 release reproduction
moves to a separately bounded workflow. Versioned policy and dated cost evidence make the savings and quality boundary
auditable.

## Technical Context

**Language/Version**: Python 3.12 and GitHub Actions workflow YAML

**Primary Dependencies**: Python standard library (`argparse`, `dataclasses`, `json`, `pathlib`, `re`), existing
`uv==0.11.31`, existing SHA-pinned GitHub Actions; no new dependency

**Storage**: Version-controlled JSON policy and historical aggregate cost evidence only; no runtime persistence

**Testing**: pytest unit tests for classification/audit/model behavior, repository contract tests for workflow
topology, full existing offline suite on Linux/macOS/Windows, local action/workflow static validation

**Target Platform**: GitHub-hosted `ubuntu-latest`, `macos-latest` and `windows-latest`; local Python 3.12 on macOS

**Project Type**: Python library/CLI with repository automation

**Performance Goals**: deterministic policy audit and classification complete in under one second locally; comparable
runner-cost model shows at least 55 percent gross reduction; macOS/Windows test duration removes coverage overhead

**Constraints**: final code PR still runs all tests on three platforms; coverage remains at least 85 percent; unit tests
remain network-blocked; job-level rather than workflow-level skips preserve required-check completion; release evidence
remains fail-closed; branch protection must not deadlock a solo maintainer

**Scale/Scope**: 1,381 pre-feature and 1,407 final tests, two workflows, four stable core required checks, one bounded
path classifier, 34 historical runs and 158 historical jobs in the 2026-08-01 comparison window

**Contract/Version Impact**: Developer-operations contract only. Application `0.1.0rc1`, workspace revision 10, public
schema versions, provider profiles, export profile, identities and F015 decision remain unchanged.

**Trust/Operational Impact**: Pull-request content remains untrusted; workflows use `pull_request`, read-only contents
and non-persistent credentials, never `pull_request_target`. The classifier reads repository-relative names only and
cannot execute content. Cache persistence is limited to uv artifacts and cannot bypass the lockfile. Main protection is
an external repository setting recorded and verified after merge.

## Constitution Check

### Before design

- **Articles I-II**: No source/evidence bytes or derived-artifact identity changes; F015 evidence remains unchanged.
- **Articles III-IV**: No provider, representation or dependency is introduced.
- **Article V**: Changed paths are data only; no PR content is evaluated as commands and workflow permissions are read-only.
- **Article VI**: No persisted identity, serialization or durable-write behavior changes.
- **Article VII**: Product context delivery is outside scope.
- **Article VIII**: Workflow contracts and classifier failure cases are tested before workflow replacement; coverage,
  socket denial and complete final platform suites remain mandatory.
- **Article IX**: The cost claim uses a dated aggregate snapshot, official price source, explicit formulas and limitations.
- **Article X**: One policy module and two workflows replace duplicated steps without a CI framework or reusable-workflow
  abstraction that would lack two consumers.
- **Article XI**: F019 is one bounded branch/PR and retains Linux/macOS/Windows final quality before merge.
- **Article XII**: No public or persisted product contract changes; no ADR is required.

**Gate result**: PASS.

## Project Structure

```text
.github/workflows/
├── ci.yml
└── release-evidence.yml
quality/
├── ci-policy.json
└── ci-cost-baseline-2026-08-01.json
scripts/
└── audit_ci.py
tests/
├── unit/test_ci_audit.py
└── test_repository_contract.py
spec-kit/
├── FEATURE_MAP.md
└── feature-prompts/019-ci-cost-optimization.md
specs/019-ci-cost-optimization/
├── contracts/ci-execution-policy.md
├── checklists/{requirements,ci-quality}.md
└── spec,plan,research,data-model,quickstart,tasks,analysis,implementation-notes.md
```

**Structure Decision**: CI policy is developer tooling, so its executable audit remains under `scripts/` and its
reviewed data under `quality/`; no product architecture layer imports it. Core and release workflows remain separate
because they have different authorization events, required checks and artifact lifecycles.

## Phase 0: Research

[research.md](research.md) records the observed topology/cost baseline, historical platform-specific failure evidence,
GitHub required-check behavior, uv cache safety and rejected alternatives. No unresolved clarification remains.

## Phase 1: Design and contracts

- [data-model.md](data-model.md) defines classification, quality-lane, release-boundary, policy and cost-snapshot records.
- [contracts/ci-execution-policy.md](contracts/ci-execution-policy.md) defines fail-closed classification, triggers,
  stable checks, complete-test and cache invariants.
- [quickstart.md](quickstart.md) defines local policy/classifier validation, full gates and safe Draft-to-Ready operation.
- `quality/ci-policy.json` is the machine-readable source for classification and audit invariants.
- `quality/ci-cost-baseline-2026-08-01.json` is immutable dated aggregate evidence, not live billing state.

### Post-design constitution re-check

PASS. The design eliminates redundant execution without reducing final test inventory, coverage threshold, supported
platforms, release controls or supply-chain constraints. No runtime dependency, network path or product contract is
added.

## Implementation strategy

1. Add policy parsing, unsafe-path, mixed-scope, empty-input, deterministic-audit and cost-model tests and record the
   intentional red state.
2. Implement `scripts/audit_ci.py` and the two reviewed JSON records using only the standard library.
3. Replace core CI with classification, preflight, authoritative Ubuntu quality and complete no-coverage Windows/macOS
   lanes; add ready/draft and main-event conditions.
4. Move the unchanged F015 matrix and aggregate gate into a release-boundary workflow with manual, version-tag and
   release-path pull-request triggers.
5. Update repository contracts, contributor guidance, feature map/status and cost/rollback documentation.
6. Run two deterministic audits, all local gates and the final ready private PR; merge only after three-platform success.
7. Apply and verify solo-safe `main` protection with strict stable checks, administrator enforcement and no force/delete.

## Complexity Tracking

No constitution violation or exceptional complexity is introduced.
