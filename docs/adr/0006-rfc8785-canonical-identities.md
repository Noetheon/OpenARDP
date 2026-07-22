# ADR 0006: RFC 8785 canonical JSON and domain-separated identities

Status: Accepted

Date: 2026-07-22

## Context

OpenARDP needs independently implemented components to produce identical persistent identifiers from equivalent domain facts. Python's ordinary sorted-key JSON is deterministic only within its own serialization rules: it does not define ECMAScript number rendering or UTF-16 property ordering, and hashing an entire model would make identifiers self-referential and sensitive to unrelated schema evolution.

Source bytes, normalized representations, content blocks, derivation recipes and semantic relations also have different meanings. Reusing an unqualified digest across those purposes would make accidental cross-domain equality possible and obscure which fields are identity-significant.

## Decision

- Original source versions remain the direct lowercase SHA-256 of the authoritative source bytes: `sha256:<hex>`.
- All structured identities use RFC 8785 (JSON Canonicalization Scheme) through the narrow `openardp.domain.identity` façade.
- The accepted input domain is the interoperable JCS/I-JSON subset: unique string keys, valid Unicode, safe integers, finite binary64 numbers and acyclic JSON containers. No runtime object is silently coerced.
- Representation, block-content, derivation-artifact and relation identifiers hash a versioned RFC 8785 envelope containing `canonicalization`, a purpose-specific `domain`, integer `identity_version` and an explicit `payload`.
- Identity projections are allowlists. Timestamps, source positions, trust labels, quality metadata and extensions—including extensions on relation endpoints—are excluded unless a future ADR and migration explicitly changes a projection.
- Derivation recipe identity and produced-output integrity remain separate fields.
- Canonicalization, identity-envelope and public-schema versions evolve independently.

The complete version-1 projections and exact exclusions are normative in `specs/002-domain-models-schemas/contracts/domain-contracts.md`.

## Consequences

- Equal supported JSON values converge across insertion order, process hash seed and supported operating system; JCS-defined numeric equivalences such as `1`/`1.0` and negative/positive zero also converge.
- Unicode code points are preserved without normalization, so visually equivalent NFC/NFD text may retain different identities.
- Integers outside the cross-language safe range, non-finite floats, lone surrogates, cycles, non-string keys, `Decimal`, UUID, datetime, bytes, sets and model objects are rejected at the canonicalization boundary.
- `rfc8785>=0.1.4,<0.2` becomes a deliberately constrained runtime dependency behind an OpenARDP-owned API.
- Changing the canonicalization algorithm, envelope version, identity domain or projection requires a new ADR, compatibility analysis, new golden vectors and a migration plan before implementation.

## Alternatives rejected

- Python `json.dumps(sort_keys=True)`: not a cross-language canonical JSON contract.
- Hashing full record dumps: self-referential and unstable under unrelated optional metadata changes.
- A home-grown float serializer: too subtle to maintain as security- and persistence-critical code.
- Canonical CBOR: would introduce a second interchange format before there is a demonstrated need.
