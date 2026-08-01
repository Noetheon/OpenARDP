# Implementation Notes: Benchmark, Security and v0.1 Release Gate

## Acceptance criteria restated

Feature 015 is complete when the repository can independently identify and validate
the candidate source, frozen corpus/protocol/policy, all five baseline outcomes,
mechanical quality judgments, security/privacy controls, dependency/SBOM state,
artifact/reproduction state and every platform bundle; then apply every policy clause
without a waiver and generate consistent machine, human and claim projections. Missing,
failed, stale or unavailable evidence must remain visible and produce `NO-GO`.

The feature does not require a favorable decision. It forbids advancing
`0.1.0rc1` to final `0.1.0`, tagging or publishing unless a later current binding
decision is `GO`.

## Authoritative inputs and rollback point

- Base: merged Feature 014 main commit
  `2450e71f8fb7a58aa6d6de081ba08eb75258306c`.
- Candidate application version: `0.1.0rc1`; previous application: `0.0.1`.
- Policy/corpus/security/dependency inputs:
  `benchmarks/release/v0.1.0/`.
- Candidate source identity: canonical SHA-256 over the closed allowlist in
  `source-tree-policy.json`; generated release evidence, VCS data, caches and build
  output are excluded to avoid self-reference.
- Public contract: `schemas/openardp-release-evidence.schema.json`.
- Current decision root: `release/evidence/v0.1.0/decision.json`.
- Rollback: discard the bounded F015 branch and return to the F014 merge. No workspace
  schema, persisted identifier algorithm, CAS layout or application runtime fast path is
  changed by F015.

## Implemented slices

### Frozen sources and identities

- Three exact judged document families, three budgets, one edit pair and hostile body,
  metadata, table, image-alt and provider-native fixtures are generated deterministically;
  every source has byte length, SHA-256 and redistribution fact.
- Five baseline names, timing/statistics rules, thresholds, required suites/platforms,
  claims/non-claims and the candidate source allowlist are frozen before the current
  result.
- The release policy ID is RFC 8785/SHA-256 derived from the policy facts and verified
  before evaluation.

### Measurement and quality

- The offline runner distinguishes raw reparsing, direct persisted-native reuse, native
  lexical retrieval, OpenARDP evidence retrieval and bounded compiler output. It emits
  individually identified cold/warm/update/retrieval/compile/replay observations bound
  to exact source, protocol, corpus, configuration, executable, lockfile, platform and
  Python facts without changing production ingestion or compiler behavior.
- Warm-up results are discarded; seven retained repetitions remain raw observations.
  Unavailable treatment results are retained with a closed reason.
- Median, MAD and deterministic 10,000-resample percentile-bootstrap intervals are
  case-stratified for quality and independently seeded from evidence identities.
- Precision/recall/reciprocal-rank, exact anchors, three-budget coverage, stale rejection,
  replay and selected/native byte ratios are mechanical. The absent optional model
  evaluator is one explicit abstention, not a fabricated score.

### Security, privacy and filesystem boundaries

- Exact JUnit-backed test-node manifests fail on missing, renamed, skipped, duplicate or
  unallowlisted results. The current registry executes 44 concrete test cases across
  content, MCP, parser, filesystem, stale-data, recovery and release-policy boundaries.
- Instruction-shaped source/metadata remains untrusted data. OOXML/archive reads are
  bounded; DTD/entity declarations, traversal, malformed archives and excess resources
  fail with sanitized categories.
- Evidence publication is manifest-last, no-overwrite and retry-idempotent only for
  exact verified bytes. Candidate inventories skip only the frozen cache/build classes.
- Privacy scans inspect bounded files, ZIPs and tar archives while persisting only
  canary digests/counts.

### Supply chain and reproduction

- `uv 0.11.31` exports CycloneDX 1.5. Normalization removes timestamp/random serial
  drift, validates every dependency node and enriches all 125 locked components with an
  explicit license expression or named unreviewed state.
- Wheel and sdist inspection validates type, size, member paths, links/devices,
  expanded limits, hashes and privacy canaries without extraction.
- Previous `0.0.1` revision-10 and historical revision-9 fixture plans identify their
  synthetic provenance. The release-evidence pipeline now opens the supported previous
  state and executes revision-9 backup, candidate migration and verified disjoint restore
  rather than treating the fixture plans as execution evidence.
- CI builds the candidate, performs a clean offline wheel install and emits platform
  bundles on Linux, macOS and Windows. The aggregate job downloads immutable artifacts
  with commit-pinned actions and evaluates one all-platform decision.

### Gate and interfaces

- The gate recomputes policy/evidence identities, the exact per-suite required-check
  registry, non-empty evidence bindings, platform/baseline/suite completeness,
  one-reference timing, sample sufficiency, non-overlapping intervals, zero warm parser
  calls, correctness/coverage and bounded-context value in a fixed order.
- `release-evidence`, `release-gate` and `release-report` are workspace-independent,
  bounded, body-free commands. They provide no override/waiver flag. An honest
  `NO-GO` is a successful evaluation; malformed/tampered/conflicting input is not.
- Machine evidence, report, claim map, checksums and SBOM are deterministic generated
  artifacts with independent drift/validation commands.

## Current measured result and claims

The committed local reference capture contains 4,222 individually identified raw
observations over all five baselines, three judged families and all three budgets.
Performance, deterministic mechanical correctness, the exact security registry,
privacy scans, artifact/offline-install checks, previous-version migration/recovery and
local platform semantics pass. The selected/native ratio exceeds the frozen `0.5`
threshold, so bounded-context value is not established by this corpus.

The deterministic committed candidate decision is `NO-GO`. Its remaining blockers are
missing all-platform evidence, an incomplete mandatory supply-chain suite (121 explicit
unreviewed license states and no current vulnerability snapshot) and bounded-context
value. Candidate wheel and sdist inspection, local reference timing and the executable
upgrade/rollback drill are no longer reported as unavailable. Allowed claims are limited to `evidence-preserving`,
`experimental-contracts` and `local-first`. Performance leadership, universal
security, third-party reproduction, three-platform support and v0.1 release readiness
are prohibited.

## Tradeoffs and residual risks

- The frozen standard-library OOXML-native projection is portable and deterministic but
  narrower than a separately configured Docling/model benchmark; this limitation is
  explicit and no enterprise/provider-general performance claim follows from it.
- Shared CI is suitable for semantic/install evidence, not stable performance claims.
- Manifest and canonical-hash integrity do not establish authenticity; Feature 015 does
  not introduce signing or publication authority.
- License metadata can be missing or ambiguous, and an empty/stale vulnerability source
  is not evidence of absence. Both remain blockers.
- Python worker/resource isolation and archive parsers are bounded defense in depth, not
  a portable strong sandbox.

## Verification log

- Foundation focused checks: 14 schema/domain tests passed.
- Expanded F015 focused suite: 49 tests passed before the convergence hardening pass.
- Preliminary complete suite: 1,296 passed; expected F015 version/module/governance/CI
  contract updates were then reconciled. Coverage was `84.94%`, so additional negative
  security/privacy branches were added before the final gate.
- First complete post-convergence capture: 44 exact security-control cases passed; 4,222
  raw observations were committed; seven of eight local suites passed and the
  supply-chain suite failed closed on license/vulnerability evidence.
- Final local quality gate: Ruff lint and format, strict mypy over 77 source files,
  14 schema checks, repository/corpus/dependency/SBOM/evidence validation and 1,317
  tests passed with 85.07% total coverage. Immutable remote CI evidence is recorded
  after publication.
