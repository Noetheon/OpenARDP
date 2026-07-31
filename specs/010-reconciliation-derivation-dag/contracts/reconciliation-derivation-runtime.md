# Contract: F010 Reconciliation and Derivation Runtime

**Stability**: Internal application/port contract

**Workspace**: revision 7
**Public schema impact**: none

## Reconciliation operation

```python
reconcile(
    previous_scope: RepresentationScope,
    current_scope: RepresentationScope,
    *,
    cancellation_check: CancellationCheck | None = None,
) -> ReconciliationResult
```

Preconditions:

- scopes are distinct and identify the same `document_id`;
- both catalog aggregates are complete `READY` F002 block representations;
- every canonical block object verifies physically and semantically;
- count, hierarchy and matcher bounds are satisfied;
- if lifecycle changes are requested, `current_scope` is still the current head inside
  the commit transaction.

Postconditions:

- every block in both involved scopes has one persisted lineage membership;
- every accepted match has one canonical CAS-backed F002 relation;
- reusable matches are an exact subset of logical matches with equal content hashes;
- run/members/relations/state events are all visible or none are;
- an exact retry returns `CONVERGED` and emits no additional event.

The operation never updates source/version/representation/head/ingestion/index facts.

## Derivation publication operation

```python
publish(
    record: DerivationRecord,
    dependencies: tuple[DerivationDependency, ...],
    slot: DerivationSlotKey,
    *,
    output_chunks: Iterable[bytes] | None = None,
    failure_code: str | None = None,
    cancellation_check: CancellationCheck | None = None,
) -> DerivationPublicationResult
```

Rules:

- `READY` requires output chunks whose CAS identity equals `record.output_hash`;
- `FAILED` requires no output and one bounded failure code;
- any other F002 generation state is rejected for new publication;
- canonical record bytes are always stored and reverified;
- dependency ordinals/digests equal `record.input_hashes` exactly;
- evidence/object/producer dependencies must exist and be exact;
- producer dependencies name a current producer and match its output hash;
- cycle/self-edge and divergent same-artifact output are conflicts;
- one transaction publishes node/edges/slot/events;
- an exact retry returns `CONVERGED` without an additional event.

`output_chunks` are data bytes. No path, URL, command, provider or model identifier is
executed by the operation.

## Read operations

```python
get_reconciliation(run_id: str) -> ReconciliationResult | None
get_lineage(block: BlockReference) -> BlockLineageMembership | None
get_derivation(artifact_id: str, *, verify_objects: bool = True) -> DerivationNode | None
list_derivation_events(artifact_id: str) -> tuple[DerivationLifecycleEvent, ...]
```

Reads are deterministic and body-free. Service reads with `verify_objects=True`
rehash canonical record/output objects before returning metadata. No read repairs or
reactivates state.

## Stable failure classes

| Class | Condition | Mutation |
|---|---|---|
| `ReconciliationScopeError` | same/cross-document/non-READY/stale-current scope | none |
| `ReconciliationLimitExceeded` | fixed safety cap exceeded | none |
| `ReconciliationConflict` | same target/run has different facts | none |
| `ReconciliationIntegrityError` | block/relation/CAS/catalog drift | none |
| `DerivationDependencyError` | dependency absent/ineligible/hash mismatch | none |
| `DerivationCycleError` | self/transitive cycle | none |
| `DerivationConflict` | identity/output/slot/state conflict | none |
| `DerivationIntegrityError` | record/output/row/CAS drift | none |
| cancellation exception | callback requests stop before commit | none visible |

Messages are fixed and body-free. Raw SQLite text, paths, document content, prompt
content and output bytes are never part of the contract.

## Determinism and limits

- Algorithm: `openardp-block-reconcile-v1` with the configuration in `research.md`.
- Sort keys use exact scope/reference fields and ordinals.
- Confidence is planned as fixed-point ppm and converted once for the F002 relation.
- UTC publication time is the only non-identity/non-result volatile fact.
- Complete results are capped by the existing 100,000-block representation limit and
  the stricter comparison/window bounds.

## Compatibility

- This is an internal application/port contract, not a twelfth JSON Schema root.
- The F002 record remains the canonical immutable generation object.
- Workspace revision 7 is required for persistence; revision-6 workspaces are upgraded
  explicitly by the existing initializer.
- The F009 MCP server remains read-only and has no F010 tool.
