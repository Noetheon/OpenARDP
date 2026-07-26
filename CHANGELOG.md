# Changelog

All notable OpenARDP changes are documented here. The format follows Keep a Changelog principles, and releases use
semantic versioning once the public package lifecycle begins.

## Unreleased

### Added

- Experimental evidence contract family `0.1.0`: four strict JSON Schema 2020-12 roots
  for retained native artifacts, source-bound evidence anchors, thin retrieval
  projections, and anti-escalation trust classifications.
- Text-span, fixed-point page-region, table-cell, and opaque provider-pointer anchors
  with synthetic valid/invalid conformance fixtures, canonical SHA-256 vectors, and an
  offline adapter-independent validator.
- Optional W3C PROV/Web Annotation mapping guidance that introduces no mandatory JSON-LD
  field, remote context, or conformance claim.
- Constitution 2.0.0 with implementation-first positioning, complete provider-native artifact preservation, thin
  evidence projection, verified disposable indexes, fair evidence and independent contract-version governance.
- Accepted ADRs 0007–0010 for implementation-first evolution, provider-native representations, non-authoritative indexes
  and contracts-before-adapters.
- Curated v3.1 strategy, prior-art, non-goal, contract-lifecycle, benchmark, release, operations, privacy, supply-chain,
  contract-example and conformance guidance.
- Authoritative continuation prompts and roadmap for Features 005A–017, including retention/recovery and
  alternate-parser conformance work packages.
- Lexical search over prepared evidence: checksummed catalog revision 4 with contentless-delete FTS5, STRICT mapping
  table, atomic READY+index commits, coverage fail-closed checks and explicit idempotent `reindex`.
- Bounded term/phrase query grammar, deterministic bm25 ranking with total tie-break, verified CAS snippets and
  document/version/history/kind/trust/page/slide/limit filters.
- Installable CLI verbs `search` and `reindex` using the shared workspace, envelope and exit-classification contract.
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
- Explicit version-1 local workspaces and the installable `openardp` CLI with `init`, `ingest`, `list`, `status`, `outline`
  and `get`, including stable human/JSON error classifications.
- Provider-neutral deterministic text parser contracts, strict incremental UTF-8 handling, reviewed TXT/Markdown block
  normalization and a killable spawned-worker product adapter with portable limits and socket denial.
- Safe regular-file local snapshots that reject unsafe path components and special files, detect read races, preserve
  original bytes/size/mtime/mode and feed parsers only from the verified CAS object.
- Checksummed SQLite revision 3 for fenced document representations, complete block projections, current document heads
  and append-only ingestion evidence.
- Parse-once ingestion and progressive query services with canonical F002 manifest/block objects, deterministic UUIDv8
  block handles, full cache verification, A → B → A correctness and body-minimizing navigation.
- Synthetic offline F004 coverage for parser isolation, source races, representation rollback boundaries, concurrent
  cache hits, corruption, source removal and all six CLI commands.

### Changed

- Reconciled entry points with the completed Feature 005 search behavior and classified future capabilities explicitly.
- Replaced the planned complete OpenARDP rich-document IR with immutable provider-native artifacts plus thin
  provider-neutral evidence projections.
- Deferred the proposed custom `.ardp.zip` decision to an evidence-based Feature 014 export/interchange experiment.
- Propagated Constitution 2.0.0 into Spec Kit templates, `AGENTS.md`, architecture, security and operating guidance.
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
- Hardened CAS publication after a macOS CI race: POSIX now publishes with a no-clobber hard link plus staging unlink
  and Windows with no-clobber `os.rename`, so duplicate writers converge through verified reuse instead of
  `os.replace`; racing readers classify the transient internal second link with a re-check before judging it unsafe.

### Removed

- Superseded pre-v3.1 future feature prompts that conflicted with the adopted 005A–017 dependency order.
- Premature chunking and CLI scaffold behavior that belongs to later bounded features.
- Placeholder runtime dependencies and extras for Docling, MCP, watchers and other later work packages.

### Security

- Evidence contract roots reject stale source/native scope, malformed geometry and
  pointers, trust promotion, unknown direct fields, unsafe JSON, and instruction
  authority; fixture paths are confined to the declared conformance tree.
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
