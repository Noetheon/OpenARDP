# Research: Read-only MCP

## Decision 1 — Stdio transport only, pinned protocol revision

**Decision**: Implement exactly one stdio transport using newline-delimited UTF-8
JSON-RPC 2.0 messages under the pinned MCP protocol revision `2025-06-18`. Streamable
HTTP, sockets and every other transport are excluded.

**Rationale**: The MVP is local-first and single-user (constitution Articles III, V).
A network listener would create an attack surface, an authentication obligation and a
conflict with the no-egress default without enabling any required local behavior. One
pinned revision makes lifecycle behavior deterministic and testable offline.

**Alternatives considered**:

- Streamable HTTP alongside stdio: rejected because it contradicts the local
  single-user boundary and would require an ADR plus a security model expansion.
- Header-framed (LSP-style) stdio: rejected because the pinned MCP revision specifies
  newline-delimited framing; supporting both doubles the framing attack surface.
- Accepting a range of protocol revisions: rejected because negotiated downgrade
  semantics are unneeded for one local server and weaken deterministic errors.

## Decision 2 — Stdlib codec, no MCP SDK dependency

**Decision**: Implement the narrow framing, lifecycle and dispatch codec with the
Python standard library inside the interface layer. No `mcp` SDK, async framework or
network library is added; the locked dependency set is unchanged.

**Rationale**: The delivered surface is nine synchronous read-only tools over
existing synchronous services. An SDK would add a supply-chain, license, maintenance
and lockfile obligation (constitution Article XI), pull in an async runtime and still
require the same boundary tests. A small stdlib codec is fully deterministic, offline
testable and replaceable because it sits behind the interface layer, not inside
domain or services.

**Alternatives considered**:

- Official `mcp` Python SDK as an optional extra: rejected for the MVP because the
  dependency and async obligations outweigh reuse value for nine synchronous tools;
  the interface-layer isolation keeps a later SDK adoption possible without touching
  services.
- A generic internal RPC framework: rejected by Article X (no abstraction without two
  implementations); the codec is deliberately specific to the pinned MCP revision.

## Decision 3 — Tools wrap existing services; the interface owns no logic

**Decision**: Each of the nine tools maps one-to-one onto an existing verified service
call: `DocumentQueryService` (list, status, outline, get block), `SearchService`
(search), `RichEvidenceService` (list/get rich evidence) and
`ContextCompilerService` (compile, verified receipt load). The MCP layer validates
and bounds input, projects output and maps errors; it contains no selection,
verification or persistence logic.

**Rationale**: F008 explicitly built the CLI as the stable application boundary that
F009 wraps (FR-024 there). Duplicating logic in the transport would create a parallel
framework and invalidate the determinism and verification evidence already delivered.

**Alternatives considered**:

- A separate MCP-specific query service: rejected as a parallel framework with no
  behavioral difference.
- Exposing catalog/object-store ports directly: rejected; ports are internal
  provider-neutral seams, not a machine-facing contract.

## Decision 4 — Identifiers only, never paths

**Decision**: No tool parameter accepts a filesystem path. `get_source_status` accepts
a document UUID only, even though the CLI `status` verb also accepts a path target.
All other object addressing uses document, block, projection or receipt identifiers.

**Rationale**: Path acceptance is the primary confused-deputy channel: a client (or a
document-influenced prompt) could steer the server toward arbitrary local files. The
CLI path form is a local-ergonomics convenience resolved inside the owner's shell;
the machine-facing boundary gets the strictly safer identifier-only form. Identifier
lookups already fail closed through existing catalog exceptions.

**Alternatives considered**:

- Accepting paths resolved against configured roots: rejected because even
  canonicalized path reach expands authority beyond registered objects and conflicts
  with the feature prompt's "no arbitrary paths".
- Accepting source locators as opaque strings: rejected because the locator is a
  filesystem path by construction in the local connector.

## Decision 5 — Compile persists derived artifacts; read-only means sources untouched

**Decision**: `compile_context` calls the exact F008 compile-and-persist path. Its
durable effect — additive immutable CAS objects plus one atomic catalog commit — is
the only write any tool may cause. No tool mutates sources, heads, existing evidence,
indexes, catalog history or configuration, and no implicit migration or repair runs
at startup.

**Rationale**: Receipts must remain auditable after the call (Article VII), and the
F008 persistence path is already atomic, idempotent and fully verified. Derived data
is disposable and reproducible (Article II), so additive derived publication does not
violate a read-only evidence boundary. Forbidding it would force an unauditable
ephemeral compile or a second compile path.

**Alternatives considered**:

- Ephemeral compile without persistence: rejected because receipt verification and
  replay would be impossible and a divergent compile path would be required.
- Opening the SQLite catalog in `mode=ro`: rejected because it would break the
  sanctioned compile commit; least privilege is enforced structurally by composing
  only query, search, evidence and compiler services and never constructing
  ingestion or reindex surfaces.

## Decision 6 — Handle-first responses with one response cap

**Decision**: Every tool returns bounded structural data. `compile_context` defaults
to receipt/bundle handles, decision counts, accounting and notices; an explicit
`include_bundle` opt-in embeds the bundle only while the complete serialized response
stays within the response byte cap, otherwise failing with a stable limit category.
Body-bearing fields always use the F008 untrusted-content envelope.

