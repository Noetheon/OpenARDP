# Feature Specification: Benchmark, Security and v0.1 Release Gate

**Feature Branch**: `codex/f015-benchmark-security-release-gate`

**Created**: 2026-08-01

**Status**: Draft

**Input**: Authoritative Feature 015 prompt
`spec-kit/feature-prompts/015-benchmark-security-release-gate.md` (SHA-256
`83ce842376ae2e41d9ac2f511c5571298409e38cd88c0fc60002e74e0abd804d`) plus the
request to complete the remaining project sequentially with best-practice,
long-lived and sustainable implementation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compare the Complete Retrieval Pipeline Fairly (Priority: P1)

As a maintainer or independent evaluator, I can run one published benchmark
protocol against raw reparsing, direct reuse of a persisted provider-native
document, provider-native retrieval, OpenARDP retrieval and the OpenARDP
context compiler so that redundant-parsing and retrieval claims have fair,
decision-relevant evidence.

**Why this priority**: OpenARDP's central value proposition cannot support a
release unless it is measured against strong reuse baselines rather than only
against intentionally expensive raw reparsing.

**Independent Test**: Run the complete synthetic/redistributable corpus from a
fresh benchmark workspace, reproduce the raw observations and verify that every
reported comparison uses the same source versions, tasks, environment facts,
sample policy and metric definitions.

**Acceptance Scenarios**:

1. **Given** the published corpus and environment declaration, **When** the
   performance suite runs, **Then** all five required baselines report cold and
   warm latency, update latency, parser invocations, storage overhead, context
   assembly time and failure/skip status under the same workload.
2. **Given** repeated observations, **When** results are summarized, **Then**
   raw samples, sample counts, central estimates, dispersion and 95% confidence
   intervals remain inspectable and no unavailable baseline is silently omitted.
3. **Given** a workload where OpenARDP is equal to or worse than a persisted
   native baseline, **When** the report is generated, **Then** that result is
   displayed with the same prominence as an improvement and blocks any contrary
   README claim.
4. **Given** a source change, **When** the update suite runs, **Then** the report
   distinguishes exact reuse, invalidation, reparsing and stale rejection rather
   than counting all cache hits as useful reuse.

---

### User Story 2 - Measure Correctness and Budgeted Quality (Priority: P1)

As an evaluator, I can verify source-anchor correctness, retrieval relevance,
evidence coverage and bounded-context quality against declared judgments, with
uncertainty and abstentions visible rather than hidden inside an aggregate score.

**Why this priority**: Faster or smaller output has no operational value if it
selects the wrong evidence, loses anchors or conceals uncertainty.

**Independent Test**: Run fixed queries and context tasks against a deterministic
ground-truth corpus, recompute every metric from committed judgments and confirm
that confidence intervals, missing evidence and evaluation limitations appear in
both machine and human reports.

**Acceptance Scenarios**:

1. **Given** exact expected source anchors, **When** each retrieval baseline is
   evaluated, **Then** precision, recall, rank-sensitive relevance and anchor
   correctness are derived from traceable per-case judgments.
2. **Given** multiple context budgets, **When** compilation is evaluated, **Then**
   evidence coverage, supplied units, deterministic replay and explicit
   insufficiency are reported separately for every budget.
3. **Given** a quality judgment that cannot be made deterministically or without
   an unavailable optional evaluator, **When** the suite runs, **Then** the case
   is recorded as unavailable or abstained and never replaced by a fabricated
   score.
4. **Given** fewer observations than the declared minimum, **When** a confidence
   interval or release threshold is requested, **Then** the evidence is marked
   insufficient and cannot satisfy the gate.

---

### User Story 3 - Exercise Security and Failure Boundaries (Priority: P1)

As a security reviewer, I can run hostile document, parser, storage, stale-data,
privacy and recovery fixtures and receive stable evidence that untrusted content
does not gain authority, sensitive data is not exposed and partial failures fail
closed.

