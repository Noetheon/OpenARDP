# Feature Specification: Reconciliation and Derivation DAG

**Feature Branch**: `codex/f010-reconciliation-derivation-dag`

**Created**: 2026-07-31

**Status**: Converged, merged and remotely verified

**Input**: Reuse valid evidence across small edits without false identity reuse and
invalidate dependent derivatives exactly. Matching is deterministic and conservative,
ambiguity creates new evidence, derivations bind exact inputs and complete generator
identities, publication is transactional/cycle-safe/idempotent/restartable, and an
A→B→A source sequence can converge to immutable prior artifacts.

## Clarifications

### Session 2026-07-31

- Q: Does F010 replace or break the public F002 `DerivationRecord 0.1.0`? → A: No.
  The frozen public record remains the immutable generation-result contract. F010 adds
  internal workspace lifecycle state (`CURRENT`, `STALE`, `FAILED`, `SUPERSEDED`) and
  maps accepted `READY`/`FAILED` generation records into that catalog lifecycle. A
  future public contract revision requires its own compatibility decision.
- Q: What is the safe unit of cross-version reuse? → A: A version-independent block
  lineage plus the exact canonical block-content digest. The resulting evidence-binding
  digest changes when either lineage or content changes. Content equality alone never
  resolves an ambiguous lineage, and logical similarity alone never permits reuse.
- Q: Can a similarity match transfer summaries, captions or embeddings? → A: No.
  Similarity may establish a `same_logical_block_as` relation when the match is unique
  and conservative, but reuse is allowed only when the old and new canonical content
  hashes are byte-identical and every other derivation input identity is unchanged.
- Q: Are rich-provider projections reconciled in this feature? → A: F010 reconciles
  canonical F002 block aggregates. F007 deliberately does not fabricate F002 blocks;
  rich projection reconciliation requires a separately designed provider-neutral
  lineage surface and is not silently inferred from opaque provider pointers here.
  Exact rich retrieval hashes may still be ordinary immutable derivation inputs.
- Q: How are invalidation and historical reuse reconciled? → A: Mutable lifecycle state
  expresses eligibility against current document heads; immutable recipes and outputs
  remain retained. Head changes stale the exact transitive dependants of inactive
  evidence bindings. If A becomes current again, the engine revalidates the old exact
  dependency closure and can reactivate the same immutable artifact without generation.
- Q: What makes publication restartable without a `PENDING` node state? → A: Output and
  canonical record objects are published to CAS first and reverified, then one SQLite
  transaction publishes the node, direct edges, slot transition and event. A crash or
  cancellation before commit leaves only complete unreachable objects; retry is
  idempotent and converges. F013 owns later orphan reclamation.
- Q: What owns `SUPERSEDED`? → A: A deterministic derivation slot identifies one logical
  output purpose. Publishing a different valid artifact into the same slot atomically
  moves the prior occupant to `SUPERSEDED`; dependency invalidation instead uses
  `STALE`. These states are not aliases.
- Q: Is automatic reconciliation part of ingestion or the watcher? → A: No. F010
  exposes an explicit service/catalog operation over two already-READY scopes. F012
  may schedule it later; F010 must not add file watching, queues or background work.
- Q: How can relation publication be byte-stable across a crash/retry? → A: Relation
  provenance uses the target representation's immutable `ready_at`, not a retry-time
  clock. Run/lineage operational timestamps are stored only by the winning transaction
  and are excluded from identity/result comparison; a converging retry returns them.
- Q: What happens to a stale prior artifact when a replacement publishes into its
  slot? → A: Publication supersedes every prior nonterminal (`CURRENT` or `STALE`)
  artifact in that slot before installing the replacement. A stale artifact can
  reactivate only while no later replacement has superseded it.

## User Scenarios & Testing

### User Story 1 - Reconcile Small Edits Conservatively (Priority: P1)

As a local application service, I can reconcile two READY representations of the same
logical document into deterministic lineages and `same_logical_block_as` relations,
while every ambiguous candidate receives a new lineage.

**Why this priority**: Safe logical continuity is the prerequisite for any reuse or
invalidation claim.

