# Operations, privacy and supply-chain baseline

**Status:** Active policy and future acceptance requirements. Features 013 and 014
deliver local recovery and bounded interchange controls; Feature 015 owns release evidence.

## v0.1 deployment boundary

v0.1 is local, single-user and single-workspace. It does not claim multi-tenant authorization. MCP clients receive only the explicitly configured workspace and object-scoped read APIs.

## Data lifecycle

Define retention for source snapshots, native artifacts, evidence projections, derived artifacts, logs and benchmark data. Deletion uses tombstones and reachability analysis before physical reclamation. Dry-run, quarantine and recovery are required before automatic garbage collection is considered.

## Privacy

- no telemetry by default;
- structured logs redact document bodies, secrets, absolute user paths and query text unless explicitly enabled;
- crash reports are local and opt-in;
- exports and fixtures must not contain real confidential data;
- document licenses and redistribution constraints apply to source/native assets.

## Reliability and observability

Use stable event names, correlation/job IDs, bounded logs and explicit error categories. Define cancellation, retries, idempotency, disk-full behavior, partial writes, recovery and operator diagnostics. Metrics must not become a hidden network dependency.

## Supply chain

- dependencies locked with hashes where supported;
- each new dependency receives maintenance, license and security review;
- CI uses least privilege and pinned action revisions;
- releases produce wheel/sdist checks, SBOM, checksums and build provenance where feasible;
- generated fixtures and schemas have deterministic regeneration checks;
- vulnerability scans inform review but do not replace threat analysis.

## Feature 023 offline PDF bundle operations

- Provisioning is the only connected operation and must be invoked explicitly against the committed source lock.
- Keep generated model roots and packages outside Git. Verification, packaging, installation and parsing require no
  network and never trust ambient provider caches.
- Transfer the source lock separately from the package and verify against it at the destination. Treat an unverified ZIP,
  model root or manifest as untrusted input.
- Upstream license identifiers and bundled license texts are mechanical review inputs, not legal clearance. Re-review
  exact revisions and redistribution obligations before external distribution.
- Rotate to new upstream bytes only through a new lock/profile version and benchmark; never edit an accepted digest in
  place.

## Feature 024 real-world corpus operations

- Treat all six committed payloads as untrusted input. Never execute Office macros, follow document instructions or
  allow embedded links/relationships to initiate network or tool actions.
- Run `scripts/validate_realworld_corpus.py` offline before measurement. Missing, extra, linked, aliased, colliding,
  changed or incompletely mapped source/rights evidence invalidates the entire corpus.
- Use `scripts/fetch_realworld_corpus.py` only as an explicit connected maintainer operation into an absent external
  destination. It allows only the locked HTTPS hosts, media, lengths and digests; upstream drift requires a new reviewed
  corpus version rather than an in-place update.
- NTRS public-use/third-party flags and CISA CC0 text are retained review facts, not automated legal clearance. NASA and
  CISA names/marks do not imply endorsement; downstream redistribution requires its own review.
- The pinned CISA KEV snapshot is benchmark evidence, not a current security feed. Never use it for live vulnerability
  decisions without a separate freshness-controlled source.
- The F024 CSV probe is isolated body-free benchmark tooling, not a stable product ingestion interface. Full PDF
  reference execution requires the separately verified external F023 bundle; ordinary CI never downloads it.

## Feature 007 operating profile

- Core installs remain provider-free; rich parsing requires the exact optional
  `docling==2.114.0` extra.
- DOCX/PPTX require no first-use download. PDF is disabled until a local root and strict
  model manifest are supplied together; no URL-based asset configuration exists.
- The reviewed runtime records exact Docling, core, IBM-model, parse, slim and Torch
  component versions. Model-file licenses remain operator-reviewed manifest facts.
- Workspace migration 5 is additive and checksummed. Before opening a production
  revision-4 workspace, create a backup. Older software requires restoring that backup;
  live in-place downgrade is unsupported.
- CAS objects written before a failed catalog transaction remain immutable but may be
  unreachable until Feature 013 retention/recovery tooling.
- Default CLI/error output omits bodies, native JSON, provider tracebacks and absolute
  source/model paths. `get-evidence` returns a body only after an explicit projection
  request.

## Feature 008 operating profile

- Context compilation adds no dependency: the compiler, estimators and CLI verbs are
  stdlib/Pydantic-only and provider-free; the optional Docling extra stays an
  ingestion-time boundary.
