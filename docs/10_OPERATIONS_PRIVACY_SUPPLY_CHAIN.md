# Operations, privacy and supply-chain baseline

**Status:** Active policy and future acceptance requirements. Feature 013 owns retention/recovery implementation and
Feature 015 owns release evidence; this document does not claim they are already delivered.

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
