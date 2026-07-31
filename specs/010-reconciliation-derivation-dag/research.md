# Research: Reconciliation and Derivation DAG

## Decision 1 — Reconcile F002 blocks, not opaque rich projections

**Decision**: F010 operates on complete verified `RepresentationAggregate.blocks` and
their canonical `ContentBlock` CAS records. It does not invent F002 blocks for rich
representations or infer provider-neutral identity from F006 opaque pointers.

**Rationale**: ADR 0008 deliberately keeps rich projections thin and provider pointers
opaque. The existing `same_logical_block_as` relation also requires two F002
`BlockReference` endpoints. Extending that public boundary opportunistically would
make Docling assumptions provider-neutral without conformance evidence.

**Alternatives considered**:

- Treat each `EvidenceProjection` as an artifact relation: rejected because projection
  identity is source/native-bound and the public relation would not express a logical
  evidence lineage.
- Parse native JSON inside reconciliation: rejected because the provider-neutral core
  must not interpret provider internals.

## Decision 2 — Lineage plus exact content is the reuse key

**Decision**: Persist a deterministic block lineage and derive a separate evidence
binding digest from `(lineage_id, canonical_hash)`. Derivations consume binding digests,
not bare text similarity or mutable block handles.

**Rationale**: A block handle may change with source location; a canonical content hash
may be duplicated in unrelated locations. The pair preserves logical continuity and
exact input identity. It also makes A→B→A naturally converge to the old binding.

**Alternatives considered**:

- Keep the old `block_id`: rejected because rewriting the new immutable block would
  falsify its accepted representation object.
- Content hash alone: rejected because duplicate boilerplate becomes an unsafe reuse
  oracle.
- Full old/new block object hash: rejected because source/version fields make otherwise
  unchanged logical content differ and prevent safe reuse.

## Decision 3 — Conservative phased matcher with a hard reuse rule

**Decision**: A pure matcher uses fixed deterministic phases:

1. unique namespaced native stable ID with same kind;
2. unique exact canonical hash with same kind and compatible mapped parent/root;
3. unique exact asset identity or canonical structured-table identity in that
   neighborhood;
4. unique mutual-best normalized-text similarity with same kind, mapped parent/root,
   bounded order displacement, minimum score and minimum winner margin;
5. bounded sibling-gap alignment using exact signatures only.

Every phase consumes one-to-one assignments. Ties, collisions, incompatible parent
context, limit overflow or insufficient margin remain unmatched. Regardless of match
phase, `reusable=true` requires exact canonical-hash equality.

**Rationale**: Phase ordering follows canonical incremental-processing guidance while
making the safety property independent from heuristic quality. Similarity may retain a
lineage across an edit, but it cannot transfer a derivative whose input changed.

**Fixed v1 bounds/configuration**:

| Setting | Value | Failure behavior |
|---|---:|---|
| blocks per scope | 100,000 | reject before pairwise work |
| hierarchy depth inspected | 32 | reject malformed/deeper aggregate |
| normalized text per comparison | 4,096 code points | compare deterministic prefix and length digest facts |
| similarity candidate window | ±8 sibling orders | candidates outside are ignored |
| minimum similarity | 0.97 | below remains new |
| minimum winner margin | 0.05 | tie/near-tie remains new |
| similarity comparisons | 1,000,000 | reject before exceeding |
| sibling alignment gap | 256 | larger ambiguous gap remains new, not an error |

The config is canonicalized and hashed; changing any value changes the algorithm
configuration and requires new evidence, not silent drift.

**Alternatives considered**:

- Global quadratic similarity: rejected as unbounded and denial-of-service prone.
- Greedy first-match: rejected because input ordering could choose a different edge.
- Lower threshold for recall: rejected because continuity recall is secondary to the
  zero-false-reuse gate.

## Decision 4 — Internal lifecycle wraps frozen public generation records

**Decision**: Keep `DerivationRecord 0.1.0` unchanged. A successful F010 node stores a
canonical F002 `READY` record object and maps it to internal `CURRENT`; a failed node
stores a canonical `FAILED` record and maps it to internal `FAILED`. `STALE` and
`SUPERSEDED` are current-workspace eligibility states.

**Rationale**: The record already binds the required ordered inputs and complete recipe
identity. Changing its public enum would be a breaking contract revision. Runtime
eligibility against mutable heads is a separate concern and does not belong inside an
immutable CAS object.

**Alternatives considered**:

- Add `CURRENT` and `SUPERSEDED` to schema 0.1.0: rejected as an in-place break.
- Publish schema 0.2.0 in F010: rejected because no interchange consumer requires the
  runtime lifecycle and it would enlarge the feature without evidence.

## Decision 5 — Typed direct dependency edges

**Decision**: Each ordered direct input has one of three kinds:

- `EVIDENCE_BINDING`: digest must exist in a persisted lineage membership; it is
  eligible only if that membership is present at a current document head.
