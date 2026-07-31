# Data Model: Reconciliation and Derivation DAG

## Version dimensions

| Dimension | F010 value | Impact |
|---|---|---|
| application | package release | additive services/models |
| workspace | SQLite revision `7` | additive migration from revision 6 |
| reconciliation algorithm | `openardp-block-reconcile-v1` | fixed phases and bounds |
| persisted identity | new version-1 lineage/binding/run/slot domains | ADR 0011 |
| public F002/F006/F008 contracts | unchanged | eleven schemas frozen |
| MCP interface | `0.1.0` unchanged | no new or mutable tool |
| provider/export profiles | unchanged | no provider/export behavior |

## Pure domain records

### `ReconciliationBlock`

| Field | Rule |
|---|---|
| `reference` | exact F002 `BlockReference` |
| `parent_id` | block UUID or null; parent must occur earlier in the same aggregate |
| `kind` | F002 `BlockKind` |
| `order` | non-negative contiguous sibling order |
| `ordinal` | contiguous aggregate order |
| `canonical_hash` | exact verified F002 content hash |
| `text` | untrusted string or null; bounded before similarity |
| `structured_hash` | SHA-256 of canonical structured content or null |
| `asset_id` | exact SHA-256 asset identity or null |
| `native_stable_id` | optional bounded namespaced opaque string |
| `lineage_id` | prior persisted lineage for old-scope blocks; null for new blocks |

The model contains no source path and grants no authority. `native_stable_id` is read
only from the explicit F002 `SourceLocator.native_id` field and is treated as bounded
opaque data.

### `BlockLineageMembership`

| Field | Rule |
|---|---|
| `lineage_id` | ADR 0011 lineage identity |
| `block` | exact block reference |
| `canonical_hash` | exact block content hash |
| `binding_digest` | recomputed ADR 0011 `(lineage_id, canonical_hash)` identity |
| `introduced_by_run_id` | F010 reconciliation-run identity |

One scope contains every block exactly once. One lineage contains at most one block per
scope and never crosses `document_id`.

### `ReconciliationMatch`

| Field | Rule |
|---|---|
| `previous` / `current` | distinct-scope block references for the same document |
| `lineage_id` | previous block's lineage inherited by current |
| `method` | `native_id`, `exact_content`, `asset_or_table`, `similarity`, `sequence` |
| `confidence_ppm` | deterministic integer 0..1,000,000; float relation value derives from it |
| `reusable` | true only when canonical hashes are exact-equal |
| `relation` | valid F002 `same_logical_block_as`; current source → previous target |
| `relation_object` | canonical CAS object for the relation |

Fixed-point confidence avoids cross-platform floating comparison during planning. The
public F002 relation receives `confidence_ppm / 1_000_000`. Relation provenance uses
the target representation's immutable `ready_at`, making canonical bytes retry-stable.

### `ReconciliationPlan`

| Field | Rule |
|---|---|
| `run_id` | exact prior/target/config identity |
| `previous_scope` / `current_scope` | same document, distinct READY scopes |
| `algorithm_version` | `openardp-block-reconcile-v1` |
| `config_hash` | canonical fixed v1 matcher config |
| `memberships` | complete current-scope memberships in ordinal order |
| `seed_memberships` | missing previous-scope memberships seeded in ordinal order |
| `matches` | deterministic current ordinal order |
| `inactive_binding_digests` | old bindings absent from current scope, sorted unique |
| counts | matched/reusable/new/ambiguous and comparisons, bounded |
| `result_fingerprint` | canonical digest of all non-time result facts |
| `created_at` | UTC commit time; excluded from result fingerprint |

### `DerivationLifecycleState`

Exactly `CURRENT`, `STALE`, `FAILED`, `SUPERSEDED`.

### `DerivationDependency`

| Field | Rule |
|---|---|
| `ordinal` | contiguous from zero |
| `kind` | `EVIDENCE_BINDING`, `OBJECT`, `DERIVATION_OUTPUT` |
| `input_digest` | exact SHA-256 input in the F002 recipe |
| `producer_artifact_id` | required only for `DERIVATION_OUTPUT` |

Evidence bindings must exist in lineage history. Objects must exist in the object
catalog and verify physically. Producer inputs require a current successful producer
whose output hash equals `input_digest`.

### `DerivationSlotKey`

| Field | Rule |
|---|---|
| `namespace` | 1..128 lowercase token/period/hyphen characters |
| `subject_digest` | SHA-256 identity, usually a lineage/document/task identity |
| `purpose` | 1..128 lowercase token/period/hyphen characters |
| `slot_id` | recomputed ADR 0011 identity |

### `DerivationPublication`

| Field | Rule |
|---|---|
| `record` | valid F002 `DerivationRecord`, state `READY` or `FAILED` only |
| `record_object` | exact canonical record CAS object |
| `output_object` | required and equals `output_hash` for READY; null for FAILED |
| `dependencies` | ordered exact match to `record.input_hashes` |
| `slot` | deterministic slot key |
| `failure_code` | bounded machine token only for FAILED |
| `published_at` | UTC and not before record creation/completion |

### `DerivationNode`

