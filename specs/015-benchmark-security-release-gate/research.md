# Research: Benchmark, Security and v0.1 Release Gate

## Decision 1 — Evidence first; the gate may honestly return NO-GO

**Decision**: implement a binding two-state `GO`/`NO-GO` evaluator. Missing, stale,
inconsistent, unavailable or failed mandatory evidence always maps to `NO-GO`. There is no
force, waive, warning-only or manually editable decision path.

**Rationale**: the feature prompt and Constitution Article IX make negative evidence a valid
outcome. Shipping a favorable default would turn the gate into presentation rather than a
decision control.

**Alternative rejected**: tri-state `GO_WITH_RISK`. Residual risks may be accepted only where
policy explicitly permits them; the release result itself stays binary.

## Decision 2 — Five baselines are separate named treatments

**Decision**:

1. `raw_reparse`: convert exact source bytes for every query/task.
2. `native_reuse`: load and verify one persisted `DoclingDocument`; no chunk selection.
3. `native_retrieval`: load the same native bytes, run Docling's deterministic hierarchical
   chunk projection and rank those chunks with the declared exact lexical scorer.
4. `openardp_retrieval`: use verified OpenARDP projection/index retrieval.
5. `openardp_compiler`: use the existing budgeted compiler and receipt replay.

Every treatment receives the same source version, query/task, relevance judgment and process
isolation profile. `native_retrieval` is described precisely; it is not overclaimed as a
complete official Docling search product.

**Rationale**: direct native reuse is the strongest redundant-parsing counterfactual; native
chunk retrieval separates OpenARDP lifecycle/provenance value from parser-native structure.

## Decision 3 — Small deterministic corpus, not enterprise generalization

**Decision**: reuse the redistributable rich DOCX/PPTX fixtures, add deterministic text and
edited variants, and publish exact queries/tasks/anchors. Each case is small enough for CI and
has one manifest/license entry.

**Rationale**: this proves mechanics, anchors, invalidation and reproducibility. It cannot
support enterprise throughput or quality claims, which remain explicit non-claims.

## Decision 4 — Monotonic raw samples and deterministic statistics

**Decision**: record integer nanoseconds from a monotonic clock; convert only during reporting.
Require seven post-warmup repetitions for a release timing metric. Validate finite,
non-negative values and exact units. Summaries use median, median absolute deviation and a
deterministic percentile bootstrap with 10,000 resamples seeded from the evidence identity.
Quantiles use the documented nearest-rank rule and report six decimal places.

**Rationale**: median/MAD resist shared-runner outliers, while raw values and fixed bootstrap
make every interval independently reproducible without scientific-library dependencies.

**Alternatives rejected**: mean-only summaries; Student intervals without distribution
evidence; cross-host latency aggregation; random unseeded bootstrap.

## Decision 5 — Operational value is predeclared and multidimensional

**Decision**: `GO` requires all of the following on the declared reference environment:

- warm OpenARDP retrieval and compiler parser-invocation count is exactly zero;
- OpenARDP warm retrieval median latency upper 95% bound is below raw-reparse lower bound;
- all judged OpenARDP anchors/retrieval/replay outcomes are correct;
- the smallest declared compiler budget covers all required evidence and its selected body
  bytes are at most 50% of direct persisted-native bytes;
- OpenARDP retrieval recall and anchor correctness are no worse than native retrieval.

Direct native reuse may remain faster. The value claim is avoided reparsing plus verified,
bounded, auditable selection—not universal latency dominance.

## Decision 6 — Quality is mechanical unless an evaluator is explicit

**Decision**: the binding suite scores retrieval relevance, anchor correctness, evidence
coverage, budget use, insufficiency and replay from committed judgments. Optional model-based
answer scoring is recorded as `unavailable` unless a separately versioned, local, reproducible
evaluator is explicitly supplied; it cannot silently affect `GO`.

**Rationale**: no default external model call is allowed, and fabricated answer-quality scores
would be less trustworthy than an explicit gap.

## Decision 7 — Existing security tests become traceable evidence

**Decision**: add a closed security-control manifest mapping every mandatory threat to exact
test node IDs and expected invariants. The release evidence runner executes that manifest with
network disabled and records only node ID, outcome, duration and sanitized category. New
end-to-end sentinels cover prompt injection, parser crash/hang/malformed output, stale drift,
log/report privacy and partial publication.

**Rationale**: re-running existing hardened tests avoids a second security implementation;
the manifest makes coverage inspectable and fails on renamed/missing/skipped tests.

## Decision 8 — Privacy uses canaries and allowlisted payload locations

**Decision**: unique synthetic canaries represent body, query/task, absolute path, username,
hostname, credential and exception text. A scanner checks every generated log/report/manifest,
artifact member and machine response. Body canaries are allowed only inside the declared
synthetic source/native payload objects; all other appearances fail.