- `OBJECT`: digest must be a verified registered CAS object.
- `DERIVATION_OUTPUT`: digest must equal the verified `output_hash` of the named
  producer artifact.

The ordered edge digests must equal `DerivationRecord.input_hashes` exactly.

**Rationale**: Hashes alone cannot tell the engine whether head changes affect them or
which producer edge supplies transitive invalidation. Explicit kind is required for
exact lifecycle computation without changing the recipe identity.

**Alternatives considered**:

- Infer producer edges by comparing hashes: rejected because an object can share an
  output digest and inference becomes ambiguous.
- Store only transitive dependencies: rejected because they are reproducible from
  direct edges and would create drift.

## Decision 6 — Slot ownership separates stale from superseded

**Decision**: A domain-separated derivation slot represents one namespace, subject
digest and purpose. At most one node per slot is `CURRENT`. New publication atomically
marks every prior nonterminal (`CURRENT` or `STALE`) node in the slot `SUPERSEDED`
before installing the replacement. Invalidation clears the current pointer and marks
the occupant `STALE`. Revalidation can reclaim only an empty matching slot with no
later replacement.

**Rationale**: `STALE` means dependency eligibility failed; `SUPERSEDED` means another
output was deliberately selected for the same purpose. Treating them separately makes
rollback and audit truthful.

## Decision 7 — CAS-first and one SQLite transaction

**Decision**: Services canonicalize, write and reverify relation/record/output objects
before calling one catalog transaction. Reconciliation commits the run, lineages,
members, relation roots and lifecycle transitions together. Derivation publication
commits the node, edges, slot transition and event together.

F002 relation provenance uses the target representation's immutable `ready_at` as its
creation time. It never uses retry wall-clock time, so a crash after relation CAS
publication and an exact retry reproduce the same canonical relation bytes. Operational
run/lineage timestamps are first-writer facts excluded from identity/result comparison.

**Rationale**: This is the accepted ADR 0002 cross-resource order. SQLite readers never
observe a missing referenced object; a crash can leave only a complete unreachable CAS
leaf. Same-identity retry converges by comparing complete canonical facts.

**Fault checkpoints**:

- after each CAS object publication;
- after run/node insert;
- after lineage/edge inserts;
- after relation/object registration;
- after state closure updates;
- after event inserts;
- immediately before commit.

Cancellation uses the existing callback shape and is checked before expensive phases,
between bounded matching groups and before transaction commit.

## Decision 8 — Cycle prevention and deterministic closure

**Decision**: A producer dependency must already exist and be `CURRENT`. Publication
rejects self-dependency and checks producer ancestry with a recursive CTE before insert.
Invalidation computes the affected closure from changed evidence-binding inputs and
producer edges, then updates nodes/events in `(depth, artifact_id)` order. Revalidation
iterates stale candidates sorted by `artifact_id` until a full pass makes no change.

**Rationale**: Existing-producer publication naturally prevents most cycles, but the
explicit query defends migrated/corrupt state and documents the aggregate invariant.
Stable ordering makes events and tests reproducible.

**Alternatives considered**:

- Recursive Python traversal after reading the whole graph: rejected as memory-heavy
  and race-prone between read and write.
- Database triggers: rejected because lifecycle policy and sanitized errors belong in
  the catalog adapter/service, while triggers obscure fault injection.

## Decision 9 — Additive revision 7 and reachability roots

**Decision**: Checksummed migration 7 adds only new STRICT tables/indexes. Relation
objects, derivation record objects and successful output objects become reachability
roots. Existing revisions, schemas, objects and indexes are untouched.

**Rationale**: Runtime lifecycle needs durable queryable state. Additive migration
supports populated workspaces and preserves the explicit backup/restore downgrade
model used by Features 007–008.

## Decision 10 — No CLI/MCP mutation or background scheduling

**Decision**: F010 delivers pure domain APIs plus provider-neutral service/catalog
ports. Demonstration uses synthetic service-level quickstart/tests. The read-only MCP
surface remains byte-frozen; scheduling reconciliation belongs to F012.

**Rationale**: A CLI publication format would require exposing paths or arbitrary
generator outputs before a real enrichment provider exists. A watcher/job path would
cross the next feature boundary. The independently testable service is the smallest
coherent capability needed by later orchestration.

## Dependency and supply-chain review

- No new dependency is required. Matching uses bounded stdlib algorithms and existing
  Pydantic/JCS helpers.
- `pyproject.toml` and `uv.lock` remain unchanged.
- Unit tests prohibit network access; fixtures are synthetic and generated in-tree.

## Known limitations

- Exact rich projection lineage remains future work; exact rich artifact hashes can be
  immutable inputs but cannot be current-head evidence bindings in F010.
- Similarity is a conservative continuity heuristic, not semantic equivalence.
- A slow disk may leave complete CAS orphans after cancellation; F013 owns reclamation.
- SQLite serializes writers. F010 provides correctness and idempotency evidence, not a
  multi-node throughput claim.
