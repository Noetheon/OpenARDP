# Text Ingestion Safety Requirements Checklist

**Purpose**: Formal review of F004 requirement completeness, clarity, consistency, measurability and security boundaries
**Created**: 2026-07-22
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are explicit workspace layout, initialization idempotency and non-implicit-open rules defined? [Completeness, Spec FR-001–FR-003]
- [x] CHK002 Are regular-file, media, encoding, NUL, size, line and block boundaries defined? [Completeness, Spec FR-004–FR-009; Data Model Scalar limits]
- [x] CHK003 Are source snapshot, CAS-only parsing and original immutability obligations complete? [Completeness, Spec FR-005–FR-006; Contract Local source]
- [x] CHK004 Are manifest, native artifact, block, hierarchy, provenance and recipe requirements complete? [Completeness, Spec FR-010–FR-015]
- [x] CHK005 Are claim, busy, expiry, retry, cache verification and forced-reparse semantics complete? [Completeness, Spec FR-016–FR-019; Data Model State transitions]
- [x] CHK006 Are list, status, outline and get selection/body-minimization requirements complete? [Completeness, Spec FR-020–FR-022]
- [x] CHK007 Are trust, body-free diagnostics, deterministic tests and bounded scope obligations present? [Completeness, Spec FR-023–FR-026]

## Requirement Clarity

- [x] CHK008 Is the exact built-in Markdown subset stated without a CommonMark claim? [Clarity, Clarifications; Research Decision 1]
- [x] CHK009 Is empty/whitespace-only input distinguished from failure? [Clarity, Clarifications]
- [x] CHK010 Is ordinary cache reuse distinguished from explicit `--force`? [Clarity, Clarifications; Contract IngestionService]
- [x] CHK011 Are parser-native lossless bytes distinguished from normalized blocks? [Clarity, Research Decision 1]
- [x] CHK012 Are source line ranges inclusive and one-based with a precise F002 extension location? [Clarity, Research Decision 2]
- [x] CHK013 Is a READY cache candidate distinguished from a physically and semantically verified cache hit? [Clarity, Research Decision 7]
- [x] CHK014 Is current document head semantics defined for A → B → A and overlapping observations? [Clarity, Research Decision 6]
- [x] CHK015 Are source-read races and unsupported adversarial same-user filesystem guarantees separated? [Clarity, Plan Security impact]

## Requirement Consistency

- [x] CHK016 Does parsing the CAS snapshot align exact source version, manifest and block provenance? [Consistency, Spec FR-005/FR-010; Plan End-to-end flow]
- [x] CHK017 Does the new block-handle rule preserve SHA-256 content identity and existing ADR-0006 projections? [Consistency, Data Model Deterministic block ID]
- [x] CHK018 Do STAGING/FAILED rows remain non-queryable while READY becomes atomically complete? [Consistency, Contract Ready commit]
- [x] CHK019 Do immutable source-version facts remain unchanged when same bytes are observed with new metadata? [Consistency, Research Decision 6]
- [x] CHK020 Do document heads remain mutable without rewriting historical representations? [Consistency, Data Model DocumentHead]
- [x] CHK021 Do every representation artifact and historical block remain a conservative reachability root? [Consistency, Data Model Reachability]
- [x] CHK022 Does the CLI contract keep business logic in services and persistence/parsing in adapters? [Consistency, Plan Project Structure]
- [x] CHK023 Does F004 READY legitimately require zero indexes while F005 remains unimplemented? [Consistency, Spec Assumptions; Research Decision 10]

## Acceptance Criteria Quality

- [x] CHK024 Is first-ingest proof based on persisted manifest/native/block validation after source removal? [Measurability, SC-001]
- [x] CHK025 Is parser avoidance quantified across repeated and concurrent unchanged requests? [Measurability, SC-002]
- [x] CHK026 Is changed-source history measured as one new version with old evidence still queryable? [Measurability, SC-003]
- [x] CHK027 Is failure atomicity measured as zero partial READY representations at named boundaries? [Measurability, SC-004]
- [x] CHK028 Is provenance accuracy measured against exact line ranges and persisted native bytes? [Measurability, SC-005]
- [x] CHK029 Is the hostile input corpus tied to zero parser side effects, network calls and source writes? [Measurability, SC-006]
- [x] CHK030 Are all six human/JSON commands and body-minimization behavior measurable? [Measurability, SC-007]
- [x] CHK031 Is cross-platform completion tied to actual Linux/macOS/Windows CI evidence? [Measurability, SC-008]

## Security and Operational Boundaries

- [x] CHK032 Are path strings denied CAS-path, SQL, command, URL and tool authority? [Security, Spec FR-004/FR-023]
- [x] CHK033 Are symlink, junction, special-file, replacement and truncation cases explicit? [Security, Spec Edge Cases; Contract Local source]
- [x] CHK034 Are source/body/raw-parser/token/SQL values prohibited from normal errors and events? [Security, Contract Logging]
- [x] CHK035 Is instruction-like content always untrusted data with execution disabled? [Security, Spec FR-023]
- [x] CHK036 Are representation leases fenced by owner, token hash, revision and strict expiry? [Security, Contract Acquisition]
- [x] CHK037 Are corrupt READY artifacts surfaced rather than automatically replaced or hidden by reparse? [Evidence safety, Research Decision 7]
- [x] CHK038 Are CAS orphans preserved for reachability rather than deleted after rollback? [Evidence safety, Contract Ready commit]
- [x] CHK039 Are runtime dependencies unchanged and tests explicitly offline/synthetic? [Operational, Plan Technical Context/Test Strategy]
- [x] CHK040 Are performance, CommonMark, hostile-filesystem and later-feature claims explicitly bounded? [Operational honesty, Spec Assumptions/Out of Scope]

## Notes

- All 40 requirements-quality checks pass after one formal review on 2026-07-22.
- Each item traces to specification or Phase-1 design artifacts; none treats future implementation as already proven.
