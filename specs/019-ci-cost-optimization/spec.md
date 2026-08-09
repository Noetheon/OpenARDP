# Feature Specification: CI Cost and Latency Optimization

**Feature Branch**: `codex/f019-ci-cost-latency`

**Created**: 2026-08-02

**Status**: Converged — see the [authoritative feature map](../../spec-kit/FEATURE_MAP.md)

**Input**: User description: "Reduce GitHub Actions cost and latency while preserving or improving the current quality standard."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preserve authoritative final quality at lower cost (Priority: P1)

As the repository owner, I can merge a code-bearing pull request only after one Linux coverage owner and complete
Linux, macOS and Windows test execution succeed, while platform-independent gates are executed once rather than once
per operating system.

**Why this priority**: Cross-platform regressions have occurred independently on Windows and macOS, so savings must
come from eliminating redundant work rather than weakening the final merge standard.

**Independent Test**: A non-draft pull request containing an unknown or code path schedules exactly one authoritative
coverage job, complete no-coverage test jobs on the other two supported platforms, and one preflight job; all required
job names are stable for branch protection.

**Acceptance Scenarios**:

1. **Given** a non-draft pull request with a production, test, dependency, configuration or unknown file change,
   **When** CI is evaluated, **Then** all tests run on Ubuntu, macOS and Windows and Ubuntu alone enforces branch
   coverage of at least 85 percent.
2. **Given** the same pull request, **When** lint, format, strict typing, repository validation and package build run,
   **Then** each platform-independent gate executes once on Ubuntu and is not duplicated on paid platforms.
3. **Given** any CI job, **When** dependencies are installed, **Then** the locked environment is used, network remains
   blocked in tests, action references remain immutable, and only the bounded uv download/build cache is persisted.

---

### User Story 2 - Iterate cheaply without hiding final failures (Priority: P2)

As a contributor, I can keep an actively changing pull request in draft state and receive a quick deterministic
preflight, then receive the complete three-platform final gate automatically when the pull request becomes ready.

**Why this priority**: Re-running expensive platform suites on every intermediate commit creates most avoidable spend;
draft status is an explicit, reviewable signal that the change is not yet mergeable.

**Independent Test**: A draft code pull request runs classification and preflight but not the three full test jobs;
the `ready_for_review` event on the same pull request schedules all final jobs without a new commit.

**Acceptance Scenarios**:

1. **Given** a draft pull request, **When** it is opened or synchronized, **Then** deterministic classification and the
   preflight run while the final Linux, macOS and Windows jobs are skipped.
2. **Given** that draft pull request, **When** it is marked ready for review, **Then** the full final gate runs without
   requiring a content change.
3. **Given** a documentation/specification-only change from a reviewed allowlist, **When** the final pull request runs,
   **Then** repository/governance validation runs and platform test jobs are skipped.
4. **Given** an empty, malformed or previously unseen path, **When** classification runs, **Then** it fails closed to
   the full final gate rather than treating the change as documentation-only.

---

### User Story 3 - Generate costly release evidence only at release boundaries (Priority: P3)

As a release operator, I can reproduce the unchanged all-platform F015 evidence gate deliberately, on a release tag,
or when release-owned files change, without regenerating immutable release evidence for every ordinary commit.

**Why this priority**: Release evidence is essential at release boundaries but its four-job workflow duplicates costly
platform setup for changes that do not affect release policy or evidence.

**Independent Test**: The release workflow retains its Linux/macOS/Windows evidence matrix and aggregate fail-closed
decision, but its trigger contract is limited to manual dispatch, version tags and final release-relevant pull requests.

**Acceptance Scenarios**:

1. **Given** an ordinary application pull request, **When** workflows are selected, **Then** the release-evidence
   workflow does not run.
2. **Given** a ready pull request changing a release-owned input or the release workflow itself, **When** CI runs,
   **Then** all three platform evidence jobs and the aggregate decision run unchanged.
3. **Given** a version tag or manual dispatch, **When** the release workflow runs, **Then** the full all-platform
   evidence and aggregate gate execute independent of path classification.

---

### User Story 4 - Measure and enforce the optimization (Priority: P4)

