# Feature Specification: Repository Hygiene and Bounded Refactoring

**Feature Branch**: `codex/f031-repository-hygiene`

**Created**: 2026-08-08

**Status**: Complete — published and verified

**Input**: Completely plan and implement repository refactoring, cleaning and hygiene until ten explicit quality gates pass.

## Clarifications

### Session 2026-08-08

- Q: What does “10/10” mean for a mature repository? → A: Ten named, independently verifiable gates all pass; it does
  not mean zero complexity, zero exceptions or a license for an unbounded rewrite.
- Q: May sync-conflict copies be deleted? → A: Only after every candidate has a canonical tracked counterpart and is
  proven byte-identical or demonstrably older; ambiguous or newer content fails closed and is preserved.
- Q: How broad may refactoring be? → A: Behavior-preserving, test-first changes in measured hotspots only; public
  contracts, persisted identities and storage architecture remain unchanged.

## User Scenarios & Testing

### User Story 1 - Trust the repository state (Priority: P1)

As a maintainer, I can prove that the working tree and local Git metadata contain no conflict-copy artifacts and can
detect their return before they corrupt repository operations or obscure real work.

**Why this priority**: A repository cannot be safely changed or released while duplicate sync artifacts can masquerade
as source files or invalid Git references.

**Independent Test**: Run the read-only hygiene audit against a clean synthetic repository and repositories containing
byte-identical, divergent, missing-canonical and Git-metadata conflict copies; only the clean repository passes and no
candidate is modified.

**Acceptance Scenarios**:

1. **Given** a repository containing a numbered conflict copy with a tracked canonical counterpart, **When** the audit
   runs, **Then** it reports the relative path and classification without exposing file contents or changing either file.
2. **Given** an ambiguous or newer conflict copy, **When** cleanup evidence is evaluated, **Then** deletion is blocked
   and the file is preserved for explicit review.
3. **Given** the verified 2026-08-08 OpenARDP duplicate inventory, **When** the bounded cleanup is executed, **Then** all
   151 worktree copies and four unused Git-index copies are removed while every canonical tracked file remains unchanged.

---

### User Story 2 - Maintain complex workflows safely (Priority: P2)

As a contributor, I can understand and change selected high-complexity workflows through smaller named units while
their observable behavior, error semantics and architecture boundaries remain stable.

**Why this priority**: The measured baseline contains concentrated function-level complexity, but broad rewrites would
create more risk than value. Characterized extraction gives maintainability value with bounded compatibility risk.

**Independent Test**: Run focused characterization tests before and after each extraction and prove identical parser,
scanner and CLI results for success, boundary and failure cases while the selected hotspot spans and complexity fall.

**Acceptance Scenarios**:

1. **Given** the existing CLI parser and result rendering contracts, **When** construction and rendering helpers are
   extracted, **Then** all command names, defaults, help behavior, exit codes and JSON/human projections remain stable.
2. **Given** supported and malformed Markdown inputs, **When** parser state transitions are decomposed, **Then** emitted
   blocks, locations, hashes, warnings and failures remain identical.
3. **Given** local-watch trees containing supported, ignored, changed and adversarial paths, **When** scan decisions are
   decomposed, **Then** ordering, identities, classifications and path-boundary failures remain identical.

---

### User Story 3 - Verify and sustain a 10/10 hygiene state (Priority: P3)

As a release reviewer, I can reproduce one scorecard that ties hygiene claims to exact commands, thresholds and evidence
and prevents later maintainability regression.

**Why this priority**: Cleanup is sustainable only when the desired state is encoded as deterministic policy rather than
recorded as a one-time subjective review.

**Independent Test**: Run the repository validator and the documented full gate sequence from a clean checkout; the
feature reports 10/10 only if every named gate passes and reports the failing gate otherwise.

**Acceptance Scenarios**:

1. **Given** a clean checkout, **When** all ten gates pass, **Then** the implementation notes may record 10/10 with exact
   evidence and residual debt.