**Rationale**: Large evidence dumped into a protocol response invites truncation,
unbounded memory use and injection ambiguity. Handles plus envelope-delimited bodies
preserve progressive disclosure (Article VII) and the data-is-not-instruction
boundary (Article V).

**Alternatives considered**:

- Always embedding the bundle: rejected because bundle size (up to the compiler cap)
  can exceed safe response bounds.
- Streaming partial responses: rejected because the pinned request/response lifecycle
  has no streaming semantic in this feature and partial JSON invites parser
  confusion.

## Decision 7 — Versioned sanitized error taxonomy over the CLI classification

**Decision**: One experimental taxonomy (`mcp_error_version: 1`) maps every failure to
a stable machine code inside the JSON-RPC error object: `invalid_request`,
`unsupported_protocol_version`, `unknown_tool`, `invalid_params`, `not_found`,
`conflict`, `integrity_or_workspace`, `cancelled`, `deadline_exceeded`, `internal`.
Messages are fixed body-free strings; the taxonomy reuses the CLI's exit
classification semantics so identical failures read identically on both interfaces.

**Rationale**: Clients need stable programmatic outcomes; operators need no document
content in diagnostics (Article V, F008 FR-022). Uniform `not_found` removes the
identifier-enumeration oracle beyond the documented envelope.

**Alternatives considered**:

- Per-tool bespoke error shapes: rejected as unstable and unauditable.
- Echoing validation detail (offending field/value): rejected because the value may
  be attacker-controlled content or a path; the stable code plus parameter name is
  the documented maximum disclosure.

## Decision 8 — Deadlines and cancellation ride the F008 checkpoints

**Decision**: Each request runs under a wall-clock deadline (default 30 s, range
1–120 s) checked before dispatch and threaded into `compile_context` through the
existing `CancellationCheck` port. The deadline never claims to interrupt a blocked
stdin read between requests. One stdlib reader thread continues bounded framing while
application dispatch remains sequential, so `notifications/cancelled` can flip the
same thread-safe active-request flag during compilation. Cancellation and deadline
overrun prevent catalog commit and return stable categories; no request worker pool,
subprocess or preemptive kill is introduced. The pending non-cancellation queue is
capped at 64; overflow cancels active work and closes the session fail-closed.

**Rationale**: The compiler already checks cancellation at bounded phases and fails
closed without partial publication (F008 US3). Reusing that port keeps semantics
identical across CLI and MCP. Separating input observation from application dispatch
is the smallest mechanism that makes a real mid-flight cancellation notification
observable without introducing concurrent service execution.

**Alternatives considered**:

- A worker thread per request with hard preemption: rejected because Python cannot
  safely preempt and a thread pool adds nondeterministic concurrent service execution.
- A fully synchronous read/dispatch loop: rejected after final runtime analysis proved
  it cannot observe a cancellation notification during compilation.
- No deadline: rejected because one unbounded compile could block the single stdio
  loop indefinitely.

## Decision 9 — No new persisted contract root

**Decision**: F009 adds the experimental `MCP interface 0.1.0` application contract —
published tool descriptors, session limits and the error taxonomy — as reviewed
feature documentation and deterministic `tools/list` fixtures. It adds no JSON Schema
root under `schemas/` and no workspace migration; the eleven public schemas and all
identity vectors remain byte-frozen.

**Rationale**: The public persisted contracts (blocks, bundles, receipts, evidence)
already exist and are frozen. The MCP surface is an application/interface version
that evolves independently (Article XII); materializing it as another persisted root
would imply storage and migration semantics that do not exist.

**Alternatives considered**:

- Publishing tool descriptors as a twelfth schema: rejected because nothing persists
  or exchanges them as standalone documents; the deterministic `tools/list`
  transcript fixtures provide equivalent conformance evidence.
- Versioning the error taxonomy inside an existing schema's extensions: rejected
  because it would mutate a frozen contract.

## Conflict resolution — `docs/05` planning sketch versus delivered set

The planning document lists `get_visual_evidence` among MVP tools and a
`--transport stdio|streamable-http` option. Both predate the F008/F011 split and the
pinned-transport decision. Per the constitution's source-of-truth precedence, this
spec (the active feature artifact) governs: the visual tool is F011 scope, HTTP
transport is out of scope, and `docs/05` is corrected at F009 convergence rather than
silently implemented as written.

## Limits and known limitations

| Limit | Default | Accepted range |
|---|---:|---:|
| inbound line bytes | 64 KiB | fixed |
| pending non-cancellation frames | 64 | fixed |
| protocol revision | `2025-06-18` | pinned |
| request deadline | 30 s | 1–120 s |
| serialized response bytes | 1 MiB | 64 KiB–4 MiB |
| `list_documents` results | 256 | 1–1,024 |
| `get_document_outline` items | 1,000 | 1–4,000 |
| `search_document` limit | 20 | 1–100 |
| `list_evidence` projections | 256 | 1–1,024 |
| one returned body | 256 KiB | 1 KiB–1 MiB |
| `compile_context` scopes | 8 | 1–32 (compiler cap) |
| tool count | 9 | fixed |

These are safety and reproducibility bounds, not throughput claims. Cooperative
cancellation means a deadline is honored at the next bounded checkpoint, not at
arbitrary instruction granularity. The server is one synchronous stdio loop: a slow
but in-bounds request delays later requests, which is acceptable for one local user
and is documented rather than hidden.
