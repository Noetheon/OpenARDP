# OpenARDP interchange schemas

This directory contains the reviewed JSON Schema Draft 2020-12 contracts for OpenARDP release `0.1.0`. The Pydantic models under `src/openardp/domain/` are the executable authoring source; these committed schemas are the provider-neutral interchange source that other implementations can consume without importing Python.

## Public roots and traceability

| Record | Python model | Schema | Golden fixture | Version field |
|---|---|---|---|---|
| Document Manifest | `DocumentManifest` | `manifest.schema.json` | `tests/fixtures/domain/manifest.json` | `spec_version` |
| Content Block | `ContentBlock` | `block.schema.json` | `tests/fixtures/domain/block.json` | `schema_version` |
| Derivation Record | `DerivationRecord` | `derivation.schema.json` | `tests/fixtures/domain/derivation.json` | `schema_version` |
| Relation | `Relation` | `relation.schema.json` | `tests/fixtures/domain/relation.json` | `schema_version` |
| Context Bundle | `ContextBundle` | `context-bundle.schema.json` | `tests/fixtures/domain/context-bundle.json` | `schema_version` |

Each row is exercised by a positive schema/model round-trip, unknown-field rejection, all three version-failure categories and the record-specific negative tests under `tests/domain/` and `tests/contract/`.

## Compatibility policy

- Readers accept exactly the explicitly installed schema release `0.1.0`; they do not guess compatibility from a shared minor number.
- A malformed semantic version, a well-formed but uninstalled version and an unsupported major family produce distinct model errors.
- Core objects are closed. Future experimental data is allowed only under the JSON-valued `extensions` member.
- Adding a direct optional field requires a new reviewed schema release. A new reader may consume older installed records, but an old strict reader need not accept a schema it does not have.
- Schema versions, algorithm versions and identity-envelope versions evolve independently.
- Removing fields, weakening invariants, changing identifier inputs or changing the compatibility guarantee requires an ADR and migration analysis.
- The non-resolving `https://openardp.example/...` values are stable identifiers for this pre-stable contract, not runtime network dependencies.

## Enforcement layers

JSON Schema deliberately expresses only portable structural constraints. Cross-field computation remains in the executable record models, and cross-record graph behavior belongs to a later aggregate or service boundary.

| Invariant | Enforcement layer |
|---|---|
| Required fields, closed objects, enum values and scalar types | Schema and model |
| Hash/UUID syntax, UTC timestamp shape and numeric bounds | Schema and model |
| At least one non-null block payload | Schema and model |
| Content trust role is data and instruction execution is always false | Schema and model |
| `version_id` equals the source SHA-256 | Record model |
| Recomputed representation, block, artifact and relation identities match | Record model |
| Derivation lifecycle is consistent with output integrity | Record model |
| Context usage does not exceed its budget | Record model |
| Every evidence scope is pinned in the same context bundle | Record model |
| Parent block exists in the same representation | Aggregate/service in a later feature |
| Required relation graph properties hold across records | Aggregate/service in F010 |

Schema acceptance alone is therefore not proof of semantic validity. Python consumers must use `openardp.domain.validate_json`; independent implementations must reproduce the record-semantic checks documented in `specs/002-domain-models-schemas/contracts/domain-contracts.md`.

## Deterministic regeneration

Normal tests and check mode never rewrite committed contracts. Generate only as an explicit review action:

```bash
uv run --locked python scripts/generate_schemas.py --write
uv run --locked python scripts/generate_schemas.py --check
```

Output is UTF-8 with LF line endings, two-space indentation, sorted object keys and one trailing newline. It contains no timestamps, host paths or network-derived values. The full tests validate each schema with `Draft202012Validator.check_schema` and compare every committed file byte-for-byte with a fresh in-memory build.
