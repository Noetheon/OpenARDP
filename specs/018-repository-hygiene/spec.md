# Feature Specification: Repository Hygiene and Maintainability

**Feature Branch**: `codex/f018-repository-hygiene`

**Created**: 2026-08-02

**Status**: Draft

**Input**: User request for a complete post-roadmap refactoring, hygiene and cleaning pass, constrained by the
OpenARDP constitution and the requirement to preserve existing behavior and evidence.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Maintain High-Risk Workflows Safely (Priority: P1)

As a maintainer, I can understand and change high-risk orchestration workflows through cohesive, bounded units so that
future fixes do not require editing one monolithic decision path.

**Why this priority**: Long, highly branched orchestration paths create the greatest review and regression risk after
the roadmap's rapid feature growth.

**Independent Test**: Exercise the existing black-box behavior before and after decomposition and verify identical
outputs, errors, persisted state and side-effect boundaries for every affected scenario.

**Acceptance Scenarios**:

1. **Given** an existing supported workflow, **When** its orchestration is refactored, **Then** all observable success,
   failure, atomicity and redaction behavior remains unchanged.
2. **Given** a high-complexity decision path, **When** a maintainer reviews it, **Then** its distinct responsibilities
   are represented by named, independently testable units rather than one growing conditional block.
3. **Given** immutable evidence and persisted compatibility contracts, **When** hygiene changes are applied, **Then**
   their bytes, identifiers, schema versions and workspace behavior remain unchanged.

---

### User Story 2 - Run Truthful Validation Commands (Priority: P1)

As a contributor, I can run focused checks and the complete quality gate exactly as documented so that a successful
focused check is not misreported as a failing repository-wide coverage run and full coverage is never weakened.

**Why this priority**: A command that claims to be a focused quick check but exits unsuccessfully erodes trust in both
documentation and feature evidence.

**Independent Test**: Execute every changed validation command verbatim and verify focused commands exit successfully
while the separate full suite continues to enforce the existing coverage threshold and network prohibition.

**Acceptance Scenarios**:

1. **Given** a feature-local quickstart command, **When** only its focused tests pass, **Then** the command exits zero
   without pretending to measure repository-wide coverage.
2. **Given** the full repository test command, **When** it runs, **Then** the existing branch-coverage threshold and
   socket prohibition remain mandatory.
3. **Given** a new maintainability regression, **When** repository validation runs, **Then** it fails with a stable,
   body-free location and reason.

---

### User Story 3 - Review an Honest Hygiene Baseline (Priority: P2)

As a reviewer, I can inspect reproducible before/after maintenance evidence and known residual debt so that completion
means measured improvement rather than an unsupported claim that all complexity has disappeared.

**Why this priority**: Large mature modules can be safe yet costly to change; an explicit non-regression baseline is
more sustainable than a high-risk rewrite or an unverifiable "clean" label.

**Independent Test**: Regenerate the audit from a clean checkout, compare it with the committed policy and verify that
the report identifies guarded hotspots, allowed legacy debt, exclusions and exact validation results.

**Acceptance Scenarios**:

1. **Given** the repository baseline, **When** the maintainability audit is rerun, **Then** it produces deterministic
   results and permits improvements while rejecting unreviewed regressions.
2. **Given** remaining oversized legacy components, **When** the feature is reported complete, **Then** those components
   are named as residual debt with rationale rather than hidden or rewritten without a bounded design.
3. **Given** generated caches or build outputs, **When** repository cleanliness is evaluated, **Then** none are tracked
   and documented ignore rules cover them.

### Edge Cases

- A refactor changes exception precedence, output ordering, cursor publication or transaction timing.
- A helper extraction accidentally crosses the domain/adapter/interface dependency boundary.
- A focused test command inherits the global coverage threshold and reports false failure.
- A maintainability baseline makes existing debt permanent instead of permitting only equal-or-better results.
- Generated schema, conformance or release-evidence bytes drift during an unrelated cleanup.
- Platform-specific process behavior passes locally but regresses on Windows, macOS or Linux.
- Comments, suppressions or compatibility branches appear unused only because an optional rule is evaluated alone.
- Ignored virtual environments are mistaken for disposable build caches.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST preserve all public CLI, MCP, schema, conformance, application-version, workspace-version,
  export-profile and provider-profile behavior.
- **FR-002**: Original evidence, persisted identifiers, canonicalization algorithms, migration history and frozen public
  contract bytes MUST remain unchanged.
- **FR-003**: The repository MUST have a deterministic, reviewable maintainability policy that detects unapproved growth
  in oversized production modules and functions while allowing debt to decrease.
