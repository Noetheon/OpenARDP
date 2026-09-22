# Feature Specification: Secure development test runner

**Feature Branch**: `codex/pytest-security-update`

**Created**: 2026-09-23

**Status**: Draft

**Governance Tier**: High assurance — development dependency and supply-chain change

**Input**: Upgrade the vulnerable pytest development dependency in a narrow maintenance package while the OpenARDP expansion pause remains in force.

## User Scenarios & Testing

### User Story 1 — Safe, reproducible contributor test run (Priority: P1)

A maintainer runs the existing local and CI test suite from the committed dependency state without using a pytest release affected by CVE-2025-71176. The same tests, socket restriction and coverage gate remain in effect.

**Why this priority**: The current locked test runner is affected by a known advisory. Maintenance is permitted during the expansion pause, and a reproducible, passing test gate protects future work.

**Independent Test**: Resolve the committed development dependencies in a fresh locked environment and run the existing quality gates, without changing application requirements or test policy.

**Acceptance Scenarios**:

1. **Given** a fresh contributor environment, **when** it installs the committed development dependency set, **then** the test runner is at least the advisory's patched version and the lock remains reproducible.
2. **Given** the upgraded test runner, **when** the complete existing test suite runs, **then** tests, no-network policy and coverage threshold pass without skipped security checks, changed assertions or a reduced threshold.
3. **Given** the default runtime dependency set without development tools, **when** it is resolved, **then** the application dependency list, feature behavior and persisted/public contracts remain unchanged.

### Edge Cases

- If the patched release is incompatible with the existing plugins or supported Python version, stop and record the conflict; do not silently lower coverage or remove tests.
- If regeneration changes unrelated runtime or optional dependency versions, reject the drift or separately justify it before implementation.
- An audit with no pytest finding does not imply the whole optional dependency graph is free of vulnerabilities.

## Requirements

### Functional Requirements

- **FR-001**: The development test-runner requirement MUST exclude pytest releases before 9.0.3, the patched version named by the CVE-2025-71176 advisory.
- **FR-002**: The committed dependency lock MUST resolve a compatible patched pytest with verifiable distribution hashes, without unrelated package-version drift.
- **FR-003**: The existing complete quality gate MUST pass with the patched test runner, including socket denial and the unchanged 85% branch-coverage floor.
- **FR-004**: The application runtime and optional dependency requirements, public schemas, persisted identifiers, provider behavior and release/pilot decisions MUST remain unchanged.
- **FR-005**: The completion record MUST state the tested version, exact commands/results, remaining advisories and rollback route; it MUST NOT claim that an unchanged optional dependency advisory was fixed.

### Non-Goals and Compatibility Impact

- **Non-goal**: Upgrade optional Docling, semantic or model dependencies, change the human pilot, or alter F015 release evidence.
- **Non-goal**: Add a new security scanner, service or automatic update mechanism.
- **Compatibility impact**: Development-only dependency floor changes from pytest 8 to pytest 9; no application, workspace, public-contract, provider-profile or export-profile version changes. Contributors using the dev group must re-sync from the updated lock.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A locked development installation resolves pytest 9.0.3 or newer, and the previous vulnerable pytest version is absent.
- **SC-002**: All existing required local checks and the full test suite pass with no regression in the 85% branch-coverage floor.
- **SC-003**: A dependency diff identifies zero unrelated package-version changes and zero runtime/optional requirement edits.
- **SC-004**: The audit no longer reports CVE-2025-71176 for the committed development graph, while all other unresolved advisories are explicitly reported.

## Assumptions

- The official GitHub advisory `GHSA-6w46-j5rx-g56g` and pytest's 9.0.3 release identify the fixed floor; this is checked against an audit before claiming closure.
- Existing `pytest-cov` and `pytest-socket` versions can work with pytest 9, subject to full-suite verification.
- A dev-tool major upgrade merits the full high-assurance lifecycle even though shipped runtime behavior is unchanged.
