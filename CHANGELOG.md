# Changelog

All notable OpenARDP changes are documented here. The format follows Keep a Changelog principles, and releases use
semantic versioning once the public package lifecycle begins.

## Unreleased

### Feature 019 — CI cost and latency optimization

- Replaced duplicated all-event quality execution with fail-closed change classification, draft Preflight and stable
  ready-PR quality lanes that retain the complete Linux, macOS and Windows test inventory.
- Assigned branch coverage, lint, formatting, strict typing, repository validation and package build once to Ubuntu;
  macOS and Windows retain all tests with redundant coverage instrumentation disabled.
- Moved the unchanged F015 evidence matrix and aggregate `NO-GO` gate to manual, version-tag and release-owned ready-PR
  boundaries; enabled lock-keyed, safely pruned uv artifact caching without caching environments.
- Added deterministic CI policy/audit/cost evidence and a Draft-to-Ready operating model. The dated gross model projects
  55–65 percent savings under its documented assumptions and is not an invoice guarantee.

### Feature 018 — repository hygiene and maintainability

- Decomposed the release-gate evaluator, CLI command dispatcher and watcher reconciliation
  transaction behind characterization tests while preserving public results, failure ordering
  and transactional behavior.
- Added a deterministic standard-library AST audit with strict policy parsing, explicit
  monotonic ceilings for reviewed legacy hotspots and repository-validation integration.
- Corrected focused quickstarts to opt out of the full-suite coverage threshold explicitly,
  retained the authoritative offline 85 percent branch gate and synchronized current project
  status without changing dependencies, schemas, migrations, identities or release decisions.
- Recorded measured improvements and remaining structural debt in
  [`docs/17_CODEBASE_HYGIENE.md`](docs/17_CODEBASE_HYGIENE.md); this maintenance feature makes
  no claim that the whole codebase is complexity-free or release-ready.

### Feature 017 — Microsoft Graph design spike

- Added experimental tenant/site/drive-scoped Graph synchronization contracts with stable
  item-ID digests, remote revision hints, complete permission-snapshot references and explicit
  tombstones while excluding raw provider IDs, paths, names, cursors and secrets.
- Added deterministic zero-network delta/state mocks and bounded whole-cycle orchestration for
  pagination, last-occurrence-wins reduction, 410 reset, throttling and atomic final-cursor/state
  publication, plus constant-time wakeup-only notification validation.
- Added an official-source research record, permission matrix, threat model, data-protection
  assessment and ADR. The mock architecture is `GO`; a production Microsoft Graph connector
  remains `NO-GO` pending tenant isolation, live least-privilege evidence and operational,
  privacy, release and security controls.

### Feature 016 — alternate parser conformance spike

- Added a bounded standard-library evidence consumer that runs under Python isolated/no-site
  mode without OpenARDP, Pydantic or RFC8785 imports and independently validates all seven
  valid roots, eight invalid roots, one record set and six F006 identity vectors.
- Added a deterministic non-Docling TXT/CSV producer with complete retained native JSON plus
  thin text, page-region, table-cell and opaque-pointer evidence accepted by the reference
  contracts on the reverse path.
- Added fail-closed conformance evidence and repository drift validation. The decision is
  `supported_for_scoped_claim`; arbitrary parser interchangeability, semantic anchor
  equivalence, production readiness and contract stabilization remain prohibited claims.

### Feature 015 — benchmark, security and v0.1 release gate

- Set the application candidate to `0.1.0rc1` and froze a synthetic five-baseline
  protocol, three document families, three byte budgets, exact judgments, 10,000-sample
  deterministic bootstrap policy and canonical candidate source-tree identity.
- Added strict release-evidence models/schema/storage, body-free platform observations,
  exhaustive no-waiver `GO`/`NO-GO` evaluation, generated human/claim projections and
  the `release-evidence`, `release-gate` and `release-report` CLI commands.
- Added exact security-control manifests, hostile/privacy fixtures, bounded artifact
  inspection, complete locked-component inventory, per-component license state,
  normalized CycloneDX 1.5 SBOM and three-platform aggregate CI evidence jobs.
- The committed local capture contains 4,222 raw observations and passes performance,
  exact mechanical quality, 44 security-control cases, five privacy canary classes,
  candidate artifact/offline-install and executable upgrade/rollback suites.
- The binding decision remains `NO-GO`: three-platform evidence, a complete current
  license/vulnerability review and bounded-context value are not all established. Final
  `0.1.0`, tagging and prohibited performance/security/support claims remain blocked.

### Feature 014 — export and interchange experiment

- Selected RFC 8493 BagIt 1.0 plus an experimental OpenARDP profile `0.1.0` after an
  evidence matrix covering RO-Crate 1.2, OCFL 1.1, BagIt and a custom archive; no
  `.ardp` suffix or universal-format claim was introduced.
- Added deterministic stored-ZIP export, complete offline hostile-package verification,
  fresh read-only snapshot import, explicit permitted-asset dispositions and body-free
  `package-export`, `package-verify` and `package-import` CLI operations.
- Added a strict public interchange JSON Schema plus three valid and thirty-eight invalid
  deterministic cross-platform vectors covering versions, paths, ZIP metadata,
  resources, extensions, relationships, trust and integrity.

### Feature 013 — retention, recovery and migrations

- Added SQLite revision 10 maintenance intent, complete retention roots, operator holds,
  deterministic dry-run plans, reversible quarantine/restore and explicit grace-gated
  reclamation with crash recovery.
- Added verified internal backup manifests, fresh disjoint restore, explicit paired
  revision-9 migration, exact storage diagnostics/reserve checks and transactional global
  lexical-index rebuild.