2. **Given** any new conflict copy, unapproved maintainability exception, architecture violation, failed test or stale
   generated artifact, **When** validation runs, **Then** 10/10 is withheld and the failing gate is identifiable.

### Edge Cases

- A legitimate tracked filename ends in a space and number; only untracked conflict-copy patterns and explicitly named
  Git metadata artifacts are candidates, and tracked files are never classified as disposable.
- A conflict copy has no canonical counterpart, has newer content or cannot be read; the audit reports ambiguity and
  cleanup preserves it.
- A symlink, directory, non-regular file or path outside the repository resembles a conflict copy; the audit fails
  closed and never follows it for deletion.
- Git metadata is a linked-worktree file rather than a directory; discovery resolves it without leaving the repository's
  declared Git directory.
- Refactoring reveals behavior not covered by tests; characterization is added before extraction, and implementation is
  blocked if equivalence cannot be demonstrated.
- A complexity reduction merely moves logic into one new oversized function; aggregate policy and no-new-exception gates
  prevent the feature from claiming success.

## Requirements

### Functional Requirements

- **FR-001**: The feature MUST preserve original document bytes, public schemas, persisted identities, catalog/storage
  behavior, default provider independence and all existing CLI/MCP contracts.
- **FR-002**: A standard-library-only, read-only repository-hygiene audit MUST deterministically identify untracked
  numbered conflict copies and explicitly scoped Git-metadata conflict copies.
- **FR-003**: The audit MUST classify each worktree candidate as byte-identical, divergent, missing-canonical or unsafe,
  using relative paths and SHA-256 facts without logging file bodies.
- **FR-004**: The audit MUST never delete, rename, rewrite or follow a candidate as part of validation.
- **FR-005**: Repository validation MUST fail when an unsafe or unresolved sync artifact is present and MUST pass in a
  normal clean GitHub checkout where no such artifact exists.
- **FR-006**: One deterministic synthetic test suite MUST cover clean, identical, divergent, missing-canonical, tracked,
  symlink and Git-metadata cases without network access or reliance on the developer's repository.
- **FR-007**: Cleanup of the observed 2026-08-08 inventory MUST occur only after a machine-readable pre-clean audit proves
  every candidate has a canonical tracked counterpart and no candidate contains newer or unique work.
- **FR-008**: The cleanup MUST remove exactly the 151 verified worktree copies and four unused `.git/index N` copies,
  preserve canonical files, and be followed by the same audit plus Git integrity validation.
- **FR-009**: The feature MUST document the root cause risk of placing active Git repositories in file-synchronization
  locations and provide non-destructive prevention and recovery guidance without relocating the user's workspace.
- **FR-010**: Refactoring MUST be limited to baseline-measured hotspots selected for high maintenance value and low
  contract risk; replacing SQLite, changing identity algorithms or introducing framework abstractions is prohibited.
- **FR-011**: Existing observable behavior of every selected hotspot MUST be characterized before implementation and
  remain equivalent after refactoring, including success, boundary and sanitized failure paths.
- **FR-012**: The selected original hotspot functions MUST reduce their combined executable span by at least 40 percent
  and each selected function MUST remain within the repository's normal function-size policy after extraction or have a
  smaller documented residual justified by evidence.
- **FR-013**: Refactoring MUST introduce no new maintainability-policy exception, no growth in an existing exception,
  no inward-dependency violation and no circular import.
- **FR-014**: Dead imports, obsolete compatibility shims and stale comments encountered inside the selected scope MUST be
  removed when tests prove they are unused; unrelated code MUST not be mechanically rewritten.
- **FR-015**: The maintainability policy and repository validator MUST remain deterministic and MUST include the new
  hygiene audit without depending on optional packages or network access.
- **FR-016**: The feature MUST update the architecture/module inventory, hygiene guide, feature map, changelog and
  implementation evidence without overstating remaining legacy complexity.