**Independent Test**: Run a synthetic edit corpus containing insertions, deletions,
moves, duplicate boilerplate, similar-but-distinct paragraphs, tables/assets and
ambiguous reorderings; compare the complete plan and persisted result with labelled
ground truth across repeated processes and platforms.

**Acceptance Scenarios**:

1. **Given** unique blocks whose exact content survives a line/order shift, **When**
   the scopes are reconciled, **Then** each new block inherits the prior lineage,
   receives a deterministic relation and is classified reusable.
2. **Given** one uniquely similar edited block in the same bounded structural
   neighborhood, **When** confidence and margin thresholds pass, **Then** logical
   continuity is recorded but reuse remains false because its content digest changed.
3. **Given** duplicate or tied candidates, **When** no phase can choose uniquely,
   **Then** the new block receives a new deterministic lineage and no relation or reuse
   edge is emitted.
4. **Given** different documents, non-READY scopes, corrupt block objects or an
   already reconciled target with conflicting facts, **When** reconciliation is
   requested, **Then** it fails closed without visible partial rows.

---

### User Story 2 - Publish Exact Derivations Transactionally (Priority: P2)

As an enrichment component, I can publish a successful or failed derivation with exact
ordered inputs, complete generator/model/config/prompt identity and one logical output
slot, and retries converge without duplicate or divergent results.

**Why this priority**: A dependency graph is useful only when every node is
reproducible, physically verified and atomically visible.

**Independent Test**: Publish leaf and multi-level synthetic derivations, retry the
same commits, inject transaction faults/cancellation at every boundary, attempt a
conflicting output and a cycle, and inspect node/edge/event visibility from a second
connection.

**Acceptance Scenarios**:

1. **Given** verified input bindings and a verified CAS output matching a valid F002
   derivation recipe, **When** publication commits, **Then** the node, ordered direct
   dependencies, current slot and append-only event become visible atomically.
2. **Given** the exact same publication after a crash or retry, **When** it is
   submitted again, **Then** the existing artifact is returned as converged with no
   duplicate row or event.
3. **Given** the same recipe identity with different output bytes or metadata,
   **When** publication is attempted, **Then** it fails as a deterministic conflict
   and preserves the accepted artifact.
4. **Given** a dependency edge that is missing, stale, output-mismatched or would form
   a cycle, **When** publication is attempted, **Then** no node, edge, slot movement or
   event is committed.

---

### User Story 3 - Invalidate and Reactivate Exact Dependency Closures (Priority: P3)

As an operator, a document-head edit stales exactly the current derivations that
depend transitively on bindings no longer active, leaves unrelated branches current,
and reactivates reusable historical artifacts when their complete exact inputs become
current again.

**Why this priority**: Exact invalidation is the safety property that prevents stale
summaries or embeddings from masquerading as current evidence.

**Independent Test**: Build a branching DAG with shared dependencies, edit one table
lineage, reconcile A→B and then B→A, and assert the precise state/event set after each
transition, including repeated, cancelled and fault-injected runs.

**Acceptance Scenarios**:

1. **Given** a leaf binding whose content changes, **When** the new scope is
   reconciled, **Then** every current direct and transitive dependant becomes `STALE`
   in deterministic order and no unrelated derivation changes.
2. **Given** a replacement artifact for the same slot, **When** it publishes,
   **Then** the old occupant becomes `SUPERSEDED` atomically while the replacement is
   `CURRENT`.
3. **Given** a prior A scope becomes current after A→B→A, **When** reconciliation
   completes, **Then** stale nodes whose complete dependency closure is again exact
   become `CURRENT` without rewriting their record/output objects.
4. **Given** repeated invalidation or revalidation with no state change, **When** the
   operation retries, **Then** it is a no-op with no duplicate lifecycle events.

---

### User Story 4 - Upgrade, Inspect and Recover Safely (Priority: P4)

As a workspace operator, I can upgrade revision 6 to the additive F010 schema,
inspect deterministic body-free reconciliation/derivation facts, and rely on explicit
rollback and recovery limitations.

**Why this priority**: Lifecycle metadata is persisted evidence; migration and
operational truth are part of correctness.

