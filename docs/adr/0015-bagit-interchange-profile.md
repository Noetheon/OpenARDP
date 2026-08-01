# ADR 0015: Reuse BagIt for experimental snapshot interchange

Status: Accepted for Feature 014

Date: 2026-08-01

## Context

OpenARDP needs a finite, offline way to exchange selected portable evidence, provenance,
trust and permitted exact bytes. It does not need a universal document format, a second
workspace backup, long-term repository versioning or linked-data complexity without a
consumer. The constitution requires evaluating maintained prior art before defining a
project-owned container.

The same decision criteria were applied to RO-Crate 1.2, OCFL 1.1, BagIt 1.0 and a
minimal custom archive: exhaustive integrity, semantic metadata, independent versions,
asset permission/reference policy, extension behavior, streaming, deterministic output,
hostile-input safety, implementation/supply-chain cost and independent-tool use.

## Decision

### Adopt BagIt 1.0 with one narrow profile

RFC 8493 BagIt supplies the standard bag directory, payload directory and checksum
manifests. BagIt Profiles 1.4.0 supplies the convention for declaring additional
community constraints. OpenARDP therefore adopts an experimental BagIt profile `0.1.0`
and adds one closed canonical `openardp-package.json` tag. This is a profile, not a new
container or universal standard.

The transport is an ordinary `.zip`, never `.ardp`. The normative writer uses only
stored regular entries, fixed timestamps/permissions, sorted portable paths and no
comments, extra fields, encryption, links or data descriptors. `fetch.txt` is forbidden;
references are inert data and no verification/import path performs network access.

The profile carries independently versioned source/native/evidence/derivation/trust
records, separate include/reference/omit asset dispositions, affirmative redistribution
assertions, SHA-256 identities and complete BagIt payload/tag integrity. RFC 8785
canonical JSON gives the semantic package identity independently of the ZIP digest.

### Keep RO-Crate additive and reject OCFL/custom scope

RO-Crate 1.2 is a useful future semantic mapping, but its structure guidance notes that
a crate is not necessarily an exhaustive fixity inventory and may be combined with
BagIt or OCFL. Normative JSON-LD would add context and semantic processing complexity
without a demonstrated F014 consumer.

OCFL 1.1 provides durable versioned digital-object repository structure. Those storage
and version-history semantics exceed a one-shot exchange snapshot and overlap the local
workspace lifecycle.

A minimal custom archive is rejected because BagIt plus a profile tag already satisfies
the integrity/packaging gap. Reconsider only after at least two independent consumers
show a need that cannot be represented safely by BagIt tags/payloads or an additive
RO-Crate mapping.

### Verify before publishing a fresh snapshot

The reader validates ZIP metadata, portable paths, exact installed versions, resource
limits, canonical metadata, manifests, every member hash/length and cross-record
relationships without extraction. It then copies only allowlisted members to sibling
staging, reverifies, makes the snapshot read-only by default and atomically publishes a
fresh disjoint directory.

F014 does not merge records or bytes into an existing workspace SQLite/CAS. That would
require a separate transaction/conflict ADR. F013 backup/restore remains the only
workspace recovery format.

## Compatibility

- Adds experimental export profile and public record schema `0.1.0`.
- Application remains `0.0.1`; workspace/catalog remains revision 10.
- Existing public schemas, provider profiles, identity algorithms and MCP descriptors
  remain byte-stable.
- The reader accepts only installed `0.1.0`; malformed and unsupported versions are
  distinct. Breaking profile changes require a new version, fixtures, changelog and
  migration/reset guidance.

## Security and trust consequences

- Included source/provider-native bytes require affirmative operator selection and
  sender-asserted redistribution permission. Missing permission defaults to reference
  or omission.
- Packages, records, license assertions and document/model text remain untrusted data.
  SHA-256 integrity does not prove authenticity, truth, ownership, permission, license,
  safety or execution authority.
- Limits cover archive/expanded/per-entry/metadata bytes, entry/relationship counts and
  path bytes/depth. Traversal, collisions, links, devices, compression, encryption,
  nested archives and undeclared entries fail before publication.
- The strict ZIP transport is intentionally narrower than general BagIt tooling; this is
  a documented experimental interoperability limit.

## Evidence

- [RFC 8493 — BagIt File Packaging Format 1.0](https://www.rfc-editor.org/rfc/rfc8493)
- [BagIt Profiles Specification 1.4.0](https://bagit-profiles.github.io/bagit-profiles-specification/)
- [RO-Crate 1.2 introduction](https://www.researchobject.org/ro-crate/specification/1.2/introduction.html)
- [RO-Crate 1.2 structure](https://www.researchobject.org/ro-crate/specification/1.2/structure)
- [OCFL 1.1](https://ocfl.io/1.1/spec/)
- `conformance/interchange/v0.1.0/manifest.json`: three valid and thirty-eight invalid
  deterministic offline package vectors.

## Alternatives considered

- RO-Crate alone: rejected for exhaustive fixity and current JSON-LD cost.
- OCFL: rejected as repository/version-history overreach.
- Custom `.ardp`/`.ardp.zip`: rejected because it duplicates BagIt and implies an
  unsupported universal-format claim.
- Compressed normative ZIP: rejected because stored entries improve deterministic
  cross-platform output and bound expansion.
- Import directly into a workspace: deferred until real interchange evidence justifies
  a separate atomic merge/conflict design.