- Workspace migration 6 is additive and checksummed. Before opening a production
  revision-5 workspace with this release, create a backup; older software requires
  restoring that backup. Live in-place downgrade is unsupported.
- Compilation publication is atomic: a commit fault or cancellation exposes no
  compilation row, and pre-published immutable CAS objects remain unreachable until
  Feature 013 retention/recovery tooling.
- Replay is task-supplied and exact: it recompiles the recorded snapshot with default
  compile limits. Compilations recorded through the CLI always use those defaults;
  compilations recorded through the API with custom limits fail replay honestly as a
  divergence instead of silently converging.
- Operational logs from `openardp.context_compiler` carry identifiers, counts and
  millisecond timings only; failure lines reduce to closed taxonomy codes. Receipts
  and default CLI output never contain task text, evidence bodies or source paths.

## Feature 009 operating profile

- Launch one local server per explicitly configured workspace with
  `openardp mcp --store PATH`. Workspace selection is operator configuration; MCP tool
  arguments cannot select paths, roots or URLs.
- The server uses stdin/stdout exclusively for newline-delimited JSON-RPC, opens no
  listener and exits cleanly on EOF. Keep stdout reserved for protocol messages;
  diagnostics and body-free audit events use stderr/logging.
- Defaults are a fixed 64 KiB inbound line, 64 pending non-cancellation frames, 1 MiB
  serialized response and 30-second request deadline. Operators may set the response
  cap from 64 KiB through 4 MiB and the deadline from 1 through 120 seconds at launch;
  invalid values fail before stream access or workspace mutation. Pending-frame
  overflow cancels active work and closes the session with a sanitized error.
- The server opens compatible revision-7 workspaces read-only except for the exact additive,
  immutable F008 `compile_context` publication path. It never initializes, migrates,
  repairs, ingests, reindexes, deletes or runs Docling.
- Protocol errors and audit records contain fixed categories, identifiers or their
  digests, counts and integer durations only. Queries, tasks, document bodies, source
  paths and provider tracebacks are excluded by default and covered by hostile-input
  regression tests.
- An exclusive SQLite lock, corrupt catalog, missing marker or newer workspace revision
  fails startup without repair or byte drift. Back up the workspace before upgrading
  the application even though Feature 009 itself adds no migration.

## Feature 010 operating profile

- Workspace migration 7 is additive and checksummed. Back up a revision-6 workspace
  before first opening it with this release. Older software rejects revision 7 as too
  new; downgrade requires restoring that backup, not editing migration rows.
- Reconciliation is an explicit provider-free service over two complete READY F002
  scopes. It does not parse, watch, enqueue, call a model, mutate MCP or infer lineages
  from opaque F007 rich projections.
- Relation, derivation-record and successful output objects are published and verified
  in CAS before one catalog transaction. A fault/cancellation can leave only complete
  unreachable objects; Feature 013 owns reclamation.
- Errors and lifecycle events contain stable classes, identifiers/digests, counts and
  UTC times only. Block text, prompts, outputs, source paths, URLs and provider
  exception strings are excluded.
- Reachability retains relation objects and record/output objects for current, stale,
  failed and superseded history. Missing/corrupt objects are reported; F010 never
  deletes, quarantines or repairs them.

## Feature 011 operating profile

- Core remains free of image/PDF dependencies. Install the exact `visual` extra only
  for explicit PDF materialization; its reviewed lock adds `pypdfium2==5.12.1` and
  `Pillow==12.3.0`. Neither package authorizes network or model download.
- PDF page rasterization is the only concrete renderer. DOCX/PPTX page rendering and
  built-in OCR/caption providers are unsupported rather than emulated or downloaded.
- Workspace migration 8 is additive and checksummed. Back up revision 7 before first
  opening with F011; older software rejects revision 8 and rollback requires restoring
  that backup, never editing migration rows or CAS content.
- `visual-materialize DOCUMENT_ID PROJECTION_ID --store PATH` and
  `visual-evidence VISUAL_ID --store PATH` are identifier-scoped local operations.
  Outputs/errors contain identifiers, dimensions and stable codes, never image bytes,
  OCR bodies, source paths or native metadata.