**Independent Test**: Upgrade fresh and populated revision-6 workspaces, inject a DDL
failure, open concurrently, validate checksums/foreign keys/reachability and prove
that older software fails as too-new without mutating the workspace.

**Acceptance Scenarios**:

1. **Given** a valid revision-6 workspace, **When** initialization runs, **Then** one
   checksummed additive migration commits revision 7 with all earlier bytes/facts
   preserved.
2. **Given** a migration fault, incompatible history or concurrent initializer,
   **When** upgrade runs, **Then** the whole pending migration rolls back or converges
   to one valid revision without partial tables.
3. **Given** committed relation and derivation objects, **When** reachability is
   inspected, **Then** every referenced CAS object is a root and missing/drifted
   objects fail integrity checks rather than disappearing from the report.

### Edge Cases

- Empty representations; all blocks inserted/deleted; one block at each configured
  size/count boundary; hierarchy depth beyond the matching-context cap.
- Duplicate exact text under the same or different parents, identical boilerplate,
  crossed moves, tied similarity scores and Unicode/case/whitespace near matches.
- Native-stable-ID collision, malformed extension values and a stable ID that points
  to a block of a different kind.
- Same source version with different parser representations; reverse scope order;
  reconciliation of a scope with itself; two prior scopes racing for one target.
- Derivation inputs containing the same digest twice, dependency order changes,
  absent objects, producer output drift, failed/stale producers and a self/cross cycle.
- CAS publication succeeds but catalog commit crashes; cancellation immediately
  before commit; disk-full/locked database; retry after each case.
- Shared DAG descendants, multiple changed leaves, superseded plus stale nodes,
  repeated invalidation and partial reactivation where only some dependencies return.
- A→B→A with identical A bytes, with a newly parsed but equivalent A representation,
  and with ambiguous A blocks that must not inherit the historic lineage.

## Requirements

### Functional Requirements

- **FR-001**: F010 MUST reconcile only two complete `READY` F002 block aggregates for
  the same logical document and distinct representation scopes; input blocks and
  canonical CAS objects MUST be physically and semantically verified before planning.
- **FR-002**: Matching MUST be deterministic, one-to-one and phase ordered: unique
  native stable identity when present; unique exact canonical content in a compatible
  structural neighborhood; exact asset/table identity; unique mutual
  structural/text similarity; then bounded sequence alignment of remaining siblings.
- **FR-003**: Every phase MUST reject type mismatch, conflicting prior assignments,
  ties, insufficient confidence or insufficient best-candidate margin; ambiguity MUST
  create a new lineage rather than guess.
- **FR-004**: Matching work MUST be bounded by documented block-count, hierarchy-depth,
  text-length, sibling-window and similarity-comparison caps with fail-closed behavior.
- **FR-005**: Every accepted cross-version match MUST persist one valid F002
  `same_logical_block_as` relation with exact endpoints, confidence, algorithm version
  and generation provenance; the canonical relation object MUST be retained in CAS.
- **FR-006**: Every block in every reconciled scope MUST have exactly one deterministic
  lineage membership; a lineage may contain at most one block from a representation
  scope and may never cross logical documents.
- **FR-007**: A lineage identity MUST be a documented domain-separated RFC 8785/SHA-256
  identity rooted at its first exact block reference. A binding digest MUST similarly
  identify the lineage plus exact canonical content hash.
- **FR-008**: A match MAY be marked reusable only when lineage continuity is accepted
  and canonical content hashes are exactly equal. Similarity, native identity or
  structural proximity MUST NOT override a changed digest.
- **FR-009**: One reconciliation commit MUST atomically publish the reconciliation
  run, target memberships, relations, lifecycle invalidation/reactivation and events;
  readers MUST observe either the complete prior state or complete new state.
- **FR-010**: A repeated identical reconciliation MUST converge without duplicate
  rows or events. A conflicting plan for an already reconciled target MUST fail closed.
- **FR-011**: Reconciliation cancellation/fault before catalog commit MUST expose no
  partial catalog facts; already published immutable CAS objects may remain
  unreachable and MUST be documented as F013 recovery candidates.
