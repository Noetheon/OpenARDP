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

## Stabilization gate

No public contract becomes stable through internal declaration or elapsed time. Stabilization requires external-use
evidence, an independent implementation or consumer, conformance fixtures, compatibility evidence and practiced migration
behavior.

## Deprecation

Document introduction, replacement, warning period, removal release and migration command. Never silently reinterpret an existing field.
