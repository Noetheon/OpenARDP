# Research: Domain Models and Interchange Schemas

## Decision 1 — Use Pydantic 2.12 as the model and schema engine

**Decision**: Add `pydantic>=2.12.5,<2.13` as a runtime dependency. Use strict, frozen models with forbidden extra fields, validated defaults, non-finite-number rejection and input redaction in validation errors. Constrain the minor series and let `uv.lock` pin the exact distribution and matching `pydantic-core` version.

**Rationale**: The project mandates Pydantic v2. Strict validation avoids information-losing coercion, and the constrained minor protects committed schema snapshots from unrelated generator drift. Pydantic's JSON validation path can still parse UUID and datetime strings required by interchange JSON.

**Alternatives considered**:

- Dataclasses plus manual validation: rejected because it duplicates the mandated validation and schema stack.
- Unbounded Pydantic `<3`: rejected because schema-generation output can change between minor releases.
- Pinning `pydantic-core` separately: rejected because Pydantic already enforces its compatible core build.

## Decision 2 — Use RFC 8785/JCS for canonical JSON

**Decision**: Add `rfc8785>=0.1.4,<0.2` and expose it only through `openardp.domain.identity`. Identify the contract as `RFC8785` and prove behavior with RFC vectors. The low-level function accepts JSON values only and rejects silent conversion of UUID, datetime, Decimal, bytes, sets, models and non-string keys.

**Rationale**: RFC 8785 defines whitespace, escaping, UTF-16 property ordering, IEEE-754 number rendering and UTF-8 output across languages. Python's sorted-key JSON differs for numbers, negative zero and some Unicode keys; a home-grown float serializer would become a permanent correctness and maintenance risk. The selected library is pure Python, Apache-2.0 licensed and has no transitive dependencies.

**Alternatives considered**:

- `json.dumps(sort_keys=True, separators=(",", ":"))`: rejected as Python-deterministic but not JCS/interoperable.
- A custom OpenARDP subset: rejected because `structured`, `extensions` and geometry legitimately contain JSON numbers.
- Canonical CBOR: rejected because it would add a second interchange format contrary to the JSON/JSONL design.
- Vendoring a custom JCS implementation: rejected because number serialization is subtle and an audited, isolated dependency is smaller risk.

## Decision 3 — Constrain values to the interoperable JCS/I-JSON domain

**Decision**: Reject non-finite floats, lone surrogates, cyclic containers, non-string mapping keys and integers outside `[-9007199254740991, 9007199254740991]` at the canonicalization boundary. Preserve Unicode code points exactly and preserve array order. JCS-equivalent numeric forms such as `1`/`1.0` and `-0`/`0` may canonicalize identically.

**Rationale**: JCS builds on I-JSON and IEEE-754 binary64. Values outside this domain are not reliably portable. Exact large numbers from source documents must remain strings until a later structured-value contract defines their semantics.

**Alternatives considered**:

- Coerce Decimal or large integers to float: rejected because it loses source truth.
- Normalize Unicode: rejected because it changes evidence and violates JCS.
- Sort arrays: rejected because array order is semantic.

## Decision 4 — Strictly inspect raw JSON before model validation

**Decision**: Provide a shared `from_json` validation path that first rejects duplicate object keys, non-standard numeric constants and out-of-range integers, then uses Pydantic's strict JSON-mode validator. Direct Python construction remains strict and requires typed UUID/datetime objects.

**Rationale**: Common JSON decoders silently keep the last duplicate key and may accept NaN/Infinity. Different parsers could therefore validate or hash different meanings for the same input text.

**Alternatives considered**:

- Call `model_validate_json` only: rejected because duplicate-key handling is not an explicit public guarantee.
- Decode to a dict and call strict `model_validate`: rejected because JSON UUID and datetime strings would be incorrectly rejected as Python values.

## Decision 5 — Support one explicit schema release

**Decision**: Retain the existing Manifest field name `spec_version`; use `schema_version` on Block, Derivation, Relation and Context Bundle. Every current root contract requires exactly `0.1.0`. Model errors distinguish malformed semantic versions, unsupported major families and well-formed but uninstalled releases. Algorithm versions remain independent.

**Rationale**: Changing Manifest's published field name would create unnecessary drift. Accepting arbitrary `0.1.x` payloads without their installed schemas would defeat strict validation. Experimental forward-compatible data belongs under JSON-valued `extensions`; future optional core fields require the corresponding reader schema.

**Alternatives considered**:

- Accept every `0.1.x` by pattern: rejected because an old strict reader cannot understand a new direct field.
- Rename `spec_version` now: rejected to preserve the existing Manifest contract name.
- Allow unknown direct properties: rejected because typos and security-sensitive fields would be silently ignored.

## Decision 6 — Generate reviewed schemas deterministically

**Decision**: Treat Pydantic models as the executable authoring source and committed schemas as the reviewed interchange source. A side-effect-free `build_schemas()` function adds `$schema`, stable existing `$id` values and OpenARDP version metadata, while a script performs explicit writes. Tests compare generated mappings and normalized bytes to all five committed files and validate them with `Draft202012Validator.check_schema`.

**Rationale**: This makes drift fail loudly without letting test execution rewrite higher-authority public artifacts. Existing non-resolving `.example` identifiers are retained for `0.1.0`; changing schema identifiers requires a future versioned contract decision.

**Alternatives considered**:

