# Implementation Notes: Evidence Contract Foundation

**Feature**: `006-evidence-contract-foundation`

**Branch**: `codex/f006-evidence-contract-foundation`

**Date**: 2026-07-26
**Rollback/base commit**: `39e7f8313bdb433f3057c3ad5ebf1b141e1ee2c4`

## Restated acceptance criteria

1. Add four additive experimental roots: native representation, evidence reference,
   evidence projection, and trust classification.
2. Bind every reference and projection to one exact source version and retained native
   representation.
3. Support text, page-region, table-cell, and opaque provider-pointer anchors without
   provider-class leakage.
4. Use strict independent version/stability metadata, closed direct fields, and
   URI-namespaced JSON extensions.
5. Recompute purpose-specific RFC 8785/SHA-256 identities from explicit allowlists and
   publish reviewed golden vectors.
6. Reject stale source/native bindings, invalid geometry, malformed pointers, identifier
   drift, unknown fields, unsupported versions, and trust promotion.
7. Keep evidence data-only with instruction execution permanently disabled.
8. Preserve the complete provider-native artifact while keeping projections limited to
   identity, navigation, retrieval, trust, and lifecycle.
9. Publish deterministic JSON Schema 2020-12 files plus synthetic valid/invalid
   conformance fixtures.
10. Provide an offline, path-confined, adapter-independent validator.
11. Document optional W3C PROV/Web Annotation mappings without mandatory JSON-LD or
    conformance claims.
12. Preserve every Feature 005 schema and canonical identity vector unchanged.
13. Run the full Spec Kit lifecycle, repository quality gate, distribution build, and
    three-platform PR/post-merge CI before closure.

## Baseline

The feature begins from merged and remotely verified F005A closeout commit
`39e7f8313bdb433f3057c3ad5ebf1b141e1ee2c4`. The older uncommitted pre-v3.1 F006
worktree remains isolated and is not a source of authority for this feature.

| Evidence | Result |
|---|---|
| `git rev-parse HEAD` | `39e7f8313bdb433f3057c3ad5ebf1b141e1ee2c4` |
| Five existing schema SHA-256 values | `1995cc10…`, `413d7250…`, `56e8fc17…`, `00b581b0…`, `e6cea129…` |
| Existing canonical-vector SHA-256 | `9387f64d…` |
| `uv sync --all-extras --locked` | pass; 35 packages installed/audited |
| `uv run --locked ruff check .` | pass |
| `uv run --locked ruff format --check .` | pass; 65 files |
| `uv run --locked mypy src` | pass; 32 source files |
| `uv run --locked pytest -q` | pass; 415 tests, 86.49% branch coverage |

## Test-first evidence

Before contract implementation, the three new focused modules failed during collection:
`openardp.domain.evidence` and the three F006 identity helpers did not exist. After the
smallest domain implementation, 26 focused identity/anchor/trust/security tests passed.
Schema/conformance tests were then added before the four generated roots and public
fixture corpus; the first schema run exposed that `patternProperties` alone did not close
unnamespaced extension keys. The originating model schema metadata was corrected to emit
`additionalProperties: false`, after which the focused schema/model parity suite passed.

## Implemented boundary

- Four immutable experimental roots with installed-version and stability enforcement.
- Domain-separated JCS/SHA-256 identities for native artifacts, references, and
  projections.
- Half-open text spans, fixed-point page rectangles, table cells, and bounded
  profile-scoped opaque pointers.
- Origin/effective trust lattice, data-only role, and permanent non-execution.
- Pure native/reference/projection aggregate validation with caller-pinned source scope
  and duplicate-ID collision rejection.
- Four deterministic schemas, seven valid fixtures, eight invalid fixtures, one coherent
  record set, and six reviewed identity vectors.
- Adapter-independent, traversal-resistant offline conformance validation.
- Optional PROV/Web Annotation mapping guidance without JSON-LD or conformance claims.

## Phase evidence

| Phase | Evidence |
|---|---|
| Foundation | Installed version categories, URI extension namespace, raw JSON and three identity domains pass focused tests. |
| US1 — references | Text/page/table/pointer anchors, declared IDs, fixed-point bounds and stale source pins pass. |
| US2 — native/projection | Exact provider/native recipe, content-addressed retrieval, thin-surface audit and aggregate scope pass. |
| US3 — trust/version | All ten allowed trust transitions and six promotion classes are tested; data/non-execution is enforced. |
| US4 — conformance | Nine schemas are current; seven valid, eight invalid, one record set and six exact JCS vectors pass offline. |
| Compatibility | Five old schema hashes and the F002 canonical-vector hash match the F005A baseline; dependencies are unchanged. |

