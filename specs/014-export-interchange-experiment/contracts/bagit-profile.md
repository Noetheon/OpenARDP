# Experimental OpenARDP BagIt Profile 0.1.0

## Status and non-claim

This is an experimental OpenARDP application profile of BagIt 1.0. It is not a new
universal archive format, does not define `.ardp`, and does not claim that general
BagIt or RO-Crate consumers understand OpenARDP semantics.

## ZIP transport

- suffix: `.zip` by convention, never required for trust;
- entries: regular `ZIP_STORED` files only;
- order: ascending UTF-8 bytes of canonical NFC POSIX paths;
- timestamp: `1980-01-01 00:00:00` for every member;
- no directory entries, encryption, data descriptor, comment, extra field or link/type
  metadata;
- creator system/permissions are fixed by the profile writer;
- every path must pass the portable path grammar before any member bytes are read.

## Required tree

```text
bagit.txt
bag-info.txt
manifest-sha256.txt
openardp-package.json
tagmanifest-sha256.txt
data/objects/sha256/<2 lowercase hex>/<62 lowercase hex>  # zero or more
```

No other path is allowed. `fetch.txt`, nested archives and remote JSON-LD contexts are
forbidden.

## Required tag bytes

`bagit.txt` is exactly:

```text
BagIt-Version: 1.0
Tag-File-Character-Encoding: UTF-8
```

with LF endings and a final LF.

`bag-info.txt` contains exactly these LF-terminated fields in this order:

```text
BagIt-Profile-Identifier: https://openardp.org/profiles/bagit/0.1.0
OpenARDP-Export-Profile: 0.1.0
OpenARDP-Package-Id: <sha256 identity>
Payload-Oxum: <payload bytes>.<payload file count>
```

The identifier is inert metadata and MUST NOT be fetched.

## Manifests

Each line is `<64 lowercase hex><two ASCII spaces><canonical path><LF>`. Entries are
strictly sorted by path and unique. `manifest-sha256.txt` lists every and only payload
file. `tagmanifest-sha256.txt` lists `bagit.txt`, `bag-info.txt`,
`manifest-sha256.txt` and `openardp-package.json`; it does not list itself.

The OpenARDP record independently lists each included asset's expected object ID,
length and exact payload path. Both representations must agree.

## Canonical semantic record

`openardp-package.json` is exact RFC 8785 canonical JSON for the public schema
`openardp-interchange-package.schema.json` release `0.1.0`. Package ID is recomputed
from the canonical record with `package_id` omitted. The exact record is identity
bearing; ZIP bytes are separately reported by archive SHA-256.

## Extension policy

- `reject`: every extensions object must be empty;
- `preserve`: bounded JSON-only extension values are retained exactly at the semantic
  JSON level and participate in package identity.

Extensions cannot override core fields or change trust, identity, permission,
disposition, version negotiation or execution/network policy.

## Import publication

A conforming reader validates structure, versions, limits, canonical metadata,
manifests, all member hashes/lengths and record relationships without extraction. Only
then may it copy allowlisted members to fresh sibling staging, reverify and atomically
publish a disjoint immutable snapshot. It never merges into a live workspace.

## Trust

Successful validation establishes integrity relative to the package's own inventory.
It does not establish authenticity, truth, ownership, permission, license validity,
safety or execution authority. All content remains untrusted data.