**Why this priority**: A release is not acceptable if document content can become
instruction, malformed providers can escape their boundary, stale evidence can be
served, or logs and artifacts disclose user data.

**Independent Test**: Run the committed offline adversarial corpus with sentinel
secrets, instruction-shaped content and injected faults; verify every expected
control outcome, cleanup invariant and body-free diagnostic classification.

**Acceptance Scenarios**:

1. **Given** prompt-injection text in source bodies, metadata, tables, images and
   provider-native data, **When** all delivered retrieval and context surfaces are
   exercised, **Then** the content remains untrusted data and initiates zero tools,
   policy changes, network requests or write operations.
2. **Given** malformed, oversized, hanging or crashing parser behavior, **When**
   ingestion is exercised within declared bounds, **Then** the operation fails in
   a stable category, reaps owned work and publishes no partial authoritative state.
3. **Given** stale, drifted, corrupt or substituted catalog/CAS/index facts,
   **When** retrieval, compilation and reconciliation are exercised, **Then** all
   affected results fail closed or reject stale reuse with no silent repair.
4. **Given** sentinel bodies, paths, queries, credentials and exception text,
   **When** commands, logs, reports, crash-like failures and exported evidence are
   inspected, **Then** zero forbidden sentinel values are present outside explicitly
   designated synthetic payload evidence.
5. **Given** interruption, capacity exhaustion or malformed recovery input,
   **When** a destructive or publishing operation is tested, **Then** originals
   remain unchanged and the documented recovery/rollback path restores or preserves
   one complete state.

---

### User Story 4 - Reproduce Installation, Upgrade and Recovery (Priority: P1)

As a release operator or independent user, I can build and install the candidate
from declared artifacts, open or migrate a supported prior workspace, back it up,
restore it and run a smoke workflow on every supported platform without hidden
network or machine-specific state.

**Why this priority**: Source-tree success is not release readiness. Users require
installable artifacts, explicit compatibility and a tested rollback boundary.

**Independent Test**: Starting from clean environments on Linux, macOS and Windows,
build and verify release artifacts, install them, exercise the public local workflow,
upgrade a committed prior-version fixture, perform backup/restore and compare the
recorded support evidence.

**Acceptance Scenarios**:

1. **Given** a clean supported environment and candidate artifacts, **When** the
   documented install is performed offline from the prepared artifact set, **Then**
   version, schemas, CLI entrypoint and a minimal local workflow verify successfully.
2. **Given** every declared supported prior workspace revision, **When** upgrade is
   performed, **Then** migration receipts, authoritative identities and required
   user-visible facts match the expected post-upgrade state.
3. **Given** the last supported pre-upgrade state, **When** the documented backup,
   candidate upgrade, restore and reopen drill runs, **Then** rollback uses the
   complete backup rather than editing migration history and restores the exact
   verified state.
4. **Given** an unsupported platform, version or missing optional capability,
   **When** reproduction is attempted, **Then** the limitation is explicit and does
   not become a silent pass.

---

### User Story 5 - Make a Traceable GO or NO-GO Decision (Priority: P1)

As the release owner, I receive one deterministic machine decision and a readable
companion report that trace every gate to evidence, constrain README claims, list
residual risks and provide support and rollback instructions.

**Why this priority**: The feature exists to make a genuine release decision, not
merely accumulate test output. Missing evidence and unsafe results must have binding
consequences.

**Independent Test**: Generate the decision from valid evidence, then independently
tamper with, remove, expire or mark a mandatory suite unavailable and verify the gate
changes to `NO-GO` with stable reasons while the human and machine reports remain
consistent.

**Acceptance Scenarios**:

1. **Given** complete, current and reproducible evidence that satisfies every
   mandatory threshold, **When** the gate runs, **Then** it emits `GO` with exact
   evidence identities, candidate version, supported platforms and permitted claims.