- **FR-004**: The audit MUST distinguish measured legacy debt from new regressions and MUST NOT label existing debt as
  resolved merely because it is allowlisted.
- **FR-005**: The highest-risk selected orchestration paths MUST be decomposed into cohesive named units with no change
  to success, failure, ordering, atomicity, redaction or side-effect behavior.
- **FR-006**: Every affected workflow MUST retain or gain characterization coverage for its supported and failure paths
  before implementation changes.
- **FR-007**: Focused validation commands MUST pass independently and MUST explicitly defer repository-wide coverage to
  the separately documented full-suite command.
- **FR-008**: The full test command MUST continue to disable network access and enforce at least the existing branch
  coverage threshold.
- **FR-009**: Repository guidance MUST accurately describe implemented Features 001–018 and retain all release,
  production-connector and unsupported-capability boundaries.
- **FR-010**: Stale cross-references, misleading expected-result statements and contradictory active-feature metadata
  discovered by the audit MUST be corrected at their authoritative source.
- **FR-011**: Generated caches, virtual environments, coverage files and build outputs MUST remain untracked; cleaning
  MUST NOT delete source files or a developer's required environment.
- **FR-012**: The implementation MUST add no runtime dependency, cloud call, telemetry, credential, public endpoint or
  default network egress.
- **FR-013**: All public functions changed by the feature MUST retain complete type hints and concise docstrings; narrow
  justified suppressions MUST remain explainable and broad suppressions MUST NOT be introduced.
- **FR-014**: The complete Spec Kit lifecycle, locked dependency check, Ruff, formatting, strict typing, offline tests,
  repository validation, build, pre-commit and Linux/macOS/Windows workflows MUST pass before completion.
- **FR-015**: The final evidence MUST report exact commands, before/after metrics, residual risks and rollback steps
  without making a release-readiness or universal-quality claim.

### Non-Goals and Compatibility Impact

- **Non-goal**: A wholesale rewrite of SQLite persistence, CLI behavior, parser behavior or release policy.
- **Non-goal**: Eliminating every legacy complexity metric in one feature, changing performance semantics or adding a
  new framework merely to reduce file-size measurements.
- **Non-goal**: Deleting developer environments, user worktrees, historical specifications, evidence or generated
  conformance fixtures.
- **Compatibility impact**: Internal refactoring and additive developer validation only. Public contracts, application
  `0.1.0rc1`, workspace revision 10, schema versions and release decision remain unchanged.

### Key Entities

- **Maintainability Policy**: Version-controlled thresholds, scoped exceptions and deterministic rules used to reject
  new structural debt without concealing accepted legacy debt.
- **Hotspot Record**: A source location, measured size/complexity class, approved ceiling and rationale.
- **Validation Contract**: A runnable focused or full command with explicit coverage and network semantics.
- **Hygiene Evidence**: Reproducible before/after measurements, gate results, residual risks and rollback instructions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: One hundred percent of existing tests for each refactored workflow produce unchanged observable outcomes,
  and new characterization tests cover any previously implicit dispatch or failure boundary.
- **SC-002**: The three selected highest-risk orchestration hotspots each decrease their measured function span or
  decision complexity by at least 40 percent without moving complexity into an unbounded replacement.
- **SC-003**: A deliberate maintainability-policy regression is rejected in automated tests, while the unchanged and
  improved repository baselines pass deterministically on two consecutive runs.
- **SC-004**: Every feature-focused command changed by F018 exits successfully when its tests pass; the full suite still
  enforces at least 85 percent branch coverage and zero test network access.
- **SC-005**: Static inspection finds zero new runtime dependencies, tracked caches/build outputs, public schema drift,
  workspace-version changes or persisted-identity changes.
- **SC-006**: Project status, feature map, active-feature metadata, changelog and validation guidance agree on the F018
  scope and all production/release NO-GO boundaries.
- **SC-007**: Ruff, format checking, strict typing, all offline tests, repository validation, package build, pre-commit
  and all seven cross-platform CI jobs pass.
- **SC-008**: The final hygiene record includes baseline and final metrics, exact commands, known legacy hotspots and
  rollback steps, with zero unsupported "fully clean" or release-ready claims.

## Assumptions

- Existing black-box tests define the compatibility baseline; characterization tests are added where refactoring would
  otherwise rely on internal assumptions.
- Large components are reduced incrementally when a bounded extraction is demonstrably safer than a wholesale rewrite.
- A committed non-regression policy is useful only if exceptions are explicit, reviewed and monotonically improvable.
- The existing local virtual environment is required tooling and is excluded from destructive cache cleanup.