- Hand-maintain schemas independently: rejected because the first three drafts already drift from documented invariants.
- Rewrite schemas during tests: rejected because tests must not mutate reviewed contracts.
- Claim dynamic cross-field equality in JSON Schema: rejected because standard JSON Schema 2020-12 cannot express it.

## Decision 7 — Classify invariant ownership

**Decision**: Mark each invariant as one of:

1. **Schema-expressible** — types, constants, patterns, required fields, enumerations, bounds and structural alternatives; both schema and model must reject violations.
2. **Record-semantic** — equal hashes, recomputed identities, lifecycle combinations and budget comparisons; the model must reject and the schema may accept the structure.
3. **Aggregate-semantic** — references between distinct records or graph properties; document now, validate later at the aggregate/service boundary.

**Rationale**: This preserves honest standard compliance and prevents proprietary schema annotations from being mistaken for enforcement.

**Alternatives considered**:

- Require both validators to reject every semantic error: rejected as impossible with standard JSON Schema.
- Add custom validation keywords: rejected because independently implemented consumers would not enforce them consistently.

## Decision 8 — Use explicit, domain-separated identity projections

**Decision**: `version_id` remains the direct SHA-256 of original bytes. Representation, block-content, derivation and relation identities hash an RFC 8785 envelope containing `canonicalization`, `domain`, integer `identity_version` and an explicit `payload`. No public helper hashes an entire model dump.

**Rationale**: Domain separation prevents accidental cross-purpose reuse. Explicit payload builders exclude self-identifiers, timestamps, positions, trust labels, quality signals and extensions that must not silently alter stable identities.

**Alternatives considered**:

- Hash the full model: rejected as self-referential and schema-evolution-sensitive.
- Prefix opaque bytes: rejected in favor of a human-debuggable JSON envelope.
- Include timestamps or source locators: rejected because operational metadata is not semantic identity.

## Decision 9 — Pin representation-dependent evidence explicitly

**Decision**: Add `representation_id` to every block, block relation reference, bundle version scope and evidence provenance. Context scopes are `{document_id, version_id, representation_id}` records, not bare version hashes.

**Rationale**: A parser or normalization change creates a new representation without changing original bytes. Omitting the representation would allow stale or mixed evidence to look current.

**Alternatives considered**:

- Pin only `version_id`: rejected because it cannot distinguish parser/configuration revisions.
- Infer representation from ambient manifest state: rejected because bundles must be immutable and auditable independently.

## Decision 10 — Separate derivation recipe identity from output integrity

**Decision**: `artifact_id` is the deterministic recipe/cache key over ordered direct inputs, generator, optional model, configuration and optional prompt identity. `output_hash` separately verifies produced content and is required only for lifecycle states that have an output.

**Rationale**: A recipe key proves which transformation was requested, not which bytes were actually produced. Ordered inputs remain semantically relevant because transformations may assign positional roles.

**Alternatives considered**:

- Use one field for recipe and output bytes: rejected because it conflates reproducibility and integrity.
- Sort inputs as a set: rejected because ordering can change transformation meaning.

## Decision 11 — Use typed relation references and deterministic relation identity

**Decision**: Model block, artifact, document-version and external references as a discriminated union. Hash relation kind plus complete source and target references for `relation_id`; exclude confidence, generation time and provenance from semantic edge identity.

**Rationale**: Relations intentionally cross entity and version boundaries. Typed references prevent opaque IDs from losing document/version/representation context, while deterministic identity supports later deduplication.

**Alternatives considered**:

- Generic source/target strings: rejected as untestable and collision-prone across entity types.
- UUID relation IDs: rejected because equivalent independently produced structural relations should converge.
- Graph cycle validation in F002: rejected as Work Package 9 behavior.

## Decision 12 — Freeze the validated record shell without overstating deep immutability

**Decision**: Use frozen Pydantic models and tuples for ordered core collections. JSON extension/structured mappings are copied and validated snapshots but are not advertised as cryptographically immutable Python containers. Identity helpers always build fresh, explicit JSON payloads.

**Rationale**: Pydantic's documented frozen mode prevents attribute reassignment but does not recursively freeze nested dictionaries. A custom container framework would add disproportionate complexity in F002.

**Alternatives considered**:

- Claim full deep immutability: rejected as inaccurate.
- Add a third-party persistent collection library: rejected without two concrete consumers.
- Leave core sequences as lists: rejected because tuples better communicate fixed validated records.

## Primary references

- [RFC 8785 — JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html)
- [RFC 3339 — Date and Time on the Internet](https://www.rfc-editor.org/info/rfc3339/)
- [RFC 9562 — UUIDs, including UUIDv7](https://www.rfc-editor.org/info/rfc9562/)
- [JSON Schema Draft 2020-12 validation](https://json-schema.org/draft/2020-12/json-schema-validation)
- [Pydantic 2.12 models](https://pydantic.dev/docs/validation/2.12/concepts/models/)
- [Pydantic 2.12 strict mode](https://pydantic.dev/docs/validation/2.12/concepts/strict_mode/)
- [Pydantic 2.12 JSON Schema](https://pydantic.dev/docs/validation/2.12/concepts/json_schema/)
- [Trail of Bits rfc8785.py](https://github.com/trailofbits/rfc8785.py)
- [Python 3.12 JSON behavior](https://docs.python.org/3.12/library/json.html)
