# Feature Specification: Incremental Freshness Status

**Feature Branch**: `codex/f021-incremental-freshness`

**Created**: 2026-08-02

**Status**: Converged locally; publication verification pending

**Input**: Optimize OpenARDP's status and freshness path incrementally or sublinearly after F020 measured 2.087-second
reference and 28.626-second scale p95 results, while preserving exact change detection and explicit integrity truth.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receive Fast, Exact Freshness (Priority: P1)

As a local operator, I can determine whether one registered source is current, changed, missing or unprepared without
revalidating every persisted evidence block, so that status remains interactive even for large prepared documents.

**Why this priority**: F020 showed that the current path scales with prepared block count and misses the 250 ms target by
more than an order of magnitude. Freshness is useful only if it remains exact and inexpensive enough to call routinely.

**Independent Test**: Prepare the deterministic 10,000- and 100,000-block corpora, repeat status against unchanged,
changed and missing source copies, and prove both the returned state and that the default path does not enumerate stored
block projections or block bodies.

**Acceptance Scenarios**:

1. **Given** an unchanged registered local source with a READY head, **When** default status is requested, **Then** it
   hashes the authoritative source, returns `CURRENT`, reports its bounded integrity coverage and performs work
   independent of the prepared block count.
2. **Given** the source bytes changed at the same path, **When** status is requested, **Then** it returns
   `SOURCE_CHANGED` from the exact SHA-256 identity without invoking a parser or serving the old head as current.
3. **Given** the source is missing or unregistered, **When** status is requested, **Then** the existing closed state is
   returned without loading prepared block evidence.

---

### User Story 2 - Retain Explicit Full Integrity Verification (Priority: P1)

As a cautious operator, I can deliberately request complete physical and semantic verification when I need assurance
about every persisted artifact, so that faster freshness does not silently become a claim of full workspace integrity.

**Why this priority**: Detecting arbitrary post-publication corruption of every block requires reading that evidence.
Conflating this expensive audit with source freshness caused the scaling failure and would make a fast result dishonest.

**Independent Test**: Corrupt a copied block object after ingestion and show that default status truthfully declares
bounded coverage while an explicit full verification detects the corruption and returns `INTEGRITY_ERROR`.

**Acceptance Scenarios**:

1. **Given** a valid READY representation, **When** full integrity status is requested, **Then** the complete existing
   verification boundary runs and the result declares full coverage.
2. **Given** a block, manifest or native object is missing or corrupt, **When** full integrity status is requested,
   **Then** the result is `INTEGRITY_ERROR` and never `CURRENT` with full coverage.
3. **Given** default status did not read every block, **When** its result is serialized, **Then** it cannot be mistaken
   for complete physical integrity verification.

---

### User Story 3 - Preserve Interfaces and Failure Safety (Priority: P1)

As a CLI or read-only MCP user, I receive the same source-freshness states plus an explicit integrity-coverage field;
complete verification remains an explicit service/CLI audit and cannot turn MCP status into an unbounded operation.

**Why this priority**: Performance work must not create ambiguous output, path authority expansion or transport-specific
semantics.

**Independent Test**: Exercise service, CLI and MCP status for current, changed, missing, corrupt and non-local cases;
compare their body-free projections and verify that MCP remains identifier-only and read-only.

**Acceptance Scenarios**:

1. **Given** equivalent default service, CLI and MCP requests, **When** status is returned, **Then** freshness and
   integrity coverage use one closed vocabulary with deterministic serialization.
2. **Given** an MCP caller, **When** status is requested, **Then** no filesystem path, parser action or side-effecting
   capability becomes available.
3. **Given** a non-local source whose bytes cannot be inspected by this feature, **When** status is requested, **Then**
   the result remains closed and does not fabricate freshness or integrity.

---

### User Story 4 - Prove the Optimization Fairly (Priority: P2)

As a maintainer, I can reproduce before/after status evidence on the frozen F020 corpora and distinguish default
freshness latency from full-integrity latency, so that the optimization claim is measurable and appropriately bounded.

**Why this priority**: The change is justified by a benchmark regression. A favorable result without the original
baseline, raw samples and semantic checks would violate the project's evidence rules.

**Independent Test**: Run a versioned offline F021 status benchmark with retained samples, exact operation counters and
independent validation, then compare it with the committed F020 reference and scale observations.

**Acceptance Scenarios**:

1. **Given** the frozen reference and scale corpora, **When** the F021 benchmark runs, **Then** it publishes separate
   default-freshness and full-integrity distributions with the F020 baseline visible.
2. **Given** a faster result, **When** the report is generated, **Then** exact stale-safety, parser avoidance, coverage
   semantics, environment and limitations remain equally prominent.
3. **Given** a target is missed, **When** evidence is validated, **Then** the miss remains explicit and cannot be waived.

### Edge Cases

- The source changes during hashing or is atomically replaced while status is running.
- Source size and modification time are preserved while bytes change.
- A registered document has no head, a non-READY head or incomplete header artifacts.
- The catalog head changes concurrently between freshness inspection and representation lookup.
- A block object is corrupted after a prior fast status result.
- Manifest or native-source evidence is missing while block evidence still exists.
- The source connector is not local and cannot be re-inspected by this feature.
- The benchmark runs on a non-reference environment or has insufficient samples.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Default status MUST retain exact SHA-256 inspection of the authoritative local source on every request; it
  MUST NOT rely only on size or modification time.