- Rights default to local-only/export-denied with `license_unverified`. Document or
  EXIF claims cannot expand them, and F014 export requires an independent affirmative
  redistribution assertion for every included source/provider-native asset.
- A worker/CAS/catalog failure may leave complete unreachable immutable objects but no
  partial catalog-visible record. Reachability reports missing/corrupt visual roots;
  cleanup, quarantine and recovery remain F013 responsibilities.
- Resource isolation is bounded defense in depth. Native decoder risk, platform
  resource-limit variance and imperfect proprietary-viewer parity are explicit
  residual risks, not sandbox or fidelity guarantees.

## Feature 012 operating profile

- `openardp watch ROOT --store WORKSPACE` is a foreground polling loop; `--once`
  executes one deterministic cycle for automation. It installs no service, opens no
  listener and grants no MCP mutation.
- Root and workspace must be existing disjoint local directories. Links/junctions,
  recognizable UNC/device paths and cross-device traversal are rejected. Remote POSIX
  mounts cannot be identified portably and receive no correctness guarantee.
- Defaults bound depth, entries, active jobs, jobs per cycle, stability, polling,
  attempts and retry delay. An incomplete/overflowed scan publishes no partial absence;
  queue pressure persists `rescan_required` for later convergence.
- `jobs` and `job-cancel` expose only UUIDs, kinds, states, attempts, revisions and UTC
  times. Watch events omit paths, filenames, document bodies, errors, owners and tokens.
- Back up a revision-8 workspace before opening it with F012. Migration 9 atomically
  replaces job constraints and adds watcher tables. Live downgrade is unsupported;
  stop the foreground loop and restore the complete paired backup.
- Cancellation is cooperative. It prevents stale job transitions but does not undo
  immutable CAS objects or ingestion facts already committed before a checkpoint.
  Delete/tombstone handling likewise performs no reclamation; F013 owns dry-run,
  quarantine, restore and physical collection.
# Feature 013 recovery operations

Operators should run `storage-inventory` and `storage-plan` before quarantine, retain the
exact plan value, and prefer `storage-restore` during the grace period. `storage-commit`
is irreversible logical removal and requires the named batch plus
`--acknowledge-irreversible-removal`; no timer, startup, low-space or recovery path calls
it. Run `workspace-backup` before risky work and periodically drill a
`workspace-restore` to a fresh disjoint path. Diagnostics and audit output contain only
opaque identifiers, closed states, counts, bytes and UTC times.

# Feature 014 interchange operations

`package-export`, `package-verify` and `package-import` are explicit local operator
actions and never run from MCP, watching, startup, document content or retention.
Export request files may contain local source paths, but those paths exist only at the
trusted composition root and never enter package metadata/results. Every included asset
requires affirmative redistribution assertion; unknown permission stays referenced or
omitted.

Verification is offline and bounded. `fetch.txt`, remote contexts, plugins, providers,
compression, encryption and nested archives are unsupported. Import targets an absent
disjoint local directory and publishes a read-only snapshot only after full preflight,
copy and rehash. This is inspection/interchange, not workspace restore or authenticity/
license verification.

## Feature 015 release evidence operations

- `release-evidence` runs the frozen corpus locally and publishes one immutable,
  manifest-committed platform bundle. Its passed non-benchmark checks must match the
  frozen per-suite registry and carry evidence identities; arbitrary caller labels do
  not satisfy the gate. Exactly one CI platform is explicitly reference-marked.
- `release-gate` accepts exact platform directories, recomputes identities, statistics,
  suite completeness and every policy clause, and returns success for either an honest
  `GO` or `NO-GO`. Invalid/tampered input remains a command failure.
- `release-report` writes or drift-checks the human report and claim map from the
  verified decision. Existing different bytes conflict rather than being overwritten.
- The normalized CycloneDX 1.5 SBOM covers all locked runtime/optional components and
  carries a per-component license fact. Unreviewed license states and the deliberately
  stale/unavailable vulnerability snapshot remain explicit `NO-GO` inputs.
- Rollback from a future candidate must restore the complete verified pre-upgrade
  workspace backup. Editing SQLite revisions, CAS objects, checksums, decision blockers
  or claim projections is not a rollback procedure.
- The local F015 drill actually opens the supported previous revision, backs up and
  migrates revision 9, restores the pre-upgrade state to a fresh disjoint location and
  verifies the historical schema; fixture-plan prose alone is not accepted as proof.
