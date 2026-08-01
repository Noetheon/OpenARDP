# Data Model: Benchmark, Security and v0.1 Release Gate

## Version constants

- `RELEASE_EVIDENCE_SCHEMA_VERSION = "0.1.0"`
- `BENCHMARK_PROTOCOL_VERSION = "0.1.0"`
- `RELEASE_GATE_POLICY_VERSION = "0.1.0"`
- identity algorithm: `sha256-rfc8785-v1`
- previous application: exact F014 `0.0.1` merge revision
- supported application candidate: `0.1.0rc1` plus canonical source-tree identity; not inferred
- supported platforms: `linux-x86_64`, `macos-arm64`, `windows-x86_64` evidence profiles

## `EvidenceIdentity`

Common closed identity binding:

| Field | Type | Invariant |
|---|---|---|
| `schema_version` | semver | exact installed `0.1.0` |
| `evidence_id` | SHA-256 ID | recomputed over canonical identity projection |
| `source_tree_id` | SHA-256 ID | canonical allowlisted path/length/digest inventory |
| `protocol_id` | SHA-256 ID | exact protocol document |
| `corpus_id` | SHA-256 ID | exact manifest/judgments |
| `configuration_id` | SHA-256 ID | limits, repetitions, budgets, runner profiles |
| `lockfile_id` | SHA-256 ID | exact `uv.lock` bytes |

The source-tree inventory excludes generated release evidence, VCS metadata, build output and
untracked operator files, avoiding a self-referential commit/report identity. An observed Git
commit MAY be recorded as non-identity provenance after publication. Observation time and
absolute paths are excluded from identity projections.

## `BenchmarkObservation`

One immutable raw outcome:

| Field | Type | Invariant |
|---|---|---|
| identity binding | `EvidenceIdentity` fields | all exact and supported |
| `environment_id` | SHA-256 ID | canonical redacted environment profile |
| `baseline` | closed enum | five required baselines |
| `case_id` | bounded identifier | declared by corpus |
| `phase` | closed enum | cold, warm, update, retrieval, compile, replay |
| `repetition` | integer | unique and non-negative |
| `metric` | closed enum | latency, parser calls, bytes, storage or correctness input |
| `unit` | closed enum | ns, count, bytes, ratio |
| `value` | integer/decimal or null | finite, non-negative and unit-compatible |
| `status` | closed enum | passed, failed, unavailable, rejected |
| `reason` | closed enum or null | required unless passed; body-free |

Unique key is `(environment_id, baseline, case_id, phase, repetition, metric)`.

## `EnvironmentProfile`

Canonical redacted facts: OS family/version class, architecture, Python implementation/version,
locked component versions, CPU logical-count/memory buckets, timing resolution and CI/reference
role. It excludes hostname, username, paths, network identifiers and arbitrary environment
variables.

## `EvaluationJudgment`

Closed expected case outcome with `query_id` or `task_id`, exact source version, expected ranked
evidence IDs/anchors, required/irrelevant classification and optional budget. Judgment IDs are
canonical; no query/task body appears in release reports.

## `StatisticalSummary`

- metric group identity;
- valid/rejected/unavailable sample counts;
- median and median absolute deviation;
- deterministic bootstrap lower/upper 95% bounds;
- unit and six-decimal rounding rule;
- sufficiency state and closed reason.

At least seven valid samples are required for a timing summary used by the gate.

## `SecurityControlResult`

Maps one stable control ID to one or more exact test node IDs, threat category, expected
invariant, status, integer duration and closed failure/skip reason. Test stdout, paths,
exception strings and hostile bodies are not retained.

## `PrivacyScanResult`

Lists each canary class by digest, inspected artifact class, allowed occurrence count,
observed count and status. Canary cleartext is operation-local and never serialized in evidence.

## `DependencyReview`

Contains lock/SBOM identities, complete component keys, platform markers, exact SPDX expression
or explicit named-license state for every component, direct/transitive flag and direct
dependency dispositions. Vulnerability snapshot metadata
records tool/database/schema version, observed-at UTC and findings by stable advisory/package
ID. Finding details/URLs are supporting facts; decision uses severity and reviewed disposition.

## `ArtifactInventory`

Exact wheel/sdist filename, byte length, SHA-256, expected type, member count and inspection
status. Members are represented by digest/count in release evidence; absolute build paths are
never recorded.

## `PlatformReproduction`

One immutable platform bundle with environment identity and exact results for corpus drift,
schema/gate tests, security manifest, fresh install, smoke workflow, prior upgrade,
backup/restore, artifact inspection and decision-semantic replay. Every required item is
`passed`, `failed` or `unavailable`; skip cannot satisfy the gate.

## `EvidenceSuite`

Closed suite root for `performance`, `correctness`, `security`, `privacy`, `supply_chain`,
`fresh_install`, `upgrade_recovery` or `platform_reproduction`. It contains an identity,
terminal status, expected/observed counts, content digest and references to immutable child
records. Suite completeness is recomputed, never trusted from the declared status.

## `ReleaseGatePolicy`

Versioned canonical rules:

- exact required suite names/platforms/baselines/metrics;
- maximum evidence age for time-scoped vulnerability evidence (30 days);
- minimum timing samples (7) and bootstrap resamples (10,000);
- zero parser calls on warm OpenARDP paths;
- non-overlapping raw-reparse/OpenARDP retrieval intervals;
- exact correctness/security/privacy/recovery success requirements;
- smallest-budget coverage 1.0 and selected/direct-native byte ratio at most 0.5;
- unresolved critical/high vulnerabilities forbidden; every lower finding reviewed;
- full dependency/SBOM/artifact coverage;
- no waiver/override field.

Policy ID excludes observations and is committed before results.

## `GateCheck`

One policy clause, outcome (`pass` or `fail`), stable reason, exact evidence IDs and bounded
numeric comparison. Missing evidence creates a failing check; checks cannot be omitted.

## `ReleaseDecision`

Canonical machine root with candidate/source/policy/corpus/configuration/lock/artifact IDs,
decision time, `GO` or `NO-GO`, every `GateCheck`, ordered blockers, allowed/prohibited claim
IDs, supported-platform matrix and residual-risk dispositions. Decision identity excludes the
decision time but includes all normative facts and evidence IDs.

## State transitions

```text
corpus/config/policy -> frozen
frozen -> observations -> suite verified | suite failed
verified/failed suites -> gate evaluated -> GO | NO-GO
GO/NO-GO -> report + claim map (generated projections)
```

Evidence is append-only. A rerun creates new observation/suite identities; it never mutates a
prior decision. Any normative input drift requires a new decision.

## Failure categories

- `EVIDENCE_MALFORMED`
- `EVIDENCE_INCOMPLETE`
- `EVIDENCE_IDENTITY_MISMATCH`
- `EVIDENCE_STALE`
- `BASELINE_UNAVAILABLE`
- `SAMPLE_INSUFFICIENT`
- `THRESHOLD_NOT_MET`
- `SECURITY_CONTROL_FAILED`
- `PRIVACY_DISCLOSURE`
- `DEPENDENCY_REVIEW_INCOMPLETE`
- `VULNERABILITY_UNRESOLVED`
- `ARTIFACT_INVALID`
- `INSTALL_REPRODUCTION_FAILED`
- `UPGRADE_RECOVERY_FAILED`
- `PLATFORM_DIVERGENCE`
- `PUBLICATION_FAILED`