2. **Given** absent, stale, inconsistent, non-reproducible or failing mandatory
   evidence, **When** the gate runs, **Then** it emits `NO-GO`; no override flag,
   warning-only path or report wording converts it to `GO`.
3. **Given** benchmark evidence that does not demonstrate distinct operational
   value over persisted provider-native reuse, **When** the decision is generated,
   **Then** `NO-GO` is mandatory even if conventional quality gates pass.
4. **Given** a machine decision, **When** the human report and README claim map are
   generated and independently checked, **Then** their status, metrics, limitations
   and evidence links agree exactly.
5. **Given** a future rerun with identical normative inputs and declared environment,
   **When** reports are regenerated, **Then** identity-bearing content and the gate
   decision match while wall-clock observations remain explicitly new samples.

### Edge Cases

- A required baseline is unavailable, crashes, exceeds its resource budget or returns
  only a subset of cases.
- Timer resolution, process scheduling, thermal throttling or background load makes a
  latency sample invalid or highly variable.
- The corpus, judgments, benchmark configuration, executable tree or lockfile changes
  between suite execution and decision generation.
- Raw observations contain `NaN`, infinity, negative duration, inconsistent units,
  duplicate sample identity or too few independent repetitions.
- A confidence interval crosses a release threshold or a reported improvement is not
  practically distinct from measurement noise.
- A fast result is stale, incomplete, incorrectly anchored or derived from a different
  source version.
- Optional model-based quality evaluation is absent, non-deterministic, costly or would
  require network egress.
- A prompt-injection sentinel appears legitimately inside the designated synthetic
  source payload but leaks into a log, filename, summary, report or policy field.
- A parser writes output immediately before timeout, crashes after publication, leaves
  children behind or attempts socket creation.
- An advisory scanner is unavailable, its vulnerability database is stale, or a finding
  has no fix; the gate must distinguish tool absence from reviewed residual risk.
- Dependency metadata has multiple licenses, missing license text, an unreviewed direct
  dependency, an unexpected transitive dependency or a lockfile/artifact mismatch.
- An SBOM omits the application itself, extras, hashes, licenses or dependency edges, or
  differs between a wheel and source distribution.
- A previous-version fixture has been regenerated by the candidate, is newer than the
  declared baseline or cannot be opened by the historical release toolchain.
- One supported platform passes while another fails, skips, times out or produces a
  semantically different decision.
- Reports are manually edited after generation, refer to a different commit or include
  absolute paths, usernames, secrets or host identifiers.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST define one versioned benchmark protocol with fixed
  metric meanings, units, workload phases, warm-up, repetition, invalid-sample and
  confidence-interval rules.
- **FR-002**: The protocol MUST evaluate raw source reparsing, direct reuse of a
  persisted provider-native representation, provider-native retrieval over that
  representation, OpenARDP retrieval and OpenARDP context compilation.
- **FR-003**: Every required baseline MUST receive the same source versions, queries,
  tasks and declared resource policy; unavailable or incomplete baselines MUST remain
  explicit gate inputs rather than being omitted from comparisons.
- **FR-004**: Performance evidence MUST include cold/warm ingestion, changed-source
  update, parser invocations attempted/avoided, storage overhead, retrieval and context
  assembly latency, and deterministic replay.
- **FR-005**: Raw observations MUST be immutable, independently identifiable records
  that include protocol/corpus/configuration/executable/lockfile identities, platform
  and runtime facts, baseline, case, repetition, metric, unit and terminal status.
- **FR-006**: Reports MUST publish every valid raw observation used, rejected samples
  with closed reasons, sample counts, central estimates, dispersion, 95% confidence
  intervals and limitations; aggregate-only evidence is insufficient.
- **FR-007**: Wall-clock and environment observations MUST be separated from
  deterministic semantic outcomes so that benchmark variability never changes evidence
  identities for corpus definitions, judgments or gate policy.
- **FR-008**: The committed benchmark corpus and generator MUST be synthetic or legally
  redistributable, deterministic, bounded, license-labelled and free of real or
  confidential user data.