## Decision 9 — CycloneDX 1.5 reuses the pinned build tool

**Decision**: run `uv export --format cyclonedx1.5 --all-extras --no-dev --locked`, validate
complete components/relationships, remove volatile timestamp/serial fields, add a lock digest
property, join every component to the reviewed license inventory and canonicalize the result.
Known licenses use exact SPDX expressions; a non-SPDX declared name remains an explicit named
license, never a guessed identifier. A missing component review blocks SBOM generation.
Vulnerability disposition remains separate from the SBOM.

**Rationale**: `uv` 0.11.31 already exports the full locked graph in CycloneDX 1.5, including
platform markers. Its export support is explicitly preview, so exact tool version, normalized
schema and drift tests are required.

**Sources**:

- [uv lockfile export documentation](https://docs.astral.sh/uv/concepts/projects/export/)
- [CycloneDX specification overview](https://cyclonedx.org/specification/overview/)

## Decision 10 — Dependency review separates facts from legal/security conclusions

**Decision**: inventory every locked runtime/all-extras component, require declared-license
status, and give direct dependencies an explicit maintenance/license/security disposition.
Vulnerability input uses versioned OSV-shaped records captured with database/tool/time facts.
Unresolved critical/high findings block; lower findings require an explicit scoped disposition.
Scanner or database absence is not a clean scan.

**Rationale**: an SBOM is an inventory, not legal compatibility or proof that no vulnerability
exists. The OSV schema offers stable identifiers, affected packages/ranges and timestamps.

**Source**: [OpenSSF OSV schema](https://ossf.github.io/osv-schema/)

## Decision 11 — Reproduction separates semantic evidence from noisy timing

**Decision**: Linux, macOS and Windows must each reproduce corpus identities, correctness,
security, artifact install, migration and recovery semantics. Timing results remain separate
per environment; one declared reference environment owns the operational-value timing gate.

**Rationale**: combining unrelated CI clocks creates false precision, while platform-specific
failure and semantic drift must still block release.

## Decision 12 — Previous application and workspace fixtures must predate the candidate

**Decision**: identify exact F014 application `0.0.1` source/artifacts and have that previous
application create the previous-version revision-10 workspace. The F015 candidate is built as
`0.1.0rc1`, reopens the F014 workspace without fact or identity drift, and remains a pre-release
regardless of gate outcome. Separately, preserve the historical revision-9 fixture/inventory to
exercise the supported 9-to-10 migration. Candidate code may validate/copy either fixture but
may not regenerate it during an ordinary gate. Rollback restores the verified pre-candidate
backup to a fresh path.

**Rationale**: a candidate-generated “old” fixture or identical package version cannot prove
previous-version upgrade or rollback. A release-candidate version also avoids circularly
changing artifact identity only after observing the gate result.

## Decision 13 — Release artifact reproduction is bounded and offline

**Decision**: build wheel/sdist from the exact clean revision, publish SHA-256 inventory,
inspect archive paths/content canaries, then create a fresh environment and install only from
the local wheelhouse with dependency resolution disabled after all locked wheels are prepared.
The smoke run covers version, schemas, CLI, text ingestion/search/context and backup/restore.

**Residual limit**: bit-for-bit wheel/sdist reproduction is not claimed because build metadata
and archive timestamps require a separate reproducible-build work package. This feature proves
integrity and clean installation of the exact candidate artifacts.

## Decision 14 — Reports are projections of one verified decision

**Decision**: `decision.json` is authoritative. `report.md` and `claim-map.json` are generated
from it and validated for byte drift. README claims link to claim IDs and must be a subset of
the decision's allowed claims. Reports contain IDs, counts, intervals, platform labels and
limitations, never host/user/path/query/body/exception values.

## Decision 15 — Candidate identity is a source-tree manifest, not a self-reference

**Decision**: identify the candidate with SHA-256 over a canonical allowlisted inventory of
source, configuration, schemas, locked dependencies and benchmark policy/corpus files. Exclude
generated release evidence, VCS metadata, caches and build output. An observed Git commit may be
reported later as non-identity provenance but cannot affect the committed decision identity.

**Rationale**: a report committed in the same feature commit cannot include that commit's hash
inside its own identity without infinite amendment. A content inventory identifies the exact
executable inputs, detects dirty-file drift and remains independently reproducible.

## Known limitations

- Synthetic corpora show bounded operational behavior, not enterprise workload performance.
- Shared CI proves semantic portability but is unsuitable for cross-platform speed rankings.
- The vulnerability snapshot is time-scoped and incomplete by nature; it does not prove absence
  of unknown vulnerabilities.
- License metadata and review are evidence for maintainer decisions, not legal advice.
- A local `GO` would make artifacts release-ready but does not publish or sign them and does not
  imply independent third-party reproduction.