As a maintainer, I can inspect a versioned CI policy and deterministic audit that explain which work is authoritative,
which work may be skipped, the measured cost baseline, and the projected topology reduction.

**Why this priority**: Cost and quality claims otherwise drift into undocumented workflow folklore and are difficult to
review safely.

**Independent Test**: Repository tests reject weakened platform, coverage, trigger, cache, action-pinning or fail-closed
classification contracts, and the evidence record calculates the before/after estimate from explicit inputs.

**Acceptance Scenarios**:

1. **Given** the reviewed workflow files and CI policy, **When** the deterministic audit runs twice, **Then** both runs
   produce the same body-free result and all quality invariants pass.
2. **Given** the measured 2026-08-01 baseline, **When** the optimized topology is modeled under documented assumptions,
   **Then** the calculation reports inputs, official unit-price snapshot, limitations and a reproducible savings range.
3. **Given** a deliberate removal of a supported platform, coverage owner, locked install, final-ready event, pinned
   action or release boundary, **When** repository tests run, **Then** the regression is rejected.

### Edge Cases

- A pull request is converted from ready back to draft after a failing full run; it remains unmergeable and final jobs
  run again when it next becomes ready.
- A rename, deletion, binary file, dotfile or non-UTF-8 path appears in the change set; classification is path-based and
  defaults to full quality whenever the allowlist cannot prove governance-only scope.
- A pull request changes its own workflow, classifier, dependency lock, build metadata or CI policy; it is always full.
- A pull request contains both governance-only and code paths; one full-classified path makes the whole set full.
- The base SHA is unavailable on a new branch or forced update; classification must not silently downgrade the run.
- A cache entry is corrupt or absent; the locked sync remains authoritative and can rebuild from the lockfile.
- A platform test fails while Linux coverage passes; the final gate fails and the pull request cannot merge.
- A workflow is invoked from a fork; read-only permissions and non-persistent credentials remain sufficient.
- GitHub rounds each job to a billable minute and pricing changes later; committed evidence is explicitly a dated model,
  not a promise about future invoices.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Non-draft pull requests with full-classified changes MUST run the complete offline test suite on Linux,
  macOS and Windows before merge.
- **FR-002**: Exactly one Linux job MUST run the authoritative full suite with branch coverage and the existing minimum
  threshold of 85 percent; macOS and Windows MUST run the complete same test inventory with coverage instrumentation
  explicitly disabled.
- **FR-003**: Ruff lint, Ruff format checking, strict mypy, repository validation, pre-commit configuration validation
  and distribution build MUST execute exactly once for a full-classified final pull request.
- **FR-004**: Draft pull requests MUST run deterministic classification and bounded preflight only; `ready_for_review`
  MUST trigger the complete applicable final gate without requiring another commit.
- **FR-005**: Documentation/specification-only skipping MUST be based on a narrow version-controlled allowlist; mixed,
  empty, malformed and unknown change sets MUST classify as full.
- **FR-006**: Changes to workflows, actions, CI policy, classifier, source, tests, schemas, dependencies, packaging,
  release inputs or executable scripts MUST classify as full.
- **FR-007**: Pushes to `main` MUST run a post-merge preflight/integrity check but MUST NOT repeat the three-platform
  matrix already required by protected pull requests.
- **FR-008**: The release-evidence workflow MUST retain all three platform evidence jobs, complete frozen security and
  reproduction controls, aggregate fail-closed decision and immutable artifact handling.
- **FR-009**: Release evidence MUST run only for manual dispatch, version tags, and non-draft pull requests changing a
  reviewed release-owned path; it MUST NOT run for ordinary commits or draft pull requests.
- **FR-010**: Every dependency installation MUST use `uv sync --locked`; cached content MUST be limited to uv's cache,
  keyed by the lockfile, safely pruned for CI, and MUST never make the lockfile optional.
- **FR-011**: Workflows MUST retain explicit read-only permissions, non-persistent checkout credentials, timeouts,
  concurrency cancellation and full-commit-SHA action pinning.
- **FR-012**: Required job display names MUST be stable and documented so `main` can require preflight plus all three
  final platform jobs while allowing job-level governance-only skips.
- **FR-013**: A deterministic standard-library CI audit and repository contract tests MUST reject regressions in
  classification, trigger boundaries, coverage ownership, platform completeness, cache safety and action pinning.
