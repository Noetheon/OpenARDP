# OpenARDP feature map

**Status:** Authoritative continuation order
**Adopted:** 2026-07-26 through Feature 005A
**Governance:** [Constitution 4.0.0](CONSTITUTION_SOURCE.md) and
[operating procedure](OPERATING_PROCEDURE.md)

## Delivered foundation

| Order | Feature | Status | Demonstrable outcome |
|---:|---|---|---|
| 1 | `001-repository-baseline` | Merged | Reproducible package, governance, locked gates and three-platform CI. |
| 2 | `002-domain-models-schemas` | Merged | Deterministic domain identities and JSON Schema 2020-12 contracts. |
| 3 | `003-cas-sqlite-catalog` | Merged | Atomic filesystem CAS and SQLite catalog with migration/integrity boundaries. |
| 4 | `004-text-ingestion-slice` | Merged | Deterministic local TXT/Markdown ingestion and prepared-evidence inspection. |
| 5 | `005-lexical-search` | Merged | Verified deterministic lexical retrieval over non-authoritative indexes. |

Historical requirements and validation evidence remain under [`specs/`](../specs/README.md).

## Authoritative continuation after Feature 005

| Order | Feature | Independently demonstrable outcome |
|---:|---|---|
| 5A | `005A-strategic-realignment` | Vision, prior art, contracts, ADRs and claims align without runtime change. |
| 6 | `006-evidence-contract-foundation` | Minimal provider-neutral native/evidence/trust contracts and conformance fixtures exist before rich-parser implementation. |
| 7 | `007-docling-native-adapter` | PDF/DOCX/PPTX produce immutable Docling-native artifacts and contract-conformant thin projections. |
| 8 | `008-context-compiler-receipts` | Deterministic bounded context and auditable selection receipts. |
| 9 | `009-read-only-mcp` | Least-privilege read-only access without arbitrary filesystem reach. |
| 10 | `010-reconciliation-derivation-dag` | Safe reuse across edits and exact derivative invalidation. |
| 11 | `011-visual-evidence-escalation` | Exact page/image/table evidence and bounded visual escalation. |
| 12 | `012-local-watcher-and-jobs` | Stable, deduplicated, cancellable local ingestion jobs. |
| 13 | `013-retention-recovery-migrations` | Safe retention, garbage-collection dry-run/quarantine, backup/restore and workspace migration. |
| 14 | `014-export-interchange-experiment` | Evidence-based decision on existing packaging profiles versus custom export. |
| 15 | `015-benchmark-security-release-gate` | Fair baselines, security evidence and a v0.1 go/no-go decision. |
| 16 | `016-alternate-parser-conformance-spike` | A second minimal parser or consumer proves or falsifies provider-neutral contracts. |
| 17 | `017-microsoft-graph-design-spike` | Mock-only least-privilege enterprise connector design. |
| 18 | `018-repository-hygiene` | Measured post-roadmap refactoring, truthful validation and maintainability non-regression. |
| 19 | `019-ci-cost-optimization` | Lower-cost event-aware CI with unchanged final three-platform quality and bounded release evidence. |
| 20 | `020-product-value-benchmark` | Reproducible end-to-end value evidence at 10k/100k blocks and an honest workload-bounded worth-it decision. |
| 21 | `021-incremental-freshness` | Exact source freshness becomes sublinear in prepared block count while complete integrity remains explicit and measurable. |
| 22 | `022-storage-amplification` | Systematically reduce measured text-workspace amplification without weakening originals, provenance or replay. |
| 23 | `023-offline-pdf-model-bundle` | Reproducibly provision and measure the complete offline PDF model boundary. |
| 24 | `024-redistributable-realworld-corpus` | Add a licensed, realistic and independently reproducible multi-format corpus. |
| 25 | `025-semantic-e2e-source-evaluation` | Test semantic questions, evidence selection and source-quality evaluation end to end. |
| 26 | `026-relevance-abstention` | Reject candidates below a frozen explainable relevance floor and emit explicit evidence abstention. |
| 27 | `027-lexical-ranking-diversity` | Rank lexical candidates deterministically while diversifying and bounding per-source selection. |
| 28 | `028-csv-ingestion` | Ingest bounded RFC 4180 CSV as stable source-backed evidence without conversion or body loss. |
| 29 | `029-provider-neutral-multilingual-retrieval` | Evaluate optional provider-neutral multilingual retrieval against the unchanged F025 benchmark. |
| 30 | `030-semantic-retrieval-product-surface` | Expose the validated optional hybrid semantic profile through bounded CLI and MCP product surfaces with exact replay and operational measurements. |
| 31 | `031-repository-hygiene` | Detect and remove synchronization artifacts and reduce measured parser, scanner and CLI hotspots without contract or storage change. |
| 32 | `032-documentation-governance` | Replace universal process overhead with risk-proportionate governance and compact completed feature records without losing contracts or evidence. |
| 33 | `033-product-benchmark-correctness` | Make the F020 rich-format benchmark mutually complete, fail before expensive phases on invalid PDF assets and preserve its body-free command boundary. |
| 34 | `034-independent-retrieval-holdout` | Freeze and baseline an externally sourced 100-question multilingual retrieval holdout before any further retrieval optimization. |
| 35 | `035-profiled-retrieval-optimization` | Attribute retrieval cost by phase, then improve F025 quality and warm latency together before one milestone-only F034 validation. |
| 36 | `036-downstream-evidence-utility` | Measure bounded citation-valid evidence-review completion and time-to-ready on F025, then evaluate the frozen method once on F034. |
| 37 | `037-semantic-session-reuse` | Preserve bounded preparation across real MCP calls and replace obsolete provider caches safely. |
| 38 | `038-local-document-pilot-readiness` | Make explicit context evidence readable and prepare a bounded real-task pilot; further expansion awaits demonstrated recurring value. |
| 40 | `040-agent-ready-access` | Agents find, read and verify exact passages across PDF, Office and text files through a working MCP server and compact CLI, at a fraction of the previous token cost. |
| 41 | `041-lean-governance` | Constitution 4.0.0: usefulness first, agent efficiency, lean durable records and a lightweight usage log instead of a gating pilot. |