- **FR-002**: Default status MUST return the existing closed freshness states for unregistered, missing, unprepared,
  current, changed and invalid cases without invoking any parser.
- **FR-003**: Default status for a READY head MUST NOT enumerate representation block projections, read block bodies or
  perform work proportional to prepared block count.
- **FR-004**: Default status MUST declare a closed integrity-coverage value that distinguishes bounded head-level checks
  from complete physical and semantic representation verification.
- **FR-005**: Full integrity status MUST reuse the complete existing verification behavior and MUST detect corruption or
  absence in the native object, manifest, catalog projections and block objects.
- **FR-006**: A result MUST NOT declare full integrity coverage unless every artifact required by the existing complete
  verifier was successfully checked during that request.
- **FR-007**: Source changes detected before or during inspection MUST never produce `CURRENT`.
- **FR-008**: Concurrent head replacement MUST produce a result bound to one self-consistent catalog snapshot or a
  closed non-current/integrity outcome; mixed-head evidence is prohibited.
- **FR-009**: Default and full modes MUST retain identical document, head, observed-version and timestamp shape rules.
- **FR-010**: Service, CLI and MCP projections MUST serialize freshness and integrity coverage deterministically using
  one closed vocabulary.
- **FR-011**: MCP status MUST remain identifier-only, read-only, body-free and incapable of accepting arbitrary paths,
  initiating parsing or requesting the unbounded full-integrity mode.
- **FR-012**: Errors MUST remain sanitized and MUST NOT expose bodies, absolute paths, credentials or raw exceptions.
- **FR-013**: No source, CAS object, manifest or block evidence may be modified by either status mode.
- **FR-014**: The optimization MUST require no network access, cloud service, new model provider or mandatory dependency.
- **FR-015**: A versioned offline benchmark MUST retain the committed F020 status baselines and measure default
  freshness plus full integrity separately on 10,000 and 100,000 blocks.
- **FR-016**: Benchmark timing groups MUST use one warm-up and at least seven retained samples with p50, p95 and raw
  observations; unavailable or failed samples MUST remain visible.
- **FR-017**: Benchmark correctness MUST cover unchanged, same-metadata changed, missing, corrupt-block and concurrent
  head cases plus exact parser and block-read counters.
- **FR-018**: The benchmark report and machine result MUST be independently recomputable and must separate observed
  facts, policy checks, limitations and untested conditions.
- **FR-019**: The feature MUST preserve the F020 product-value decision and F015 release decision as historical evidence;
  F021 may publish a new bounded optimization result but MUST NOT rewrite either decision.
- **FR-020**: All repository quality, compatibility, privacy, deterministic-drift and three-platform gates MUST pass
  before merge.

### Non-Goals and Compatibility Impact

- **Non-goal**: Reduce workspace storage amplification, provision PDF models, add a real-world corpus or evaluate
  semantic question answering; those remain F022–F025.
- **Non-goal**: Make complete physical integrity verification constant-time or claim protection against arbitrary local
  administrator tampering without reading affected evidence.
- **Non-goal**: Change source identity algorithms, persisted representation identity, parser behavior, search ranking,
  context selection or release readiness.
- **Compatibility impact**: Additive service/CLI/MCP status output semantics with an explicit coverage field; no public
  evidence schema, application version, workspace revision, provider profile or export profile change is intended.

### Key Entities

- **Status Request**: One identifier or explicit local service/CLI target plus the requested integrity coverage.
- **Freshness Result**: Existing source/head relationship state bound to an exact observation time and source identity.
- **Integrity Coverage**: Closed declaration of which persisted artifacts were actually verified by the request.
- **Status Benchmark Evidence**: Versioned raw timings, operation counters, environment class, policy checks and report.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Default unchanged status p95 is below 250 ms for both 10,000- and 100,000-block frozen corpora on the F020
  reference environment after one declared warm-up.
- **SC-002**: Default status performs zero representation-block projection loads and zero block-object reads at both
  scales.
- **SC-003**: All unchanged, same-metadata changed, missing and concurrently replaced source cases return the exact
  expected freshness state with zero parser invocations.
- **SC-004**: Full integrity mode detects 100 percent of injected native, manifest, projection and block corruption cases
  in the bounded synthetic suite.
- **SC-005**: Every status result exposes an integrity-coverage value, and zero bounded/default results are represented
  as complete verification.
- **SC-006**: Service, CLI and MCP golden outputs agree on the closed vocabulary and contain zero document-body bytes or
  forbidden private values.
- **SC-007**: The versioned result retains at least seven default and seven full-integrity samples per scale and
  independently reproduces all aggregate values and policy outcomes.
- **SC-008**: Source bytes and all pre-existing persisted evidence remain byte-identical across all status workloads.
- **SC-009**: The complete offline suite retains at least 85 percent branch-aware coverage and passes lint, formatting,
  strict typing, repository validation, build and deterministic drift checks.
- **SC-010**: The final report states whether the 250 ms target was met, quantifies the improvement over F020 and lists
  the weaker scope of default freshness alongside the retained cost of full integrity verification.

## Assumptions

- Exact source hashing remains necessary for stale safety even though it scales with authoritative source bytes.
- Performance is sublinear relative to prepared block count and workspace size, not necessarily source byte length.
- Complete post-publication CAS corruption detection remains an explicit full-integrity operation.
- F020's macOS arm64 environment remains the binding timing reference; shared CI verifies semantics and counters.
