# Research: Export and Interchange Experiment

## Decision 1 — BagIt is the integrity/package base

**Decision**: adopt RFC 8493 BagIt 1.0 for directory layout and fixity, with one narrow
experimental OpenARDP profile `0.1.0`. Every bag contains `bagit.txt`, `bag-info.txt`,
`manifest-sha256.txt`, `tagmanifest-sha256.txt`, `openardp-package.json` and `data/`.

RFC 8493 defines a bag as a directory with `bagit.txt`, a `data/` payload directory and
payload manifests; a valid bag requires listed files and checksums to agree. BagIt
Profiles 1.4.0 provide the standard mechanism for communities to agree additional
components and identify the profile in `bag-info.txt`.

**Rationale**: this satisfies standard layout, exhaustive payload inventory and
independent checksum verification without inventing an archive format. OpenARDP's JSON
tag file supplies the bounded domain semantics BagIt intentionally does not define.

**Sources**:

- [RFC 8493 — The BagIt File Packaging Format (V1.0)](https://www.rfc-editor.org/rfc/rfc8493)
- [BagIt Profiles Specification 1.4.0](https://bagit-profiles.github.io/bagit-profiles-specification/)

## Decision 2 — Ordinary deterministic ZIP is transport, not a new format

**Decision**: transport the bag as an ordinary `.zip`. The experimental writer emits
only `ZIP_STORED` regular files, lexicographic UTF-8 member order, fixed DOS timestamp
`1980-01-01T00:00:00`, empty comment/extra fields, stable permissions and no directory
members. Profile readers reject compression, encryption, data descriptors, links,
devices, duplicate members and undeclared entries.

**Rationale**: stored entries avoid compression-library/version drift and make expanded
size equal declared bytes. The generated package is reproducible across supported
platforms while the extracted bag remains usable by ordinary BagIt tooling.

**Rejected**: a `.ardp` suffix; platform-native archive metadata; DEFLATE in the
normative writer; extraction with `ZipFile.extract()`.

## Decision 3 — RO-Crate is complementary, not the fixity layer

**Decision**: do not make RO-Crate JSON-LD normative in profile 0.1.0. Preserve a
future additive mapping path from the closed OpenARDP record.

RO-Crate 1.2 packages JSON-LD metadata about a research object and supports attached
and detached forms. Its specification explains that an RO-Crate is not necessarily an
exhaustive inventory and can be combined with BagIt or OCFL for fixity.

**Rationale**: OpenARDP currently needs complete byte inventory and a small closed
portable projection. Requiring JSON-LD contexts would add remote-context/security and
semantic complexity before a real consumer proves the value.

**Sources**:

- [RO-Crate 1.2 introduction](https://www.researchobject.org/ro-crate/specification/1.2/introduction.html)
- [RO-Crate 1.2 structure](https://www.researchobject.org/ro-crate/specification/1.2/structure)

## Decision 4 — OCFL does not fit a one-shot snapshot

**Decision**: do not use OCFL 1.1 for this profile.

OCFL specifies an application-independent, structured storage layout for versioned
digital objects with durable inventories and fixity. Those repository/version-history
semantics exceed a finite one-shot evidence exchange and would duplicate OpenARDP's
workspace lifecycle.

**Source**: [Oxford Common File Layout 1.1](https://ocfl.io/1.1/spec/)

## Decision 5 — No custom archive

**Decision**: reject the minimal project-owned archive candidate. BagIt plus a profile
tag already supplies the missing convention. `openardp-package.json` is a versioned tag
record inside a standard bag, not a new container or universal interchange claim.

**Revisit when**: at least two independent consumers demonstrate a requirement that
cannot be represented safely by BagIt tag/payload files or an additive RO-Crate map.

## Candidate evidence matrix

| Criterion | RO-Crate 1.2 | OCFL 1.1 | BagIt 1.0 + profile | Custom archive |
|---|---|---|---|---|
| Exhaustive byte inventory | not guaranteed; combine with fixity format | yes | yes | must invent |
| Semantic metadata | rich JSON-LD | repository inventory, not evidence semantics | profile tag needed | must invent |
| One-shot exchange fit | good, but fixity gap | poor/over-scoped | strong | possible |
| Independent versioning | spec/profile | spec/layout | spec/profile | project-owned |
| Streaming implementation | feasible | complex version layout | simple manifests | project-owned |
| Offline security | remote JSON-LD contexts must be constrained | local repository | strong when `fetch.txt` forbidden | all rules custom |
| Existing tools | broad research ecosystem | preservation systems | mature libraries/tools | none initially |
| Core dependency cost | JSON-LD implementation likely | substantial | zero with narrow stdlib writer | zero initially, permanent maintenance cost |
| Selection | future additive mapping | reject | **select** | reject |

## Decision 6 — Complete closed semantic record

**Decision**: `openardp-package.json` is RFC 8785 canonical JSON and carries:

- profile and record schema versions;
- package identity algorithm and exact scope identity;
- sorted portable records with `record_type`, `contract_version`, `record_id`, trust
  classification and closed JSON facts;
- sorted assets with content ID, length, media type, role and independent disposition;
- included payload path or inert reference/closed omission reason;
- sender-asserted permission/license facts, clearly not receiver verification;
- declared extension policy (`reject` or `preserve`) and bounded JSON-only extensions.

Package identity is SHA-256 over the canonical record with `package_id` omitted. It
does not include ZIP metadata or a creation timestamp. Repeated semantic exports
therefore have one identity.

## Decision 7 — Asset inclusion is affirmative

**Decision**: every source/provider-native asset is independently `included`,
`referenced` or `omitted`. `included` requires an affirmative `redistribution_asserted`
flag; absent/unknown permission cannot include bytes. References are inert bounded
strings with secrets/credential-shaped URL components rejected. The profile never
uses BagIt `fetch.txt` and never dereferences a reference.

**Rationale**: integrity and sender assertions cannot establish legal permission.

## Decision 8 — Portable paths are a closed language

**Decision**: normalize to NFC before validation and require the supplied path already
to be NFC. Paths use `/`, contain ASCII structural names or lowercase SHA-256 payload
names, have no empty/dot segments, controls, colon, backslash, leading slash, drive/UNC
syntax, trailing dot/space or Windows-reserved segment. Case-fold and normalized forms
must be unique. Profile metadata never contains local paths or filenames.

Payload path grammar is `data/objects/sha256/<first-two>/<remaining-62>`. A single
content object has one path even when several records reference it.

## Decision 9 — Strict bounded preflight

**Decision**: validation first checks archive stat/central directory under bounds,
then member metadata/paths, then reads bounded normative metadata, then streams every
declared member and recomputes hashes/lengths, then validates record relationships.
No member is extracted during preflight.

Defaults:

| Limit | Default | Installed range |
|---|---:|---:|
| archive bytes | 2 GiB | 1 MiB–16 GiB |
| expanded bytes | 2 GiB | 1 MiB–16 GiB |
| entry count | 10,000 | 6–100,000 |
| per-entry bytes | 1 GiB | 1 KiB–8 GiB |
| normative metadata bytes | 16 MiB | 64 KiB–256 MiB |
| path UTF-8 bytes | 512 | 64–4,096 |
| path depth | 16 | 2–64 |
| relationships | 100,000 | 1–1,000,000 |

Because valid profile entries are stored, compression ratio is exactly 1; any other
compression method is policy-rejected before expansion. Nested archive media types or
magic are rejected for included assets.

## Decision 10 — Fresh immutable import snapshot

**Decision**: import publishes to an absent local directory. It first creates an
immutable plan from complete verification, then copies allowlisted bytes into a unique
sibling staging directory using no-follow regular-file checks, rehashes the copied
files, writes the verified record last, synchronizes and renames without overwrite.

An exact existing destination may converge only after it is fully reverified against
the same package ID. A foreign/conflicting destination fails. No catalog rows or CAS
objects in a live workspace are modified.

**Rationale**: this is the smallest truthful atomic publication boundary for the F014
experiment. Merging into SQLite/CAS would require a separate accepted cross-resource
transaction and conflict model and is deferred.

## Decision 11 — Closed compatibility and extensions

**Decision**: the installed reader accepts only profile `0.1.0` and record schema
`0.1.0`. Unsupported versions are distinct from malformed input. Core objects reject
unknown fields. `extensions` contains only bounded JSON and is either empty/rejected or
preserved byte-semantically according to the declared package policy; it cannot alter
identity algorithms, dispositions, permission or trust.

## Decision 12 — Integrity is not authority

**Decision**: all imported source, metadata, model outputs, references, license facts
and extensions retain their declared untrusted-data classification. Successful SHA-256
verification says only that received bytes equal the sender's inventory. CLI results
must never describe packages as authentic, true, licensed, safe to execute or trusted.

## Known limitations

- Profile 0.1.0 exchanges a finite snapshot and does not merge it into a live workspace.
- There are no signatures, authenticity proofs, encryption or legal verification.
- General BagIt bags and compressed ZIPs are not accepted by the strict profile reader.
- RO-Crate/PROV alignment is documented but not emitted.
- Cross-platform determinism is claimed only for committed synthetic vectors and CI
  environments, not all ZIP implementations or filesystems.