- **FR-017**: Unit tests MUST use synthetic or redistributable fixtures, run without network access and preserve the
  repository-wide minimum of 85 percent branch coverage.
- **FR-018**: Locked dependency resolution, Ruff lint/format, strict mypy, full pytest, repository validation, build,
  generated-artifact drift checks and Linux/macOS/Windows CI MUST all pass before merge.
- **FR-019**: CI execution MUST follow the existing cost policy: exhaust local gates before one ready-for-review matrix
  run and never bypass required checks.
- **FR-020**: Implementation notes MUST disclose exact commands, before/after measurements, cleanup evidence, tradeoffs,
  residual risks and rollback instructions.

### Non-Goals and Compatibility Impact

- **Non-goal**: Rewriting the SQLite catalog or migrations, changing public contracts, renaming the package, replacing
  architecture layers, adding runtime dependencies or claiming that all historical complexity has been eliminated.
- **Non-goal**: Automatically deleting future conflict copies or moving the repository out of its current directory.
- **Compatibility impact**: None for application, workspace, contract, provider-profile and export-profile versions.
  The maintainer-only validator gains one additive check; runtime and persisted formats remain unchanged.

### Key Entities

- **Hygiene finding**: Body-free record containing scope, relative candidate path, canonical path, classification and
  optional SHA-256 identities used to support a read-only decision.
- **Hygiene report**: Deterministically ordered collection of findings plus checked scopes and a pass/fail result.
- **Quality gate**: Named binary criterion with a command, expected threshold and captured result; all ten are required
  for a 10/10 outcome.
- **Refactoring equivalence case**: Characterized input and externally observable output used to prove behavior stability
  across an extraction.

## Success Criteria

### Measurable Outcomes

- **SC-001 — Repository integrity**: The post-clean audit reports zero sync-conflict artifacts, `git fsck` reports no
  repository corruption, and `git status` contains only intentional F031 changes.
- **SC-002 — Safe prevention**: The synthetic audit suite detects 100 percent of specified conflict-copy classes and
  demonstrates zero mutations across every test.
- **SC-003 — Bounded maintainability gain**: The combined executable span of the selected original hotspots falls by at
  least 40 percent, no selected original exceeds the normal policy threshold, and no new exception is added.
- **SC-004 — Behavioral equivalence**: Focused characterization tests cover all declared success, boundary and failure
  scenarios and pass unchanged before and after each extraction.
- **SC-005 — Static quality**: Ruff check, Ruff format, strict mypy, maintainability audit and architecture validation all
  pass with zero new suppressions.
- **SC-006 — Test quality**: The full offline test suite passes on Python 3.12 with at least 85 percent branch coverage and
  no skipped F031 acceptance case.
- **SC-007 — Reproducibility**: Repository validation, package build and generated-artifact drift validation pass from a
  locked clean checkout.
- **SC-008 — Cross-platform quality**: Required Linux, macOS and Windows GitHub checks pass for the exact merge commit.
- **SC-009 — Documentation truth**: All affected inventory, hygiene, roadmap and changelog artifacts agree with the code,
  include exact evidence and explicitly retain residual technical debt.
- **SC-010 — Release hygiene**: The F031 pull request is merged normally, no obsolete feature branch remains locally or
  remotely, and the default branch is clean and synchronized.

## Assumptions

- The 2026-08-08 inventory is stable during cleanup: 151 worktree candidates have canonical tracked counterparts, 146
  are byte-identical and five are demonstrably older Spec-Kit artifacts; any drift triggers a fresh review.
- The four `.git/index N` files are unused conflict copies; the active Git index and referenced worktree metadata remain
  out of cleanup scope.
- Existing F018 policy thresholds remain authoritative; F031 may reduce exceptions but does not weaken limits.
- The user prefers a complete best-practice execution and has delegated bounded implementation choices within these
  compatibility and safety constraints.