## Dependency rule

A feature begins only after its predecessor converges and merges. Feature 006 defines the minimum contracts required by
Feature 007. Later features may add fields only through documented contract evolution and migration rules. Feature 018
is a behavior-preserving maintenance slice after the reviewed product roadmap. Feature 019 changes only repository
automation and its enforcement evidence. Feature 020 measures the delivered product against raw-reparse and
persisted-native baselines without changing runtime behavior or superseding the independent F015 release gate; none of
these features authorizes a new product capability. Feature 021 resolves only the measured status-path bottleneck and
does not pre-implement the storage, PDF, corpus or semantic work assigned to Features 022–025.
Feature 026 addresses only the false-positive/no-abstention failure exposed by F025. Feature 027 may use its relevance
facts for ranking and source allocation but does not add CSV or query expansion. Feature 028 adds CSV ingestion without
semantic retrieval. Feature 029 introduces the optional provider-neutral query-planning boundary and is the first point
at which the unchanged F025 benchmark is rerun as a comparative multilingual product evaluation.
Feature 030 productizes only the F029 profile through explicit local CLI/MCP composition and measures its cold/warm
operational cost. It does not add answer generation, persistent embeddings, a vector database, cloud egress or a new
retrieval policy.
Feature 031 is a behavior-preserving maintenance slice after F030. It adds a read-only repository integrity guard and
bounded private refactoring only; it does not change retrieval policy, product contracts, persistence or providers.
Feature 032 is a governance-only transition. It preserves product behavior and normative evidence while establishing
routine, standard and high-assurance documentation tiers and compacting transient historical planning artifacts.
Feature 033 corrects the existing F020 measurement harness without changing its corpus, value policy, parser behavior or
published evidence schema. Independent holdout, profiling, retrieval-policy changes and downstream utility evidence remain
separate successor work packages.
Feature 034 derives a deterministic CC BY-SA 4.0 evaluation subset from a pinned XQuAD revision. It establishes a new
20-document, 100-question English/German/Spanish holdout and current lexical/semantic baselines without changing retrieval
behavior. The public F025 set remains the development/control set; F034 is reserved for milestone validation.
Feature 035 profiles the unchanged F029 profile on F025 before changing it. Candidate policies and ephemeral-cache behavior
are selected only against F025, retain the lexical default and exact fail-closed replay, and must improve absolute quality
and warm latency together. The frozen F034 holdout is evaluated exactly once after the candidate and thresholds are frozen.
Feature 036 adds no retrieval or answer-generation behavior. It derives a provider-free progressive-disclosure review task
from immutable body-free F034/F035 evidence, freezes its budgets and decisions on F025, then evaluates F034 once without
turning evidence coverage into a human- or generated-answer correctness claim.
Feature 037 corrects only disposable semantic session state after the project audit. It preserves existing evidence,
identities, limits and ranking; onboarding and prospective human-task evaluation remain separate work packages.

## Scope rule

- One bounded change concern maps to one branch and one pull request.
- Features that change user-visible behavior, contracts or trust boundaries receive a roadmap row and a durable record;
  documentation, tests and narrow fixes do not.
- Do not implement later-feature runtime behavior as “preparation”.
- Historical requirements, final evidence and normative contracts stay in place. Transient working artifacts remain
  recoverable from Git history after compaction.


## Current continuation boundary

F040 and F041 end the F038 expansion pause. The active direction is agent-ready document access: an agent answers
questions from a person's local files with located, verifiable passages and minimal context use. Priorities come from
real use recorded in the [usage log](../pilots/usage-log/README.md) and from defects on real user paths
([Article XIII](CONSTITUTION_SOURCE.md)). The [F038 pilot protocol](../specs/038-local-document-pilot-readiness/contracts/pilot-protocol.md)
remains available for a deliberate formal comparison but does not gate work. The F015 release NO-GO is unchanged.

## Scoped maintenance record outside the product continuation sequence

[F039 pytest security maintenance](../specs/039-pytest-security-maintenance/spec.md) updates only the development
test-runner requirement and committed lock to the first patched pytest release for CVE-2025-71176. It adds no platform
feature and does not satisfy, change or restart the F038 real-task pilot or the independent F015 release gate.
F040 and F041 subsequently replaced the F038 pilot as the active continuation.