- Added body-free CLI operations and offline integration/security evidence across backup,
  restore, migration, capacity, commit and index-rebuild failure boundaries.

### Added

- Foreground `watch`, body-free `jobs` and fenced `job-cancel` CLI commands over one
  explicit disjoint local root, with deterministic bounded polling and no daemon,
  listener, cloud call or MCP mutation.
- Checksummed SQLite revision 9 with durable watch roots, observations, exact immutable
  job targets and redacted events; generic jobs now persist `available_at`, running
  cancellation requests and terminal `CANCELLED` state.
- Complete-scan stability reconciliation, one-job deterministic convergence, delayed
  capped retry, cancellation-aware lease recovery, queue backpressure, tombstones,
  fresh reappearance and unambiguous rename hints while preserving path identity.

- Experimental `VisualEvidenceDescriptor 0.1.0`, deterministic visual/page-raster
  identities and the twelfth generated JSON Schema 2020-12 root without drift in the
  eleven prior schemas or F006/F008/F009 contracts.
- Checksummed additive SQLite revision 8 for atomic reusable page rasters, visual
  descriptors, crops and complete reachability roots.
- Exact optional `visual` dependency group with `pypdfium2==5.12.1` and
  `Pillow==12.3.0`; spawned bounded offline PDF rendering, intrinsic-rotation-aware
  geometry and stripped single-frame RGB PNG crops.
- Identifier-only `visual-materialize` and `visual-evidence` CLI operations plus
  provider-free handle-only VISUAL context discovery that preserves
  `visual_evidence_required` until explicit materialization.
- Optional OCR/caption provider orchestration through the F010 derivation DAG with no
  registered default, exact crop dependencies and model-derived untrusted output.

- Conservative provider-free F010 block reconciliation with fixed phase ordering,
  bounded work, explicit ambiguity, version-independent lineages and the hard rule
  that reuse requires an exact canonical content digest.
- Checksummed additive SQLite revision 7 for reconciliation runs, complete lineage
  memberships, canonical relations, derivation slots/nodes/dependencies/events and
  restrictive foreign keys; upgrades are transactional and older readers reject the
  workspace as too new.
- Transactional derivation lifecycle (`CURRENT`, `STALE`, `FAILED`, `SUPERSEDED`) over
  unchanged F002 records, including cycle-safe CAS-first publication, exact transitive
  invalidation, slot supersession, fixed-point reactivation and A→B→A artifact reuse.
- A reviewed 130-decision synthetic corpus with 1.000 precision/recall and zero false
  reuse, plus migration, fault, concurrency, reachability and hostile-data evidence.

- Dependency-free local read-only MCP stdio server with nine fixed identifier-scoped
  tools over the existing query, search, rich-evidence and context-compilation
  services; pinned protocol revision `2025-06-18` and interface version `0.1.0`.
- Canonical MCP tool descriptors and versioned body-free error envelopes, bounded
  newline framing, serialized responses, individual bodies, pagination, scopes and
  monotonic deadlines, plus cooperative cancellation with zero partial compilation.
- `openardp mcp` composition that opens only an existing compatible workspace, accepts
  no client filesystem paths, creates no listener, invokes no parser/provider and
  preserves all earlier CLI, schema, vector and workspace contracts.
- Deterministic provider-free context compiler: exact READY corpus snapshots,
  verified lexical candidate discovery over text and rich evidence, policy-based
  trust/sensitivity/freshness classification, a documented total order and greedy
  fixed-point budget admission with ten-percent response reserve.
- Public `ContextBundle 0.2.0` with discriminated block/projection provenance inside
  delimited untrusted-data envelopes, plus the body-free experimental
  `SelectionReceipt 0.1.0` recording task digest, algorithm/estimator/policy
  identities, corpus snapshot, budget ledger and exhaustive
  selected/omitted/rejected/stale inventories.
- Checksummed catalog revision 6 with atomic immutable compilation rows, exact scope
  pinning, insert-once conflict semantics and receipt/bundle reachability roots.
- Byte-identical task-supplied replay against the recorded snapshot with closed
  task/estimator/algorithm mismatch and integrity failure taxonomy.
- Provider-free `context` and `context-receipt` CLI commands with stable JSON and
  human envelopes, explicit `--include-bundle` body access and sanitized failure
  mapping.
- Body-free structured operational logging and cancellation checkpoints across
  discovery, verification, publication and commit.
- Exact optional `docling==2.114.0` rich adapter with spawned offline conversion,
  complete native JSON retention, deterministic F006 thin evidence and reviewed local
  PDF model-bundle validation.
- Checksummed catalog revision 5 with atomic accepted rich representations, append-only
  canonical/converged/diverged attempts, complete evidence reachability and fully
  verified cache reuse.
- Provider-free rich evidence/native inspection plus `evidence` and `get-evidence` CLI
  commands in stable JSON and human-readable modes.
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

- Routed PDF/DOCX/PPTX through the optional rich adapter while preserving the existing
  text ingestion and lexical-search contracts.
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
- Placeholder runtime dependencies and extras for MCP, watchers and other later work packages.

### Security

- MCP tool parameters reject path-, traversal-, URL-, shell- and control-shaped data
  before filesystem access; body-bearing results remain explicitly untrusted, unknown
  identifiers are uniform, and errors/audit records exclude bodies, queries, tasks,
  source paths, exception strings and tracebacks.
- Rich parsing denies network before provider import, bounds source/page/process/output
  resources, streams model verification, sanitizes IPC failures and reaps child
  processes on timeout, crash, cancellation and malformed output.
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
