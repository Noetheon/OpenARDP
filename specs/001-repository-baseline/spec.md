# Feature Specification: Repository Baseline

**Feature Branch**: `main`

**Feature Directory**: `specs/001-repository-baseline`

**Created**: 2026-07-22

**Status**: Implemented

**Input**: Establish the independently verifiable OpenARDP engineering foundation described in
`spec-kit/feature-prompts/001-repository-baseline.md`, without implementing document-product behavior.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reproduce a clean development environment (Priority: P1)

As a maintainer, I can check out OpenARDP on a supported machine and reproduce the declared project environment from
version-controlled inputs, so that local and automated checks evaluate the same dependency set.

**Why this priority**: Every later work package depends on a deterministic, installable foundation. Without it, failures
cannot be distinguished from machine-specific drift.

**Independent Test**: Start from a clean checkout with only the documented prerequisites, follow the setup instructions,
and verify that the package imports and the resolved dependency state exactly matches the committed lock state.

**Acceptance Scenarios**:

1. **Given** a clean checkout on a supported operating system with the declared language baseline and environment manager,
   **When** a maintainer runs the documented synchronization command, **Then** all baseline and development dependencies
   install from the committed lock state without manual file edits.
2. **Given** an unchanged checkout that has already been synchronized, **When** the maintainer synchronizes it again in
   locked mode, **Then** dependency resolution does not change any tracked file.
3. **Given** a checkout whose lock state is missing or inconsistent with project metadata, **When** locked synchronization
   is attempted, **Then** setup fails clearly instead of silently resolving a different environment.
4. **Given** a successfully synchronized environment, **When** the maintainer imports the top-level package, **Then** the
   import succeeds and exposes the declared package version.

---

### User Story 2 - Run one authoritative local quality gate (Priority: P2)

As a contributor, I can run the documented lint, formatting, strict typing and test checks locally, so that I receive the
same actionable feedback before submitting a change that automated review will enforce later.

**Why this priority**: A baseline is dependable only if contributors can reproduce every mandatory gate before review.

**Independent Test**: Run every command listed in the repository workflow from a clean synchronized checkout, confirm all
pass, then introduce one representative lint, formatting, typing and test defect at a time and confirm the relevant check
fails.

**Acceptance Scenarios**:

1. **Given** a clean synchronized checkout, **When** all documented quality commands run, **Then** linting, formatting,
   strict type checking, tests and the configured coverage threshold all pass.
2. **Given** code containing an unambiguous lint, formatting or typing violation, **When** the corresponding gate runs,
   **Then** it exits unsuccessfully and identifies the violating file.
3. **Given** a failing test or coverage below the declared threshold, **When** the test gate runs, **Then** it exits
   unsuccessfully rather than reporting a successful baseline.
4. **Given** a unit test that attempts an outbound network connection, **When** the suite runs, **Then** the attempt is
   blocked by the test environment.
5. **Given** a contributor enables the repository's commit-time checks, **When** they attempt to commit a non-conforming
   change, **Then** the same mandatory local gates reject it.

---

### User Story 3 - Receive least-privilege automated validation (Priority: P3)

As a reviewer, I can rely on automated validation across the supported operating-system families, so that platform drift,
unsafe workflow permissions and unreviewed dependency changes are visible before merge.

**Why this priority**: Local success alone does not prove portability or safe repository automation.

**Independent Test**: Inspect the workflow as an untrusted pull-request contributor, verify its permissions and immutable
third-party references, and execute or simulate its complete operating-system matrix using the committed lock state.

**Acceptance Scenarios**:

1. **Given** a push to the default branch or a pull request, **When** automated validation starts, **Then** the full quality
   gate runs on Linux, macOS and Windows using the declared language baseline.
2. **Given** the automation workflow, **When** its effective permissions are inspected, **Then** it has read-only content
   access and no credential persistence or write authority.
3. **Given** a third-party automation step, **When** its reference is inspected, **Then** the reference is immutable and its
   human-readable release association is documented.