- **FR-012**: F010 MUST define an internal derivation node whose lifecycle states are
  exactly `CURRENT`, `STALE`, `FAILED` and `SUPERSEDED`, distinct from the frozen F002
  generation-record state enum.
- **FR-013**: Every successful node MUST bind an exact valid F002 derivation recipe,
  ordered unique input digests, generator name/version/profile, optional model,
  configuration hash, optional prompt hash, canonical record object and exact output
  object/hash. Failed nodes MUST expose no output object and only a bounded failure code.
- **FR-014**: Direct dependencies MUST declare whether the input is an evidence
  binding, immutable object or another derivation output; producer dependencies MUST
  name the producer artifact and match its verified output hash exactly.
- **FR-015**: Derivation and slot identifiers MUST use documented, domain-separated
  RFC 8785/SHA-256 algorithms with golden vectors. No existing identity projection may
  change.
- **FR-016**: Publication MUST verify all CAS objects and dependency availability,
  reject cycles, insert the node/ordered edges/event and update its slot in one
  transaction. A concurrent identical publisher MUST converge; divergent output for
  one recipe identity MUST conflict.
- **FR-017**: A new valid artifact in an occupied slot MUST atomically mark the former
  occupant `SUPERSEDED`; supersession MUST NOT be used as a synonym for dependency
  invalidation.
- **FR-018**: When active evidence bindings change, invalidation MUST compute the exact
  transitive closure of current dependants and move only that closure to `STALE` with
  deterministic append-only events.
- **FR-019**: Revalidation MUST move a stale node to `CURRENT` only when every evidence
  binding is active at current heads, every object input verifies, every producer is
  current with the exact recorded output hash, and its slot is not occupied by another
  artifact. Revalidation MUST iterate deterministically to a fixed point.
- **FR-020**: Failed and superseded nodes MUST never be automatically reactivated.
- **FR-021**: An A→B→A sequence MUST be able to reactivate and return the exact prior
  immutable recipe/record/output objects when all identities match; no object may be
  rewritten merely to update lifecycle state.
- **FR-022**: Checksummed workspace migration 7 MUST be additive, transactional and
  downgrade-honest; revision-6 facts and prior public contracts remain unchanged and
  older binaries fail as too-new unless the operator restores a backup.
- **FR-023**: Relation records, derivation record/output objects and any future F010
  canonical run object referenced by the catalog MUST be included in reachability
  roots; missing or length-drifted objects MUST be reported as integrity failures.
- **FR-024**: All SQL MUST be parameterized, foreign keys/restrict semantics enforced,
  writes fenced by SQLite transactions and timestamps UTC/RFC 3339.
- **FR-025**: Operational logs/errors MUST contain only identifiers or digests, bounded
  counts, stable codes and timings — never block text, prompts, model output, source
  paths, provider payloads or tracebacks at the public boundary.
- **FR-026**: The implementation MUST add no runtime dependency, network access,
  provider/model call, watcher, background queue, visual extraction, MCP mutation,
  retention/deletion or export behavior.
- **FR-027**: The existing eleven public schemas, identity vectors, F006 conformance
  corpus, F009 MCP descriptors and every F001–F009 behavior MUST remain byte-for-byte
  and semantically unchanged.
- **FR-028**: Synthetic offline tests MUST cover the labelled edit corpus, zero false
  reuse, deterministic repeated processes, limits, ambiguity, DAG branching/cycles,
  exact invalidation, supersession, A→B→A, cancellation, crash/fault injection,
  concurrency, migration and reachability on Linux, macOS and Windows.
- **FR-029**: Public docs MUST distinguish logical continuity from reuse eligibility,
  internal lifecycle from public generation records, current-head eligibility from
  historical validity, and complete-object residue from catalog-visible publication.
- **FR-030**: New persisted identity algorithms and the revision-7 compatibility
  contract MUST be accepted in an ADR before implementation.

### Non-Goals and Compatibility Impact

- **Non-goal**: No automatic file watching, scheduling or job orchestration (F012).
- **Non-goal**: No rich evidence-projection lineage inference, visual evidence (F011),
  parser optimization, semantic/embedding provider or model execution.
- **Non-goal**: No deletion, garbage collection, quarantine, backup/restore automation
  or migration between storage backends (F013).
