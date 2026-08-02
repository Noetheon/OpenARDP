# OpenARDP feature map

**Status:** Authoritative continuation order
**Adopted:** 2026-07-26 through Feature 005A
**Governance:** [Constitution 2.0.0](CONSTITUTION_SOURCE.md) and
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

## Dependency rule

A feature begins only after its predecessor converges and merges. Feature 006 defines the minimum contracts required by
Feature 007. Later features may add fields only through documented contract evolution and migration rules. Feature 018
is a behavior-preserving maintenance slice after the reviewed product roadmap. Feature 019 changes only repository
automation and its enforcement evidence; neither feature authorizes a new product capability.

## Scope rule

- One feature maps to one branch and one pull request.
- Complete only the active feature and selected task phase.
- Do not implement later-feature runtime behavior as “preparation”.
- Historical merged specifications stay in place even when future prompts are replaced.
