# ADR 0011: Persist conservative block lineages and derivation lifecycle separately

Status: Accepted for Feature 010

Date: 2026-07-31

## Context

OpenARDP source versions and representations are immutable. The F002 `block_id` is a
source-backed handle and may change after an otherwise harmless edit because source
location participates in the text-parser handle. Conversely, identical content can
occur in unrelated or ambiguous locations. Neither block-handle equality nor content
hash equality alone is therefore a sufficient cross-version reuse decision.

The public F002 `DerivationRecord 0.1.0` identifies an immutable generation recipe and
result. Its lifecycle enum describes the generation record (`PENDING`, `READY`,
`FAILED`, `STALE`, `REVOKED`), but Feature 010 also needs mutable workspace eligibility
against current document heads, exact dependency invalidation and logical-output
supersession. Changing the public enum in place would break a frozen experimental
contract and is unnecessary for the runtime capability.

New persisted lineage, binding, reconciliation-run and derivation-slot identifiers are
identity-critical. Repository governance requires their projections and migration
semantics to be decided before implementation.

## Decision

### Conservative lineage and binding identities

Persist a document-scoped block lineage only after deterministic conservative
reconciliation. A lineage is rooted in the first exact F002 `BlockReference` assigned
to it. Its identity is RFC 8785/JCS plus SHA-256 over this versioned envelope:

```json
{
  "canonicalization": "RFC8785",
  "domain": "openardp:block-lineage",
  "identity_version": 1,
  "payload": {
    "origin": {
      "record_type": "block",
      "document_id": "<uuid>",
      "version_id": "sha256:<source>",
      "representation_id": "sha256:<representation>",
      "block_id": "<uuid>"
    }
  }
}
```

A reuse-safe evidence binding is a second identity over the lineage plus exact F002
canonical content hash:

```json
{
  "canonicalization": "RFC8785",
  "domain": "openardp:evidence-binding",
  "identity_version": 1,
  "payload": {
    "lineage_id": "sha256:<lineage>",
    "canonical_hash": "sha256:<block-content>"
  }
}
```

A logical match may inherit a lineage after a uniquely conservative native, exact,
structural/similarity or bounded sequence decision. It may inherit a reusable binding
only when the canonical content hash is also exactly equal. A tie or insufficient
margin creates a new lineage. Provider-specific opaque pointers are never interpreted
as cross-provider equivalence.

### Reconciliation run and derivation slot identities

One reconciliation-run identity uses domain `openardp:reconciliation-run`, identity
version 1, and the exact prior scope, target scope, algorithm version and configuration
hash. The deterministic result fingerprint is stored separately so a retry converges
while a conflicting computation for the same run identity fails closed.

One derivation-slot identity uses domain `openardp:derivation-slot`, identity version 1,
and an explicit bounded namespace, subject digest and purpose token. A slot is a local
runtime coordination identity, not a new public interchange contract.

All four projections receive golden vectors. Existing identity functions and vectors
remain byte-frozen.

### Separate immutable generation facts from mutable eligibility

Retain the public `DerivationRecord 0.1.0` unchanged as the immutable canonical
generation record. Feature 010 adds an internal catalog node with exactly these
eligibility states:

- `CURRENT`: all exact direct dependencies are currently eligible and this artifact
  occupies its slot;
- `STALE`: at least one dependency is no longer current or verifiable;
- `FAILED`: generation ended with no output;
- `SUPERSEDED`: another artifact now occupies the same logical slot.

A successful publication accepts a valid F002 `READY` record and maps it to `CURRENT`.
A failed publication accepts a valid F002 `FAILED` record and maps it to `FAILED`.
F010 does not alter the public schema or claim that the two enums are interchangeable.

Direct inputs record an exact digest and one kind: evidence binding, immutable CAS
object or derivation output. A derivation-output input also records its producer
artifact identity and must equal the producer's verified output hash. The ordered input
digests must equal the immutable F002 recipe exactly.

### Transaction and restart semantics

Canonical record/output/relation objects are written and reverified in CAS before one
SQLite transaction publishes their catalog references. The transaction publishes a
complete reconciliation run or derivation node, all direct edges, slot transition and
append-only lifecycle events. Duplicate identical commits converge. Divergent
same-identity commits, cycles, missing dependencies and output drift fail closed.

Canonical F002 reconciliation relations use the target representation's immutable
`ready_at` as provenance time, not a retry wall clock. Operational run/lineage times
are first-writer facts excluded from identity and convergence comparison. A replacement
publication marks every prior `CURRENT` or `STALE` node in its slot `SUPERSEDED`, so a
stale historical artifact can reactivate only when no later replacement exists.

A failure after CAS publication but before catalog commit may leave a complete
unreachable object. It never exposes a partial logical record and is a Feature 013
reachability/recovery candidate. No `PENDING` catalog node is needed for restart:
retrying the same immutable publication is idempotent.

Dependency invalidation moves the exact transitive closure of affected `CURRENT`
nodes to `STALE`. Revalidation may return a stale node to `CURRENT` only when its full
dependency closure is exact and its slot is unoccupied. This permits A→B→A to reuse
the prior immutable artifact without rewriting its canonical objects. `FAILED` and
`SUPERSEDED` nodes never reactivate automatically.

### Compatibility and migration

Workspace migration 7 is additive and checksummed. It adds reconciliation, lineage,
relation, derivation-node, dependency, slot and lifecycle-event tables with restrictive
foreign keys and deterministic indexes. It does not rewrite revision-1–6 tables,
objects or migration rows.

Before opening a production revision-6 workspace with F010 software, operators must
create a backup. Older software will reject revision 7 as too new; live in-place
downgrade is unsupported and rollback requires restoring the backup. The eleven public
schemas, F006 conformance corpus, existing identity vectors and MCP descriptors do not
change.

## Consequences

- Reuse claims become lineage- and digest-specific rather than similarity-based.
- Historical artifacts remain immutable and auditable while current-head eligibility
  can change exactly and reversibly.
- The runtime gains a small internal identity surface and one additive migration but no
  dependency, provider call, background process or public schema root.
- Rich F006/F007 projections are not automatically assigned block lineages. A later
  feature must design that boundary instead of inferring semantics from opaque provider
  pointers.
- Complete CAS residue after an interrupted publication remains until Feature 013
  supplies retention/quarantine tooling.

## Alternatives considered

- Reuse by canonical content hash alone: rejected because duplicate content and
  context-sensitive derivations can cross logical evidence boundaries.
- Reuse by similarity threshold: rejected because a score is not exact input identity
  and violates the zero-false-reuse gate.
- Keep stable `block_id` by rewriting new blocks: rejected because source-backed
  immutable records and existing identity contracts must not be altered after parsing.
- Replace F002 `DerivationRecord 0.1.0`: rejected as an unnecessary breaking contract
  change; immutable generation facts and mutable workspace eligibility have different
  responsibilities.
- Delete stale artifacts: rejected because invalidation is not retention, historical
  evidence remains useful, and safe deletion belongs to Feature 013.
- Add a persistent `PENDING` lifecycle state: rejected because F010 does not execute
  model/provider work; CAS-first plus atomic idempotent publication is restartable
  without exposing an in-progress logical node.
