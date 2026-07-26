# Research: Evidence Contract Foundation

## Decision 1 — Add an independent experimental contract family

**Decision**: Publish four additive roots at evidence contract `0.1.0` with stability
`experimental`. Accept only installed versions and distinguish malformed, uninstalled,
and unsupported-major versions.

**Rationale**: Contract, application, workspace, provider-profile, and export versions
have different compatibility triggers. Reusing the application or F002 schema switch
would couple unrelated release axes.

**Alternatives considered**:

- Extend the five F002 roots in place: rejected because it would change already reviewed
  schema bytes and blur compatibility ownership.
- Accept all `0.x` releases optimistically: rejected because strict readers could
  misinterpret new fields or invariants.

## Decision 2 — Use four public roots, not one universal envelope

**Decision**: Generate separate schemas for `NativeRepresentation`,
`EvidenceReference`, `EvidenceProjection`, and `TrustClassification`. Shared nested
types remain definitions, not additional public roots.

**Rationale**: Each record has an independent lifecycle and validation use. A universal
union would force consumers to dispatch before validation and encourage an expanding
platform IR.

**Alternatives considered**:

- One `EvidenceRecord` union: rejected as a needless cross-lifecycle abstraction.
- Schema fragments only: rejected because independent consumers need complete validation
  entry points.

## Decision 3 — Preserve native bytes and project content-addressed handles

**Decision**: `NativeRepresentation` points to the complete immutable provider artifact.
`EvidenceProjection` points to one immutable retrieval artifact and a source-bound
evidence reference; it does not embed a provider tree or arbitrary structured subtree.

**Rationale**: This satisfies ADR 0008 and permits exact retrieval without constructing a
second complete provider-neutral representation.

**Alternatives considered**:

- Copy the complete native tree into a neutral schema: rejected by the constitution.
- Store local paths: rejected because paths are deployment-specific and can become
  unintended access capabilities.
- Embed unrestricted provider JSON in the projection: rejected because it defeats the
  thin boundary; provider detail belongs in the native artifact.

## Decision 4 — Use four explicit anchor variants

**Decision**: Define a discriminator-based union of text span, normalized page region,
table cell, and opaque provider pointer. Table cells carry an opaque table pointer plus
zero-based cell coordinates.

**Rationale**: These are the smallest classes needed for text and rich-document evidence.
The opaque variant preserves provider fidelity without claiming equivalence.

**Alternatives considered**:

- One free-form locator dictionary: rejected as untestable and likely to leak provider
  classes.
- W3C selectors as mandatory wire fields: rejected because multiple selectors need
  profile decisions and JSON-LD is not required for local validation.

## Decision 5 — Use fixed-point normalized page geometry

**Decision**: Encode page coordinates as integer parts-per-million with top-left origin
and right/down axes. Rectangles require positive width/height and sums not exceeding
`1_000_000`.

**Rationale**: Fixed-point integers are portable, exactly canonicalizable, bounded within
the I-JSON safe range, and avoid binary floating-point boundary disagreement.

**Alternatives considered**:

- Binary64 fractions in `[0, 1]`: rejected because `x + width` boundary behavior may vary
  in independent implementations.
- Physical units: rejected because page transforms and provider unit choices exceed F006.

## Decision 6 — Make provider pointers opaque but structurally safe

**Decision**: A pointer declares provider profile name, independent semantic profile
version, pointer-format identifier, and a bounded string with no control characters.
Validators never dereference it.

**Rationale**: Opaqueness preserves provider-specific semantics; profile scoping and
bounded syntax distinguish malformed records without pretending the core understands the
pointer.

**Alternatives considered**:

- Require JSON Pointer: rejected because provider artifacts are not necessarily JSON.
- Accept arbitrary JSON values: rejected because canonical identity and consumer support
  become unnecessarily broad.
- Accept paths/URLs directly: rejected because a data locator could be confused with
  access authority.

## Decision 7 — Model trust origin and effective zone together

**Decision**: The F006 root records `origin_zone` and `effective_zone`, forces role
`data` and instruction execution false, and permits only equal trust, conservative
downgrades, or `model_derived` classification. Model-derived evidence cannot be promoted
out of that zone.

**Rationale**: A single zone cannot prove that a consumer did not silently promote
external evidence. Carrying origin and effective state makes the anti-escalation
invariant locally testable.

**Alternatives considered**:

- Reuse the existing nested one-zone F002 type unchanged: rejected because trust
  escalation would require undocumented external context.
- Define a numeric trust score: rejected because trust zones are policy categories, not a
  meaningful continuous rank.

## Decision 8 — Reuse the existing JCS façade with new domains

**Decision**: Add purpose-specific identity helpers under the accepted RFC 8785 envelope.
Each helper hashes an explicit allowlist and excludes timestamps, trust, and extensions.
Declared IDs are recomputed during model validation.

**Rationale**: ADR 0006 already governs canonicalization and domain separation. Reusing
the narrow façade avoids duplicate security-critical serialization.

**Alternatives considered**:

- Hash complete model dumps: rejected because extensions and non-identity metadata would
  destabilize identifiers.
- Add a second canonicalization dependency: rejected as redundant and risky.

## Decision 9 — Use URI-namespaced extensions and closed direct fields

**Decision**: Direct fields are forbidden unless declared. Extension keys must be
absolute URI-style namespace identifiers; values must remain within the accepted
JCS/I-JSON subset and are preserved verbatim.

**Rationale**: Namespace ownership reduces collision risk while retaining experimental
evolution without weakening strict roots.

**Alternatives considered**:

- Free-form extension keys: rejected because collisions are likely across providers.
- Accept unknown direct fields: rejected because installed-version behavior becomes
  ambiguous.

## Decision 10 — Publish a path-confined adapter-independent validator

**Decision**: A standalone command reads one explicit conformance manifest, rejects
absolute/traversing fixture paths, invokes only domain/raw-JSON validation, checks
expected valid/invalid categories and golden vectors, and performs no network or pointer
resolution.

**Rationale**: Independent implementers need executable evidence that does not depend on
Docling, SQLite, the object store, or service composition.

**Alternatives considered**:

- Tests only: rejected because a public conformance corpus needs a stable direct entry
  point.
- jsonschema-only validation: rejected because recomputed IDs and cross-record source
  binding are semantic invariants.

## Decision 11 — Map to W3C concepts as optional guidance

**Decision**: Document how native artifacts and projections relate to PROV entities and
activities and how anchors relate to Web Annotation selectors/targets. Label profile
gaps explicitly; do not add remote contexts or mandatory vocabulary fields.

**Rationale**: Reuse before reinvention does not require forcing every useful local
record into an external vocabulary before independent implementation evidence exists.

**Alternatives considered**:

- Ignore prior art: rejected by the constitution.
- Claim W3C conformance in F006: rejected because no formal profile or external
  conformance evidence exists.

## Decision 12 — Preserve the Feature 005 contract baseline

**Decision**: Capture the five existing schema bytes and canonicalization vectors as a
no-diff acceptance boundary. New roots are appended to schema generation with per-root
contract metadata.

**Rationale**: F006 is additive. Any alteration to existing compatibility or identity
semantics would require a separate migration decision and, where applicable, an ADR.

**Alternatives considered**:

- Opportunistically rename old version fields or schema IDs: rejected as unrelated,
  breaking churn.