- **FR-009**: Correctness evaluation MUST include traceable per-case judgments for
  precision, recall, rank-sensitive relevance, source-anchor correctness, evidence
  coverage, stale-artifact rejection and deterministic replay.
- **FR-010**: Budget/quality evaluation MUST exercise multiple declared context budgets,
  report selected evidence and insufficiency separately, and MUST NOT substitute an
  unavailable model-based judgment with a fabricated score.
- **FR-011**: Confidence intervals and threshold comparisons MUST fail closed when sample
  counts are insufficient, values are invalid or intervals cross a mandatory boundary.
- **FR-012**: The suite MUST include source-edit cases that distinguish exact reuse,
  invalidation, reparsing, reconciliation and rejection of stale or corrupt derivatives.
- **FR-013**: The security corpus MUST cover instruction-shaped source text, metadata,
  table/image content and provider-native fields across ingestion, retrieval, context,
  MCP, visual, interchange and operator-report boundaries that are present in the
  candidate.
- **FR-014**: Security evaluation MUST demonstrate that untrusted content causes zero
  tool authorization, network initiation, policy/trust elevation, filesystem authority
  expansion or write-capable MCP behavior.
- **FR-015**: Malformed parser evaluation MUST cover invalid structured output, oversized
  output, hang, crash, resource-limit breach, network attempt and partial-output cleanup
  with stable body-free outcomes.
- **FR-016**: Stale/reconciliation safety evaluation MUST inject catalog, index, CAS,
  lineage and derivation drift and verify that no stale or unverified evidence is served
  as current.
- **FR-017**: Privacy evaluation MUST place unique sentinels in bodies, queries, paths,
  credentials and exception text, then scan commands, logs, reports, diagnostics,
  manifests and generated release evidence for forbidden disclosure.
- **FR-018**: Failure/recovery evaluation MUST cover cancellation, interruption,
  concurrent duplicate work, capacity refusal, migration failure, backup verification,
  restore and rollback without changing originals or exposing partial authoritative state.
- **FR-019**: The release review MUST inventory every direct and transitive dependency,
  enabled optional group, version, source, hash availability and declared license and
  identify additions or drift from the lockfile.
- **FR-020**: The release review MUST record maintenance, vulnerability, license and
  supply-chain disposition for every direct dependency and every actionable scanner
  finding; tool/database unavailability MUST be a visible failure or residual risk, not
  a clean result.
- **FR-021**: Candidate wheel and source artifacts MUST be built from a clean exact
  revision, have published SHA-256 checksums and be inspected for unexpected files,
  local paths, secrets, source fixtures and undeclared generated content.
- **FR-022**: A machine-readable software bill of materials MUST cover the application,
  resolved runtime dependencies, relevant optional groups, versions, licenses,
  dependency relationships and artifact/lock identities, with deterministic drift
  validation for identical inputs.
- **FR-023**: Fresh-install reproduction MUST install only from the prepared candidate
  artifact set in a clean environment, verify the public entrypoint/schema set and run
  a representative local workflow with network disabled.
- **FR-024**: Upgrade reproduction MUST begin from an independently created supported
  previous-version workspace fixture and verify ordered migrations, checksums, identities,
  user-visible facts and candidate reopen behavior.
- **FR-025**: Backup/restore reproduction MUST verify the pre-upgrade backup, upgrade the
  working copy, restore to a fresh disjoint location and prove the documented rollback
  state opens and matches its signed inventory.
- **FR-026**: Fresh install, upgrade, backup/restore and the complete gate MUST reproduce
  on Linux, macOS and Windows; a missing, skipped or semantically divergent supported
  platform result blocks release.
- **FR-027**: The gate policy MUST define mandatory evidence suites, freshness and identity
  rules, minimum samples, operational-value thresholds, safety invariants, supported
  platform agreement and permitted residual-risk dispositions before observing results.
