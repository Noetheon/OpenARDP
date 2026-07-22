# Changelog

All notable OpenARDP changes are documented here. The format follows Keep a Changelog principles, and releases use
semantic versioning once the public package lifecycle begins.

## Unreleased

### Added

- GitHub Spec Kit 0.13.3 integration for Codex with the reviewed OpenARDP Constitution.
- Python 3.12/uv repository baseline with a committed lock, strict local gates and commit-time checks.
- Least-privilege Linux/macOS/Windows CI contract with immutable third-party Action revisions.
- Offline repository validator for local Markdown evidence and governance consistency.
- Apache-2.0 license, contribution process, security policy and feature-local implementation evidence.
- Private `Noetheon/OpenARDP` GitHub remote with a successful first Ubuntu/macOS/Windows workflow run.
- Strict Pydantic v2 contracts for Document Manifest, Content Block, Derivation Record, Relation and Context Bundle.
- Five deterministic JSON Schema Draft 2020-12 contracts, five synthetic record fixtures and reviewed compatibility and
  invariant-layer documentation.
- RFC 8785 canonical JSON, strict raw-JSON inspection and domain-separated SHA-256 identities with independent golden
  vectors and fresh-process determinism coverage.
- Accepted ADR 0006 governing canonicalization, identity projections and migration requirements.
- Immutable SHA-256 filesystem CAS with streamed writes/reads, atomic publication, strict path validation, integrity
  inventory and concurrent duplicate convergence.
- Checksummed SQLite catalog revisions for stable logical documents, atomic source-version facts and durable fenced jobs,
  using rollback journaling and explicit restart recovery.
- Provider-neutral persistence ports and services for UUIDv7 registration, CAS-first version commits and deterministic
  read-only reachability classification.
- Synthetic offline integration/security coverage for publication faults, SQLite migration rollback, independent-reader
  visibility, lease fencing, process restart, unsafe filesystem layouts and byte-for-byte non-mutating analysis.
- Accepted ADR 0002 governing the MVP filesystem-CAS and SQLite durability boundary.

### Changed

- Moved the extracted Blueprint from its accidental nested folder to the repository root without altering its content.
- Limited feature 001 to package metadata and architecture namespaces.
- Pinned uv 0.11.31 and enabled its bounded centralized-project-environment preview after both 0.11.16 and 0.11.31 local
  `.venv` directories reproduced a macOS file-provider hidden-`.pth` failure.
- Added constrained Pydantic 2.12 and rfc8785 0.1 runtime dependencies behind the pure domain boundary.
- Replaced the provisional three-schema drafts with generated, byte-stable contracts for all five F002 roots.
- Fixed repository text contracts to LF and made canonicalization fixture decoding explicitly UTF-8 so byte-level
  verification has the same meaning on Linux, macOS and Windows.
- Selected SQLite `DELETE` journaling with `synchronous=EXTRA` for the observed affected SQLite runtime instead of WAL,
  and made migration history/table drift a fail-closed compatibility error.

### Removed

- Premature chunking and CLI scaffold behavior that belongs to later bounded features.
- Placeholder runtime dependencies and extras for Docling, MCP, watchers and other later work packages.

### Security

- Unit tests block socket access.
- CI uses read-only permissions, non-persistent checkout credentials and full-SHA Action pins.
- Private-phase vulnerability reporting avoids public exploit details and requires GitHub private vulnerability reporting
  to be enabled before a public release.
- Document-originated content is fixed to the `data` role with instruction execution disabled; validation errors redact
  raw inputs, and unit/contract suites remain network-blocked.
- Object access validates canonical identities and every managed ancestor before opening; source locators remain bound SQL
  values, raw lease capabilities are hashed before persistence and ordinary errors/logs exclude untrusted metadata.

## Blueprint history

Pre-implementation package revision details remain in [REVISION_NOTES.md](REVISION_NOTES.md).
