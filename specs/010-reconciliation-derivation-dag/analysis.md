# Cross-Artifact Analysis: F010 Reconciliation and Derivation DAG

**Analyzed**: 2026-07-31

**Phase**: Post-implementation convergence
**Artifacts**: Constitution 2.0.0, AGENTS.md, ADRs 0002/0006/0008/0009/0010/0011,
canonical architecture/incremental guidance, feature prompt, spec, research, data model,
plan, runtime contract, checklists and tasks.

## Result

**PASS — zero unresolved critical or high findings. Implementation may begin.**

## Findings resolved at the originating artifact

| Severity | Finding | Resolution | Source corrected |
|---|---|---|---|
| CRITICAL | F002 relation identity excludes provenance time, but canonical relation bytes include it; using retry wall-clock time would make CAS-first crash retry diverge under the same relation ID. | Relation provenance is the target representation's immutable `ready_at`; operational timestamps are excluded from identity/convergence comparison. | spec clarification, research Decision 7, data model, plan, ADR 0011 |
| HIGH | A stale artifact clears the current slot pointer; later publication could leave it stale and therefore eligible for A→B→A reactivation despite an intentional replacement. | Replacement atomically supersedes every prior `CURRENT` or `STALE` node in the slot. Only never-replaced stale nodes may reactivate. | spec clarification, research Decision 6, data model, ADR 0011 |
| HIGH | Spec Kit still pointed at converged F009 and would route prerequisite/lifecycle scripts to the wrong feature. | `.specify/feature.json` now names `specs/010-reconciliation-derivation-dag`; prerequisite discovery resolves all F010 planning artifacts. | `.specify/feature.json` |
| HIGH | The concise feature prompt names `CURRENT/STALE/FAILED/SUPERSEDED`, while frozen public F002 `DerivationRecord 0.1.0` uses a different generation-state enum. An in-place edit would break a public schema. | ADR 0011 separates immutable public generation facts from internal current-workspace eligibility. No public schema changes. | spec clarifications/FR-012, research Decision 4, ADR 0011 |
| HIGH | A historical reconciliation caller could invalidate a newer document head after planning outside the transaction. | The catalog transaction rechecks whether the target is the current head before any lifecycle change; historical reconciliation cannot mutate current eligibility. | plan architecture/concurrency, runtime contract |
| MEDIUM | Rich F007 projections have no F002 block endpoints; silently reconciling opaque pointers would violate provider neutrality. | F010 scope is verified F002 block aggregates only; exact rich artifact hashes remain valid ordinary object inputs. | spec clarification/non-goals, research Decision 1 |
| MEDIUM | Similarity-based logical matching could be mistaken for derivative reuse authority. | `reusable` is a separate hard rule requiring accepted lineage continuity and exact canonical-hash equality. Corpus precision is an unconditional 1.000 gate. | spec FR-008/SC-001, research Decisions 2–3, checklists |

## Coverage matrix

| Concern | Spec | Plan/research | Tasks | Status |
|---|---|---|---|---|
| immutable originals and prior records | FR-021/022/027 | CAS-first, additive migration | T023, T054, T067 | covered |
| deterministic conservative matching | FR-002–008 | Decisions 2–3, matcher design | T013–T021 | covered |
| bounded resource behavior | FR-004 | fixed v1 bounds | T013, T017, T020 | covered |
| canonical relations/provenance | FR-005/009 | stable ready-at provenance | T021, T029, T033–034 | covered |
| exact recipe/dependency identity | FR-013–016 | Decisions 4–5 | T037–045 | covered |
| transactional/idempotent/restartable | FR-009–011/016 | Decision 7, fault points | T027–030, T040–044 | covered |
| cycle safety | FR-016 | recursive ancestry | T039, T041 | covered |
| exact transitive invalidation | FR-018 | deterministic recursive closure | T046–049 | covered |
| supersession semantics | FR-017/020 | Decision 6 | T050–051 | covered |
| A→B→A historical reuse | FR-019–021 | revalidation fixed point | T052–055 | covered |
| migration/downgrade/reachability | FR-022–024 | revision 7 plan | T022–025, T057–059 | covered |
| privacy/untrusted input | FR-025 | body-free service boundary | T036, T059 | covered |
| dependency/network/provider freeze | FR-026–027 | no dependency/interface change | T004, T067–068 | covered |
| cross-platform measured evidence | FR-028, SC-001–010 | corpus/full gate | T064–070 | covered |

## Traceability and dependency audit

- Every FR maps to at least one file-scoped task and measurable test/gate.
- Test tasks precede their implementation tasks within each dependency phase.
- Migration/protocol work precedes catalog mutation; pure matcher evidence precedes
  reconciliation persistence; publication precedes lifecycle closure integration.
- No task authorizes F011+ runtime behavior.
- ADR 0011 is accepted before any new persisted identity or migration implementation.

## Compatibility audit

- Eleven public schemas: unchanged by plan.
- Existing identity algorithms/vectors: unchanged; four additive internal domains.
- F006 conformance corpus: unchanged.
- F009 MCP interface/descriptors: unchanged.
- `pyproject.toml` and `uv.lock`: unchanged; stdlib/existing dependencies only.
- Workspace: one additive checksummed revision 7 with backup/restore downgrade truth.

## Residual design risks (non-blocking)

- Conservative ambiguity handling may reduce logical-match recall. Recall is reported,
  while false reuse remains a hard failure.
- SQLite recursive closure and writer serialization may limit very large DAG throughput;
  F010 makes no performance claim before F015 benchmark evidence.
- Rich projection lineages remain intentionally absent, limiting reuse breadth without
  weakening provider neutrality.
- Interrupted CAS-first publication can leave complete unreachable objects until F013.

These limitations are explicit, bounded and do not contradict acceptance criteria.

## Post-implementation convergence

**PASS — zero unresolved critical or high findings.** The implemented domain models,
revision-7 storage, services, tests and operational documentation preserve the analyzed
boundaries. Re-analysis found no public-schema, prior-identity, F006 corpus, F009
descriptor, dependency or lockfile drift against rollback commit
`1e2992c294cf67bc1f87ab58dbfa4b2555f264e6`.

The executable evidence covers 130 labelled decisions with zero false reuse and exact
precision/recall of 1.000; 20-process identity and 10-process complete-plan determinism;
all 14 migration-statement fault boundaries; concurrent installers and publishers;
100 independently generated DAG closure cases; exact invalidation, supersession and
A→B→A reactivation; CAS reachability/corruption handling; and hostile-content privacy
boundaries. The full 919-test repository suite passes at 86.87 percent branch-aware
coverage. PR-head CI and post-merge `main` CI both passed the locked quality gate on
Ubuntu, macOS and Windows, closing T070 with zero remaining convergence finding.