- **FR-028**: `NO-GO` MUST be mandatory if distinct operational value over persisted
  provider-native reuse, required correctness, safety or three-platform reproducibility
  is not demonstrated. The delivered gate MUST have no force/waive path.
- **FR-029**: The machine report MUST use a versioned closed schema and include candidate,
  source, protocol, corpus, configuration, lockfile, artifact and suite identities; every
  gate outcome MUST cite exact evidence and a stable reason.
- **FR-030**: The human report MUST be generated from the verified machine decision and
  include fair comparisons, limitations, failures, residual risks, support matrix,
  install/upgrade/backup/restore/rollback instructions and final `GO` or `NO-GO`.
- **FR-031**: README performance, security, compatibility and support claims MUST each map
  to current evidence and MUST NOT exceed the machine decision's permitted claim set.
- **FR-032**: Generated corpus manifests, judgments, schemas, reports, checksums, SBOM and
  claim maps MUST have deterministic regeneration and drift checks; manual edits to
  generated normative evidence MUST be detectable.
- **FR-033**: Benchmark and release commands MUST operate locally, default to no network,
  accept only explicit bounded paths/configuration and emit body-free structured results
  with stable error categories.
- **FR-034**: Evidence and reports MUST exclude document bodies except designated
  redistributable corpus payloads, absolute paths, usernames, hostnames, credentials,
  tokens, environment secrets, query/task text and raw exception strings.
- **FR-035**: The feature MUST update authoritative benchmark, security, operations,
  release, support, compatibility, user and changelog documentation with exact commands,
  limitations, residual risks and rollback instructions.

### Non-Goals and Compatibility Impact

- **Non-goal**: Publish a package to a public package index, create a GitHub release,
  sign artifacts, claim third-party reproduction or declare a standard merely because
  the local gate can produce `GO`.
- **Non-goal**: Add cloud telemetry, hosted benchmark infrastructure, mandatory external
  scanners, remote model calls or production document data.
- **Non-goal**: Prove universal sandboxing, absence of unknown vulnerabilities, legal
  license compatibility, secure erasure, enterprise SLOs or multi-tenant isolation.
- **Non-goal**: Tune the implementation or benchmark corpus to manufacture a favorable
  comparison, suppress negative results or compare only against raw reparsing.
- **Non-goal**: Add a second parser implementation, production Microsoft Graph connector
  or independent contract consumer; Features 016 and 017 own those later spikes.
- **Compatibility impact**: Additive benchmark/release evidence contracts, local
  maintainer commands and generated artifacts. The installable candidate advances from
  F014 `0.0.1` to the distinguishable pre-release version `0.1.0rc1` before evidence is
  collected; existing workspace/catalog revision, public evidence/context/interchange
  contracts and provider profiles remain unchanged. A later explicit release commit may
  advance to final `0.1.0` only from a current binding `GO`. `NO-GO` leaves `0.1.0rc1`
  unpublished and preserves the existing public-release status.

### Key Entities

- **Benchmark Protocol**: Versioned definitions for baselines, phases, metrics, units,
  repetitions, invalid samples, statistics and fair-comparison rules.
- **Corpus Manifest**: Deterministic identity and license/provenance inventory for all
  benchmark documents, edits, queries, tasks, judgments and hostile fixtures.
- **Raw Observation**: One immutable baseline/case/repetition/metric outcome tied to
  exact protocol, corpus, configuration, executable, lockfile and environment facts.
- **Evaluation Judgment**: A traceable expected relevance, anchor, coverage, trust or
  failure outcome that supports independently recomputable correctness metrics.
- **Suite Evidence**: A verified collection of observations and semantic checks for one
  required performance, correctness, security, supply-chain or reproduction suite.
- **Gate Policy**: The versioned predeclared mandatory suites, freshness rules,
  thresholds, invariants and residual-risk dispositions that determine release status.
- **Gate Decision**: A deterministic `GO` or `NO-GO` result with stable reasons and exact
  evidence identities.
