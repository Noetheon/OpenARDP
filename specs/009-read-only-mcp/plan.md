# Implementation Plan: Read-only MCP

**Branch**: `codex/f009-read-only-mcp` | **Date**: 2026-07-27 |
**Spec**: [spec.md](spec.md)

**Input**: Feature specification from
`/specs/009-read-only-mcp/spec.md`

## Summary

Add a least-privilege, read-only MCP server on one local stdio transport under the
pinned protocol revision `2025-06-18`. Nine object-scoped tools wrap the existing
verified services — document query, search, rich evidence and context compiler — with
no business logic in the interface layer. A stdlib newline-delimited JSON-RPC codec
owns framing, lifecycle, per-request deadlines, cancellation routing and one versioned
sanitized error taxonomy. All body-bearing output uses the F008 untrusted-content
envelope; compile results default to body-free handles. No parameter accepts a
filesystem path, no tool mutates sources or existing evidence, no network listener
exists and no dependency is added. One additive `openardp mcp` CLI verb composes the
server; all eleven public schemas, identity vectors and workspace revision 6 remain
byte-frozen.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Python standard library plus existing locked dependencies
(Pydantic v2, RFC 8785 helper); no MCP SDK, async framework or network library

**Storage**: Existing filesystem SHA-256 CAS and SQLite workspace revision 6 opened
without mutation; the only durable effect is the F008 compile path's additive
immutable derived publication and atomic commit

**Testing**: pytest with branch coverage and network/socket disabled, Ruff, strict
mypy native and `win32`, scripted stdio transcript fixtures, confused-deputy/path/
ID-enumeration/injection security cases, cancellation/deadline/corruption fault
injection and three-platform GitHub Actions

**Target Platform**: Linux, macOS and Windows on Python 3.12

**Project Type**: Local-first modular-monolith library and CLI with a stdio server
entrypoint

**Performance Goals**: Bounded by the published session limits (64 KiB inbound line,
64 pending non-cancellation frames, 1 MiB serialized response, 30 s default deadline, per-tool pagination caps); no
latency or throughput claim

**Constraints**: Read-only over registered objects; identifiers only, never paths;
verified services only; untrusted-content envelopes; stable versioned errors; clean
EOF shutdown; no startup migration or repair; at least 85% branch coverage

**Scale/Scope**: Single local user, single configured workspace, one sequential
application dispatch loop plus one bounded framing/cancellation reader, nine fixed
tools over TXT/Markdown and accepted PDF/DOCX/PPTX evidence

**Contract/Version Impact**: Additive experimental `MCP interface 0.1.0` application
contract (tool descriptors, session limits, error taxonomy `mcp_error_version: 1`)
with deterministic `tools/list` transcript fixtures. The eleven public schemas,
identity vectors, conformance corpus, workspace revision 6 and provider/export
profiles are unchanged. Application and MCP-interface versions advance independently.

**Trust/Operational Impact**: All client input is untrusted; all returned document
text is structurally delimited untrusted data. The server opens no listener, resolves
no client-supplied path, executes no document content and logs only identifiers,
digests, codes and timings. Startup fails closed on missing, incompatible, locked or
corrupted workspaces without mutation. Cancellation and deadlines reuse the F008
bounded checkpoints and never expose a partial compilation.

## Constitution Check

| Article | Design result |
|---|---|
| I — Source truth | PASS — tools return verified registered evidence only; sources are never mutated or shadowed. |
| II — Disposable accelerators | PASS — search/compile reuse the verified F005/F008 paths; drift fails closed; the only writes are additive derived objects. |
| III — Reuse/provider neutrality | PASS — stdlib codec, existing services, no SDK/cloud/model dependency, locked dependency set unchanged. |
| IV — Thin projection | PASS — outputs project existing F002/F006/F008 contracts; no new document representation. |
| V — Data not instruction | PASS — identifiers only, no path resolution, untrusted envelopes, no instruction execution, read-only MVP MCP as required. |
| VI — Determinism/atomicity | PASS — deterministic canonical responses, F008 atomic compile commit, stable pinned protocol behavior. |
| VII — Progressive context | PASS — handle-first compile results, body-minimizing navigation, bounded explicit payload opt-in. |
| VIII — Test-first quality | PASS — framing, lifecycle, boundary, security, cancellation and CLI tests precede implementation where practical. |
| IX — Measured claims | PASS — only reproducible boundary/determinism evidence claimed; limits stated as safety bounds. |
| X — Simplicity | PASS — existing monolith and services reused; one synchronous loop; no new abstraction without need. |
| XI — Feature isolation | PASS — F009 only, full lifecycle and three-platform gate; F011/F012/F013 remain excluded. |
| XII — Contract evolution | PASS — additive experimental application contract; frozen persisted contracts untouched; docs conflict corrected at origin. |