| Field | Rule |
|---|---|
| `artifact_id` | exact F002 recipe identity |
| `slot_id` | derivation slot identity |
| `state` | internal lifecycle state |
| `record_object` | verified canonical generation-record object |
| `output_object` | verified output for successful nodes; null for failed |
| `dependencies` | complete ordered direct edges |
| `revision` | starts at 1 and increments per actual lifecycle transition |
| `created_at` / `updated_at` | UTC monotonic |
| `failure_code` | present only for FAILED |
| `row_fingerprint` | recomputed body-free row/edge identity |

Canonical record/output objects are immutable. State, revision, slot occupancy and
events are mutable catalog facts.

### `DerivationLifecycleEvent`

| Field | Rule |
|---|---|
| `artifact_id` / `sequence` | append-only per artifact |
| `from_state` | null only for initial publication |
| `to_state` | exact new state |
| `reason` | `published`, `generation_failed`, `dependency_inactive`, `reactivated`, `slot_replaced` |
| `run_id` | reconciliation run causing stale/reactivate, otherwise null |
| `occurred_at` | UTC, monotonic per node |

## State machines

### Successful node

```text
(absent) --publish--> CURRENT
CURRENT --dependency inactive--> STALE
CURRENT --slot replacement--> SUPERSEDED
STALE --all exact dependencies current and slot empty--> CURRENT
STALE --slot replacement--> SUPERSEDED
SUPERSEDED --automatic action--> prohibited
```

### Failed node

```text
(absent) --publish failed record--> FAILED
FAILED --automatic action--> prohibited
```

Publishing the same immutable node is convergence, not a transition. A new artifact
for a slot moves every prior `CURRENT` or `STALE` node in that slot to `SUPERSEDED`;
this prevents a replaced stale artifact from later reactivating. A recipe-identity
collision with different record/output/dependencies is a conflict.

## Migration 7 tables

### `reconciliation_runs`

Primary key `run_id`; exact prior and target scope foreign keys; algorithm/config;
result fingerprint; bounded counts; UTC creation. Unique target scope ensures one
authoritative lineage assignment for that representation.

### `block_lineages`

Primary key `lineage_id`; document and origin block reference; run/time. Origin block
has a restrictive foreign key to `representation_blocks`.

### `block_lineage_members`

Primary key `(document_id, version_id, representation_id, block_id)`; unique
`(lineage_id, version_id, representation_id)`; exact content/binding digests; run FK;
restrictive block/scope FKs. Indexed by binding digest and lineage.

### `reconciliation_relations`

Primary key `relation_id`; run FK; canonical relation object FK; method, fixed-point
confidence and reusable flag; explicit previous/current member keys. Relation object
is a reachability root.

### `derivation_slots`

Primary key `slot_id`; namespace, subject digest, purpose; nullable current artifact.
Unique key facts reproduce the identity.

### `derivation_nodes`

Primary key `artifact_id`; slot FK; lifecycle state; record/output object FKs; recipe
columns required for conflict diagnosis; revision, times, failure code and fingerprint.
A partial unique index enforces at most one `CURRENT` node per slot.

### `derivation_dependencies`

Primary key `(artifact_id, ordinal)`; unique `(artifact_id, input_digest)` consistent
with F002 input uniqueness; kind; optional producer FK; shape checks.

### `derivation_events`

Primary key `(artifact_id, sequence)`; from/to state, reason, optional run FK, UTC time.

## Transaction invariants

1. A visible reconciliation run has complete target memberships and all relation
   objects registered; result fingerprint recomputes.
2. A visible successful node has its record/output objects and every ordered dependency.
3. `CURRENT` implies the slot points to that artifact, and no second current occupant
   exists. Non-current nodes are never the slot's current artifact.
4. `DERIVATION_OUTPUT` edges point to existing successful producers and match their
   output hashes.
5. Producer ancestry is acyclic.
6. Every actual lifecycle state change increments revision once and appends one event;
   no-op retries do neither.
7. All catalog object references are registered only after physical CAS verification.

## Error taxonomy

| Exception | Stable meaning |
|---|---|
| `ReconciliationScopeError` | wrong document/order/same/non-READY scope |
| `ReconciliationLimitExceeded` | a fixed safety bound would be exceeded |
| `ReconciliationConflict` | target/run already has different facts |
| `ReconciliationIntegrityError` | canonical block/relation/catalog/CAS facts drift |
| `DerivationDependencyError` | missing/ineligible/mismatched dependency |
| `DerivationCycleError` | self or transitive producer cycle |
| `DerivationConflict` | same identity diverges or slot/state conflict |
| `DerivationIntegrityError` | record/output/row/CAS facts drift |
| existing cancellation | cooperative callback raised before commit |

Messages are body-free. Public interfaces, if added later, map them without exposing
paths, content, prompt text or outputs.

## Reachability

Add these object roots to `ReferenceSnapshot`:

- every `reconciliation_relations.relation_object_id`;
- every `derivation_nodes.record_object_id`;
- each non-null `derivation_nodes.output_object_id`.

Historical stale/superseded nodes remain roots. F010 never deletes or quarantines.