- **Claim Map**: The permitted README/support claims and the exact decision evidence that
  supports or forbids each one.
- **Release Inventory**: Candidate artifacts, hashes, SBOM, dependency/license review,
  platform results, support boundaries and recovery/rollback evidence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All five required baselines execute the same committed workload, or the
  gate reports `NO-GO`; 100% of observations and baseline unavailability reasons are
  present in machine-readable evidence.
- **SC-002**: Every reported aggregate is independently recomputable from published raw
  observations and matches sample count, central estimate, dispersion and 95% confidence
  interval exactly within the declared rounding policy.
- **SC-003**: At least three representative document/task families and three context
  budgets measure cold/warm/update, storage, retrieval, anchor, coverage and replay
  outcomes without real or confidential data.
- **SC-004**: 100% of committed relevance, anchor, stale/reconciliation and deterministic
  replay judgments produce their expected outcome; any miss blocks release.
- **SC-005**: 100% of prompt-injection, malformed-parser, authority-expansion, corruption,
  privacy-sentinel, cancellation and partial-publication fixtures pass on all supported
  platforms; any skipped or failed mandatory fixture yields `NO-GO`.
- **SC-006**: Generated operator output and release evidence contain zero forbidden body,
  path, username, hostname, secret, query/task or exception sentinels across the complete
  committed adversarial scan.
- **SC-007**: Candidate wheel and source artifacts install in clean offline environments,
  expose the expected version/schema/entrypoint set and complete the smoke workflow on
  Linux, macOS and Windows, or the decision is `NO-GO`.
- **SC-008**: Every declared supported upgrade fixture and one complete backup-upgrade-
  restore drill preserve 100% of expected identities and facts on all supported
  platforms, or the decision is `NO-GO`.
- **SC-009**: The dependency inventory, license review, checksums and SBOM cover 100% of
  resolved candidate runtime components and drift checks detect every synthetic omitted,
  changed or unexpected component.
- **SC-010**: Independent regeneration from identical normative inputs produces identical
  corpus, policy, schema, claim-map, SBOM and decision bytes; tampering with any required
  evidence changes the decision to `NO-GO` or fails validation.
- **SC-011**: The human report, machine decision, support matrix and README claim map agree
  on 100% of statuses, metrics and limitations and identify every claim's evidence or
  explicit prohibition.
- **SC-012**: A `GO` result is possible only when every mandatory suite passes and a
  predeclared operational-value comparison over persisted native reuse is satisfied;
  every tested missing, stale, failing or threshold-crossing input yields `NO-GO`.

## Assumptions

- Features 001 through 014 are merged, converged and form the exact candidate behavior
  under evaluation; F015 does not redesign those runtime boundaries to improve results.
- F014 application `0.0.1` at its exact merge revision is the previous-version install/
  workspace producer. F015 `0.1.0rc1` is the candidate under test; both versions remain
  independently identifiable even though F015 adds no workspace migration.
- Supported release platforms are Linux, macOS and Windows on the project's Python 3.12
  baseline; exact runner versions and limitations are evidence facts, not universal OS
  support claims.
- Committed corpora remain intentionally small enough for routine CI security and
  correctness checks. Timing benchmarks may run in a separately declared reproducible
  profile because shared CI timing is noisy, but missing required release evidence still
  yields `NO-GO`.
- Optional rich-provider and visual capabilities are evaluated only from locked local
  assets with network denied. Unavailable required baseline capability is reported, not
  downloaded or simulated as a successful result.
- Statistical confidence describes this bounded corpus and environment only; it does not
  generalize to enterprise workloads or downstream model quality.
- The current source revision is a release candidate, not a released version. This
  feature records a decision and release-ready evidence but performs no external
  publication without a separate explicit operator action.
- Security scanners and advisory databases are supporting evidence. The binding security
  gate is the committed offline control suite plus explicit review of scanner coverage,
  freshness and unresolved findings.
