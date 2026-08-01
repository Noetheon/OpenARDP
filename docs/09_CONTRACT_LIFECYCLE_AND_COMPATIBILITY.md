# Contract lifecycle and compatibility

**Status:** Active lifecycle policy for experimental and future contracts.

## Version dimensions

Keep independent versions for application release, workspace/catalog schema, public JSON contracts, provider profiles and export formats. Never infer one from another.

## Evolution rules

- `internal`: may change without migration guarantees.
- `experimental`: breaking changes allowed only with changelog, fixtures and an explicit migration path or documented reset/rebuild path.
- `candidate`: additive changes preferred; removals require deprecation across at least two minor releases.
- `stable`: semantic-versioning compatibility, conformance fixtures and supported migration are mandatory.

Readers must reject unsupported major versions and preserve unknown extension data only where the contract explicitly allows it. Writers must not emit fields from a newer contract under an older version identifier.

## Workspace and schema compatibility

Every catalog migration is transactional, checksummed, restart-safe and backed by upgrade/downgrade or backup/restore evidence. Opening a newer unsupported workspace must fail without mutation. Rebuildable indexes are migrated separately from authoritative facts.

As of F014 these axes are deliberately independent: application `0.0.1`, workspace
revision 10, `VisualEvidenceDescriptor 0.1.0`, unchanged F006/F008/F009 contracts and
experimental export profile/public interchange record `0.1.0`. F012 watcher/job and
F013 maintenance records remain internal. F014 adds no workspace migration and never
infers its reader version from application, workspace, provider or MCP versions.
Exact renderer, parser and watcher profile versions are identity inputs,
not application or workspace versions. A breaking visual identity or schema change
requires a new contract version, fixtures, migration/reset guidance, changelog and ADR;
it must not be emitted under `0.1.0`.

Revision 9 is a forward-only in-place upgrade because SQLite job-state CHECK
constraints are rebuilt atomically. It copies every revision-8 job/event/reference
fact, sets old jobs' `available_at` to their creation time and installs watcher tables
in the same checksummed transaction. Older software rejects revision 9. Feature 013
provides the first explicit paired backup/migration path for the revision-9 to
revision-10 transition; older historical transitions remain forward-only.

## Experimental interchange profile 0.1.0

The installed F014 reader accepts exactly profile/schema `0.1.0`; an unsupported
version is distinct from malformed structure. Core fields are closed. JSON-only
extensions are accepted only under the declared `preserve` policy and participate in
semantic package identity; `reject` requires empty extension containers. A breaking
change needs a new profile/schema version, ADR, changelog, golden vectors and explicit
snapshot reset/migration guidance. General BagIt conformance and live-workspace import
compatibility are not claimed.

## Stabilization gate

No public contract becomes stable through internal declaration or elapsed time. Stabilization requires external-use
evidence, an independent implementation or consumer, conformance fixtures, compatibility evidence and practiced migration
behavior.

## Deprecation

Document introduction, replacement, warning period, removal release and migration command. Never silently reinterpret an existing field.
# Workspace revision 10

Revision 10 is additive and forward-only. Normal `open` and repeated `init` validate an
already-current workspace and never migrate an older one. Revision 9 upgrades require
the explicit `workspace-migrate` entrypoint and a successfully published, verified
pre-upgrade backup whose manifest identity is recorded in the same migration transaction.
Rollback means restoring that revision-9 backup to a fresh location; in-place downgrade
is unsupported. Public JSON schemas remain unchanged by Feature 013.