No constitution exception or ADR is required. The read-only MCP boundary implements
accepted ADR 0004 and constitution Article V.6 with an additive application surface
and no change to persisted contracts, identity algorithms or compatibility
guarantees. This check remains PASS after Phase 1 design.

## Project Structure

### Documentation

```text
specs/009-read-only-mcp/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── implementation-notes.md
├── checklists/
│   ├── requirements.md
│   └── mcp-boundary.md
├── contracts/
│   ├── mcp-read-only-tools.md
│   └── mcp-error-envelope.md
└── tasks.md
```

### Source and tests

```text
src/openardp/
└── interfaces/
    ├── cli.py                 # additive `mcp` verb and composition only
    ├── mcp_protocol.py        # pure stdlib framing/lifecycle/error codec
    └── mcp_server.py          # session loop, tool dispatch, deadline routing

tests/
├── fixtures/mcp/              # deterministic stdio transcripts and descriptor goldens
├── integration/
│   ├── test_mcp_server.py     # lifecycle, navigation, search, compile, receipt
│   └── test_cli_mcp.py        # verb composition, startup failures, CLI regression
├── security/
│   └── test_mcp_boundaries.py # confused deputy, paths, enumeration, injection
└── unit/
    └── test_mcp_protocol.py   # framing, version, batch, deadline, error mapping
```

**Structure Decision**: Extend the existing inward-pointing monolith. The MCP surface
is interface-layer only: `mcp_protocol.py` is a pure, fully unit-testable codec with
no I/O; `mcp_server.py` owns the stdio loop and dispatch; `cli.py` composes existing
services exactly as it does today. Domain, ports, adapters and services remain
untouched because the transport adds no business rule; no parallel framework is
created.

## Implementation Phases

### Phase 0 — Baseline and contract freeze

- Freeze F008 `main`, current test count and all eleven schema/vector/corpus hashes.
- Add failing byte-freeze and package-surface tests proving no dependency or
  persisted-contract change.
- Prove the locked dependency set and all existing CLI snapshots remain unchanged.

### Phase 1 — Pure protocol codec and error taxonomy

- Define the bounded newline-framing reader and pending-frame queue, single-object
  JSON-RPC validation, pinned-version lifecycle state machine and versioned error
  taxonomy as pure code.
- Define tool descriptors, session limits and deterministic `tools/list` projection.

### Phase 2 — User Story 1: safe session and navigation tools

- Implement the session loop, initialize handshake and EOF shutdown.
- Wire `list_documents`, `get_source_status` (identifier only), `get_document_outline`,
  `get_block`, `list_evidence` and `get_evidence` through the existing services with
  envelope wrapping and per-tool caps.

### Phase 3 — User Story 2: search, compile and verified receipt

- Wire `search_document` with bounded filters and labelled snippets.
- Wire `compile_context` to the exact F008 compile-and-persist path with handle-first
  output, bounded `include_bundle` opt-in, deadline and concurrent cancellation
  observation without concurrent application dispatch.
- Wire `get_context_receipt` to full verification before return.

### Phase 4 — User Story 3: boundary defense and failure safety

- Enforce identifier-only parameters, uniform not-found, sanitized error mapping,
  body-free logging and the complete hostile-input matrix.
- Inject cancellation, deadline, CAS/catalog corruption and prove zero partial
  compilations and zero leakage.

### Phase 5 — User Story 4: CLI launch, compatibility and convergence

- Add the `openardp mcp` verb and startup fail-closed behavior; preserve every
  existing CLI envelope.
- Run quickstart transcripts, determinism repeats, byte-diff proof and all gates.
- Update `docs/05` and operational documentation, changelog, validation evidence and
  run final Spec Kit analysis and convergence.

## Complexity Tracking

No constitution violation requires justification.
