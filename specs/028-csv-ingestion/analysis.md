# Analysis: Stable CSV Ingestion

## Pre-implementation consistency review

- **Scope**: specification, plan and tasks implement only stable local CSV ingestion plus measurement; F029 is excluded.
- **Authority**: native source bytes remain authoritative and normalized JSON records are explicitly disposable evidence.
- **Architecture**: domain/port contracts stay inward-facing; adapter logic, service publication, interface composition and
  benchmark scripts remain in their existing layers.
- **Compatibility**: adding one media enum and parser recipe version requires no catalog/public-schema migration; F025
  replay remains default-closed.
- **Security**: explicit source only, isolated worker, no network, no formula execution, fixed dialect and bounded errors.
- **Tests**: each functional requirement maps to unit, contract, integration, security or benchmark validation work.

## Findings

No unresolved critical or high-severity contradiction blocks implementation. The only material design constraint is that
normalized CSV blocks must remain text-backed because the existing FTS authority indexes `ContentBlock.text`; canonical
JSON text preserves logical cells without broadening search or public schemas.

## Post-implementation convergence

- All 21 functional requirements and seven success criteria have implementation and test evidence.
- The committed reference result independently validates as `CSV_INGESTION_READY` with exact native/table/line identities,
  1,656 logical records, 18,216 cells and deterministic fresh-workspace projections.
- Q15/Q16 operator treatments achieve full source/atom/citation support at rank 1. The direct natural-language treatments
  remain honest zero-result outcomes and are carried into F029 rather than hidden by benchmark-specific rewriting.
- A clean staged-tree run passed Ruff, formatting, strict mypy, repository governance and the complete test suite:
  1,652 passed, 3 skipped, 85.39% coverage.
- The one integration mismatch exposed by the first clean run was a stale two-service `_CliWatchRunner` test fixture; it
  now supplies the explicit CSV service and the complete suite was rerun from the beginning.

There is no unresolved critical or high-severity gap. CSV dialect breadth and semantic/multilingual retrieval remain
explicit follow-up scope rather than incomplete F028 behavior.
