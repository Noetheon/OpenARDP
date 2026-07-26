# Contract: Experimental Evidence Family 0.1.0

## Public roots

| Record | Schema | Version field | Stability |
|---|---|---|---|
| Native Representation | `schemas/native-representation.schema.json` | `contract_version` | `experimental` |
| Evidence Reference | `schemas/evidence-reference.schema.json` | `contract_version` | `experimental` |
| Evidence Projection | `schemas/evidence-projection.schema.json` | `contract_version` | `experimental` |
| Trust Classification | `schemas/trust-classification.schema.json` | `contract_version` | `experimental` |

All schemas use JSON Schema Draft 2020-12. Schema identifiers are identifiers only and
must not be resolved during validation.

## Compatibility

- Readers accept exactly installed release `0.1.0`.
- Malformed semantic versions, well-formed but uninstalled versions, and unsupported
  major families are distinct failures.
- Direct fields are closed.
- Unknown data is preserved only under URI-namespaced `extensions`.
- Contract, application, workspace, provider-profile, and export-profile versions evolve
  independently.
- The family is experimental. A breaking change requires changelog, replacement fixtures,
  and explicit migration or rebuild guidance. Identity or compatibility changes require
  an ADR.
- Candidate or stable status additionally requires external-use evidence, an independent
  implementation/consumer, conformance evidence, and practiced migration.

## Canonical identity envelope

Every contract identity uses RFC 8785 over:

```json
{
  "canonicalization": "RFC8785",
  "domain": "openardp:<purpose>",
  "identity_version": 1,
  "payload": {}
}
```

The public conformance vectors define the exact version-1 allowlists. Timestamps, trust,
byte-length observations, and extensions are excluded. A declared ID mismatch is an
error; validators do not repair records.

## Anchor semantics

- `text_span`: half-open Unicode code-point offsets in the profile-defined text view.
- `page_region`: one-based page and integer normalized parts-per-million with top-left
  origin.
- `table_cell`: zero-based cell and span scoped to one opaque native table pointer.
- `provider_pointer`: uninterpreted provider-profile pointer.

All anchors are bound by their enclosing `EvidenceReference` to exact
`source_version_id` and `native_representation_id` values. Provider pointers are data,
not access authority.

## Semantic enforcement

| Invariant | Schema | Record model | Aggregate validator |
|---|---:|---:|---:|
| Closed fields, required fields, discriminator | yes | yes | no |
| Hash, semver, timestamp, media type, scalar bounds | yes | yes | no |
| Text/page/table geometry | partial | yes | no |
| Opaque pointer bounded/no-control syntax | partial | yes | no |
| Declared canonical identity | no | yes | no |
| Projection/reference internal source match | no | yes | no |
| Trust anti-escalation | partial | yes | no |
| Reference belongs to native record | no | no | yes |
| Caller-pinned expected source version | no | no | yes |
| Duplicate-ID semantic collision | no | no | yes |

Schema acceptance alone is not semantic conformance. Independent implementations must
reproduce the documented record and aggregate checks.

## Standards mapping

The detailed guide in `docs/15_EVIDENCE_CONTRACT_STANDARDS_MAPPING.md` maps contract
concepts to W3C PROV and Web Annotation. It is optional guidance:

- no JSON-LD context is a required field;
- no remote vocabulary lookup occurs;
- mapping loss and profile-specific choices are explicit;
- OpenARDP does not claim W3C conformance in F006.

## Prohibited leakage

The four roots must not contain Docling classes, Python runtime types, SQLite rows,
filesystem paths, ranking scores, model prompts, executable locators, or complete
provider-native subtrees.

## Migration from Feature 005

No migration is required. The five existing F002/F005 schemas and identity vectors remain
unchanged. F006 adds a separately versioned experimental family. F007 may produce these
records but may not alter their public shape opportunistically.