- **Non-goal**: No change to the F002 `DerivationRecord 0.1.0` schema/state enum, the
  F006 evidence family, the F008 context contracts or F009 MCP interface.
- **Non-goal**: No promise that a high similarity score proves semantic identity; low
  confidence and ambiguity always produce new evidence.
- **Compatibility impact**: Additive workspace revision 7, internal domain/port/service
  records, one accepted ADR and runtime/catalog behavior. Application and workspace
  versions advance independently; public persisted schema versions remain unchanged.

### Key Entities

- **Reconciliation Block**: Verified block facts required by the pure matcher,
  including exact scope/reference, kind, parent/order, canonical hash, bounded text,
  optional asset/native identity and structural neighborhood.
- **Block Lineage**: Version-independent document-scoped identity rooted at the first
  exact block reference; it is evidence of conservative continuity, not semantic
  equivalence across arbitrary providers.
- **Evidence Binding**: Exact `(lineage_id, canonical_hash)` digest used as a safe
  derivation leaf input.
- **Reconciliation Run**: Immutable plan identity for one prior/target scope pair and
  algorithm version, with complete counts and deterministic outcome fingerprint.
- **Derivation Node**: Workspace lifecycle projection around one immutable F002
  generation record and optional verified output.
- **Derivation Dependency**: Ordered exact input digest plus kind and optional producer
  artifact identity.
- **Derivation Slot**: Stable logical output-purpose identity with at most one current
  occupant.
- **Lifecycle Event**: Append-only body-free evidence for publish, stale, reactivate,
  fail or supersede transitions.

## Success Criteria

- **SC-001**: The labelled synthetic edit corpus contains at least 100 expected reuse
  decisions spanning every match phase and ambiguity class, with **zero false reuse**;
  precision of reusable decisions is 1.000 and any false reuse fails the gate.
- **SC-002**: Reconciliation plans, lineage/binding/run identities and relation objects
  are byte-identical across 20 fresh processes, permuted candidate construction and
  Linux/macOS/Windows CI.
- **SC-003**: Every ambiguous/tied corpus case creates a new lineage and no reuse edge;
  every exact surviving unique binding is reused, yielding reported recall separately
  from the zero-tolerance safety gate.
- **SC-004**: Fault/cancellation injection at every CAS/catalog boundary exposes no
  partial reconciliation, node, edge, slot or event rows; retry converges.
- **SC-005**: A branching synthetic DAG invalidates exactly the expected transitive
  set in one transaction and changes zero unrelated nodes over 100 randomized valid
  DAG cases.
- **SC-006**: Cycle/self-edge, unavailable dependency, producer-output drift and
  divergent same-recipe publication are rejected in 100% of negative fixtures.
- **SC-007**: A→B→A reactivates the original artifact/record/output object identities
  without generation or CAS rewrite in every supported edit-corpus case.
- **SC-008**: Revision-6→7 upgrade succeeds for fresh and populated fixtures; injected
  migration failure leaves revision 6 byte/fact equivalent; concurrent initialization
  converges to one valid checksummed revision 7.
- **SC-009**: Schema/identity/conformance freeze tests prove zero drift in all public
  schemas, existing vectors, F006 fixtures and F009 descriptor fixtures.
- **SC-010**: Ruff, format, strict mypy, all offline tests with branch coverage, build,
  repository validation and Linux/macOS/Windows CI pass with no dependency/lock drift.

## Assumptions

- F010 is invoked after both representations are already committed and verified; it
  does not change ingestion atomicity or advance document heads.
- The caller chooses the prior and target scopes explicitly. F012 may later automate
  that choice, but F010 validates same-document/distinct-scope facts and conflict rules.
- Existing text blocks have no trustworthy native stable identifier by default; the
  matching phase reads only the bounded explicit F002 `SourceLocator.native_id` value
  when a parser provides one and otherwise falls through safely.
- A historical artifact may remain intrinsically valid for its pinned old evidence
  while being `STALE` for current-head use. F010 lifecycle never deletes that evidence.
- CAS publication preceding catalog commit follows accepted ADR 0002. Complete
  unreachable residue is expected and not a partial logical publication.
