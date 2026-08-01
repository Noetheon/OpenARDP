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

As of F013 these axes are deliberately independent: application `0.0.1`, workspace
revision 10, `VisualEvidenceDescriptor 0.1.0`, unchanged F006/F008/F009 contracts and no
export-format version. F012 watcher/job and F013 maintenance records are internal and
add no public schema.
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