- **FR-014**: The feature MUST record the exact observed baseline, dated runner unit prices, calculation method,
  projected topology, exact validation commands, residual risks and rollback steps without presenting modeled savings
  as invoiced fact.
- **FR-015**: `main` MUST be protected after merge against force pushes, deletion and unchecked direct changes; merging
  MUST require an up-to-date pull request and the stable CI status checks without requiring a second human reviewer in
  this single-maintainer repository.
- **FR-016**: No product runtime dependency, public/persisted contract, schema, identity algorithm, workspace revision,
  release decision, cloud dependency, telemetry or default network behavior may change.
- **FR-017**: The complete Spec Kit lifecycle, locked Ruff, format, strict mypy, offline pytest with branch coverage,
  repository validation, package build, pre-commit and final remote workflows MUST pass before completion.

### Non-Goals and Compatibility Impact

- **Non-goal**: Removing Windows or macOS testing, reducing test inventory, lowering coverage, unpinning actions, caching
  environments, or accepting workflow failures to save money.
- **Non-goal**: Changing F015 evidence contents, its `NO-GO` release decision, product behavior or public contracts.
- **Non-goal**: Exact prediction of a future GitHub invoice; included minutes, multipliers, rounding, taxes and pricing
  may change independently.
- **Compatibility impact**: Developer-operations only. Application `0.1.0rc1`, workspace revision 10, schema versions,
  provider/export profiles and persisted identities remain unchanged.

### Key Entities

- **Change Classification**: A deterministic `governance` or `full` decision over repository-relative paths, with an
  explanation and fail-closed default.
- **Quality Lane**: A stable CI job defining platform, test inventory, coverage responsibility, prerequisites and
  conditions.
- **Release Boundary**: A manual, tag or reviewed release-path event that authorizes expensive evidence generation.
- **CI Policy**: A versioned machine-readable record of supported platforms, authoritative gates, safe-skip paths,
  immutable action references and cache rules.
- **Cost Evidence Snapshot**: Dated observed run/job minutes, runner unit prices, assumptions and model output; it is
  historical evidence rather than mutable billing state.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A full-classified ready pull request completes all 1,407 final tests on each of Linux, macOS and Windows,
  with at least 85 percent branch coverage enforced by Linux and zero network access in the suites.
- **SC-002**: Platform-independent gates fall from three executions per full pull request to one, and coverage
  instrumentation falls from three platform suites to one, without reducing the test inventory on any platform.
- **SC-003**: An ordinary main-branch merge schedules no more than one integrity/preflight job instead of the prior
  seven-job post-merge workflow; release-owned or tag/manual events retain the separate release gate.
- **SC-004**: Under the documented comparable-activity model, estimated gross GitHub-hosted runner cost decreases by at
  least 55 percent from the 2026-08-01 baseline while the final full-classified PR retains all three platforms.
- **SC-005**: At least ten classifier test cases cover governance-only, mixed, empty, unsafe, unknown, workflow,
  dependency, source, test and release changes with deterministic output and fail-closed behavior.
- **SC-006**: Repository tests detect deliberate weakening of every FR-001 through FR-013 workflow invariant, and the
  CI audit produces byte-identical output on two consecutive runs.
- **SC-007**: Locked Ruff, formatting, strict mypy, all offline tests, repository validation, package build and
  pre-commit pass locally; a final private pull request passes Preflight and all three final platform jobs.
- **SC-008**: After merge, the `main` protection API reports required up-to-date PR checks, no force pushes, no branch
  deletion and no direct administrator bypass, while zero-review solo merges remain possible.

## Assumptions

- Contributors use draft status for intermediate pushes and mark a pull request ready only when it is a merge
  candidate; GitHub prevents merging draft pull requests.
- Job-level conditional skips satisfy required status checks; workflow-level path filtering is not used for the core CI
  because a wholly skipped required workflow can remain pending.
- The 2026-08-01 run inventory and runner prices are a reproducible planning baseline, not a promise about later billing.
- `main` remains private and is protected immediately after the F019 workflow names have merged.
- Release evidence remains deliberately expensive because its purpose is independent all-platform reproduction at a
  bounded release boundary.