4. **Given** project metadata and its committed lock state disagree, **When** automated validation synchronizes the
   environment, **Then** the job fails rather than mutating the lock state.

---

### User Story 4 - Understand governance and the bounded scope (Priority: P4)

As a new contributor or security reporter, I can identify the license, contribution rules, supported security-reporting
path, validation commands and architectural package boundaries without interpreting unfinished product code.

**Why this priority**: Clear governance prevents accidental architectural drift and unsafe vulnerability disclosure while
keeping the first feature narrowly scoped.

**Independent Test**: Follow only the repository's entry-point and governance documents to identify the supported setup,
quality, contribution and private security-reporting process, and inspect the installed package to confirm that later
OpenARDP behaviors are absent.

**Acceptance Scenarios**:

1. **Given** a first-time contributor, **When** they read the repository entry point and contribution guide, **Then** they
   can identify prerequisites, setup, tests, commit-time checks, architectural constraints and the feature workflow.
2. **Given** a security researcher, **When** they read the security policy, **Then** they find a private reporting route,
   the information required in a report, response expectations and explicit guidance not to disclose sensitive details
   publicly before coordination.
3. **Given** a license reviewer, **When** they inspect repository metadata and the license file, **Then** both identify the
   same license.
4. **Given** the repository-baseline package, **When** its source and installed commands are inspected, **Then** no parser,
   database, ingestion, retrieval, MCP, watcher, cloud/model integration or document-processing command exists.
5. **Given** the package layout, **When** dependencies between architectural areas are inspected, **Then** the documented
   inward dependency direction is preserved and all required areas are present as package boundaries.

### Edge Cases

- A supported machine has a newer global language runtime, but the project-specific environment must still select the
  declared baseline rather than use the global runtime accidentally.
- A dependency index or network is temporarily unavailable during initial setup; setup may fail clearly, but an existing
  synchronized environment must still be able to run the unit suite without network access.
- Path separators and executable conventions differ on Windows; the same repository commands and assertions must remain
  portable.
- Generated caches, local environments, coverage data, operating-system metadata and secrets files must not appear as
  tracked changes after normal development commands.
- A Markdown link targets a missing local file or heading, uses the wrong path case, escapes the repository, follows an
  external symlink, uses an absolute/non-portable local path, or appears only inside code; validation must distinguish
  these cases deterministically without fetching external content.
- The test suite becomes empty or stops collecting baseline-contract tests; the coverage and collection configuration must
  not allow this to look like a successful validation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The repository MUST declare Python 3.12 as the sole baseline language series for this feature and MUST use
  `uv` as the documented project environment manager.
- **FR-002**: A complete, version-controlled `uv` lock state MUST cover the baseline package and every development extra
  required by the mandatory quality gates.
- **FR-003**: Locked synchronization of the complete baseline environment MUST fail when project metadata and the lock
  state differ, and MUST leave tracked files unchanged when they agree.
- **FR-004**: The installable package MUST expose its version and MUST contain the `domain`, `ports`, `adapters`, `services`
  and `interfaces` architectural package boundaries required by `AGENTS.md`.
- **FR-005**: The baseline package MUST NOT implement document parsing, domain document models, hashing/identity behavior,
  persistence, ingestion, search, context compilation, MCP, watchers, cloud/model integrations or any related CLI command.
- **FR-006**: The repository MUST provide authoritative commands for linting, formatting verification, strict type
  checking and tests with branch coverage, and each command MUST return a non-zero status for an applicable violation.
- **FR-007**: The test configuration MUST enforce a declared coverage threshold of at least 85 percent for package code
  and MUST block outbound network access during unit tests.
- **FR-008**: Every public Python contract introduced by this feature MUST have type information, a concise docstring where
  callable, and an automated test.
- **FR-009**: The repository MUST provide commit-time checks for linting, formatting verification, strict typing and tests,
  using the repository's locked environment rather than a separately drifting toolchain.