## Full local validation

| Gate | Result |
|---|---|
| `uv run --locked ruff check .` | pass |
| `uv run --locked ruff format --check .` | pass; 71 files |
| `uv run --locked mypy src` | pass; 33 source files |
| `uv run --locked mypy src --platform win32` | pass; 33 source files |
| `uv run --locked pytest` | pass; 476 tests, 86.71% branch coverage (required ≥85%) |
| `uv run --locked python scripts/generate_schemas.py --check` | pass; all 9 schemas current |
| evidence conformance validator | pass; 7 valid, 8 invalid, 1 record set, 6 identity vectors |
| `uv run --locked python scripts/validate_repository.py` | pass; zero diagnostics |
| F005 schema/vector no-diff | pass |
| `uv build` | source and wheel distributions built |
| isolated offline wheel import | pass; package `0.0.1`, evidence contract `0.1.0` |
| `git diff --check` | pass |

## Final Spec Kit analysis

The post-implementation analysis covers 27 functional requirements, eight measurable
success criteria, four independently testable user stories, 52 implementation tasks,
and both completed checklists (56 checks total). It found no critical or high
contradiction, no uncovered requirement or success criterion, no unresolved
clarification marker, and no provider/storage/runtime leakage in the four generated
schema roots. No implementation change was required by the analysis.

## Convergence

Convergence completed cleanly after analysis. Both feature checklists are complete,
all 52 tasks are satisfied, and the schema, standalone conformance, and repository
validators remain green. The convergence assessment made no changes to `tasks.md` and
found no follow-up implementation task to append.

## Tradeoffs and residual risks

- Fixed-point page geometry uses exact integer parts-per-million. This sacrifices
  arbitrary sub-millionth precision in exchange for portable deterministic bounds and
  identity; a future coordinate profile can evolve independently if evidence requires
  more precision.
- Text offsets are Unicode code-point positions in a provider-profile text view. They are
  not claimed equivalent across providers and require the retained native artifact for
  interpretation.
- Provider pointers are deliberately opaque bounded strings. Core validation can reject
  malformed structure but cannot prove provider-specific target existence; F007 adapter
  tests and F016 independent conformance own those checks.
- Schema validation expresses structure and scalar bounds; recomputed identifiers,
  rectangle sums, trust transitions, and cross-record scope remain documented semantic
  checks. Independent consumers must implement both layers.
- `TrustClassification` records origin/effective zones but does not implement an
  administrative promotion workflow; promotion remains outside the document-data
  boundary.
- The standalone validator is adapter-independent, but it is still the Python reference
  implementation. Provider neutrality remains an experimental claim until F016 supplies
  an independent producer or consumer.
- W3C mappings are guidance only. No JSON-LD/RDF canonicalization, remote context,
  formal profile, or external conformance claim is included.

## Rollback

Revert the isolated F006 feature commit or merge commit. There is no workspace migration,
runtime data mutation, dependency rollback, or adapter state to recover. F006 records are
experimental derived metadata and may be discarded/rebuilt; existing F002/F005 records
and schemas remain valid.

## Remote verification

- Feature commit: `2d746bea859aa399f23d3e88c55540205c8784cc`.
- Pull request [#8](https://github.com/Noetheon/OpenARDP/pull/8) merged on
  2026-07-26 as `0162bd839c0cd67c66201efcbfd9610ab5899d5c`.
- PR-head workflow
  [30203968571](https://github.com/Noetheon/OpenARDP/actions/runs/30203968571)
  passed all locked gates on macOS (47 s), Ubuntu (1 min 4 s), and Windows
  (2 min 5 s).
- Post-merge `main` workflow
  [30204051975](https://github.com/Noetheon/OpenARDP/actions/runs/30204051975)
  passed all locked gates on macOS (45 s), Ubuntu (1 min 6 s), and Windows
  (2 min 3 s).
- Both workflows ran the 476-test network-blocked suite, distribution builds, and
  tracked-file drift verification.