- **FR-010**: Automated validation MUST run the same mandatory gates for pull requests and default-branch pushes on Linux,
  macOS and Windows with the declared language baseline and locked dependency synchronization.
- **FR-011**: Automated validation MUST use read-only repository permissions, MUST NOT persist checkout credentials and
  MUST pin all third-party actions to immutable revisions with readable release annotations.
- **FR-012**: Unit tests and documentation checks MUST use only synthetic or redistributable fixtures and MUST NOT depend on
  network access.
- **FR-013**: Basic documentation validation MUST verify repository-local Markdown file and heading targets with exact path
  case, MUST ignore link-like examples in code, MUST reject repository escape, external symlinks, absolute local paths,
  Windows backslashes and `file:`/`sandbox:` targets, and MUST skip genuine external URLs without network access.
- **FR-014**: Repository metadata and documentation MUST consistently identify the same license, supported Python series,
  environment manager and mandatory quality commands.
- **FR-015**: The repository MUST include coherent entry-point, license, contribution, security, validation and changelog
  documentation, including a private-first vulnerability-reporting process that does not require public disclosure.
- **FR-016**: Ignore rules MUST exclude local environments, build/test/type/lint caches, coverage output, operating-system
  metadata, local application state and conventional environment-secret files.
- **FR-017**: The implementation record MUST restate the work-package acceptance criteria, decisions, exact validation
  commands, results, trade-offs and remaining risks.
- **FR-018**: No mandatory runtime dependency, network service, external model provider or future feature abstraction MAY
  be introduced by this baseline.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On each of Linux, macOS and Windows, a clean checkout can reproduce the complete baseline environment from
  version-controlled inputs and pass all mandatory checks without manual file edits.
- **SC-002**: Repeating locked environment synchronization and all mandatory checks on an unchanged checkout produces zero
  tracked-file changes.
- **SC-003**: One representative lint, formatting, typing, test, coverage and outbound-network violation is rejected by its
  applicable gate in 100 percent of validation attempts.
- **SC-004**: Automated validation grants zero write permissions, persists zero checkout credentials and uses zero mutable
  third-party action references.
- **SC-005**: Every repository-local Markdown file/heading link and every required governance artifact passes offline
  validation, with zero unresolved missing, case-mismatched, escaping or non-portable local targets.
- **SC-006**: A first-time maintainer can locate and run the full setup and validation sequence from the repository entry
  point without undocumented prerequisite steps.
- **SC-007**: Inspection of the baseline source and installed command surface finds zero document-product capabilities from
  work packages 1 through 13.
- **SC-008**: The baseline has zero unresolved critical or high consistency findings across its specification, plan, tasks,
  implementation record and repository state at convergence.

## Assumptions

- Apache-2.0 is the intended repository license because it is already declared in project metadata and recommended in the
  blueprint; ownership, employer-IP, public-name and trademark clearance remain release-governance tasks rather than
  blockers for creating the local baseline.
- The supported operating-system families are current GitHub-hosted Linux, macOS and Windows environments; platform-specific
  product behavior is outside this feature.
- External link reachability and the correctness of external publications are not evaluated by offline documentation
  checks; only repository-local targets and explicitly required files are baseline contracts.
- The repository is hosted privately at `Noetheon/OpenARDP`. GitHub Actions run `29926478593` observed the complete
  Ubuntu, macOS and Windows matrix successfully. GitHub's repository security-advisory and private-vulnerability-reporting
  interfaces apply to public repositories, so the private phase retains the metadata-only fallback in `SECURITY.md` and
  requires that channel to be enabled before public release.
- Initial dependency installation can require package-index access, but test execution and repository validation do not
  perform application or model network calls.
- Feature artifacts are located through `.specify/feature.json`; no feature-branch hook is configured, so this first
  feature may be prepared on the current branch without making branch naming a product requirement.
- Existing scaffolded document models, hashing helpers and CLI commands belong to later work packages and may be removed
  from the baseline so they can be reintroduced only through their own analyzed feature lifecycles.
