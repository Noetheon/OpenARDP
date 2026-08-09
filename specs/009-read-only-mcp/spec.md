# Feature Specification: Read-only MCP

**Feature Branch**: `codex/f009-read-only-mcp`

**Created**: 2026-07-27

**Status**: Converged — see the [authoritative feature map](../../spec-kit/FEATURE_MAP.md)

**Input**: Expose prepared evidence through object-scoped, least-privilege MCP tools over
a local stdio transport. Configured workspace only; no arbitrary paths, ingestion,
deletion or mutation. Bounded pagination and output, stable versioned errors,
cancellation and deadlines, explicit per-request limits and a local single-user
boundary. MCP is transport only. Returned text is labelled and delimited untrusted
content. Tests are offline and include confused-deputy, path and ID-enumeration cases.

## Clarifications

### Session 2026-07-27

- Q: Which transport and protocol does the server implement? → A: Exactly one local
  stdio transport using newline-delimited JSON-RPC 2.0 under the pinned MCP protocol
  revision `2025-06-18`. Streamable HTTP or any network listener is excluded because
  the MVP is local-first and single-user; a remote transport requires its own ADR.
- Q: Is a third-party MCP SDK a runtime dependency? → A: No. The narrow read-only
  surface is implemented with the Python standard library only. Adding an SDK would
  create a supply-chain and async-framework obligation without enabling any required
  behavior; the boundary stays replaceable behind the interface layer.
- Q: Does "read-only" forbid `compile_context` from persisting? → A: No. Read-only
  means sources, existing evidence, catalog history and workspace configuration are
  never mutated, and no tool ingests, reindexes, deletes or writes outside the
  configured store. `compile_context` uses the exact F008 service path, whose only
  writes are additive immutable derived CAS objects plus one atomic catalog commit;
  derived data remains disposable and reproducible.
- Q: What does "verify evidence" mean as a tool? → A: `get_context_receipt` loads a
  persisted compilation only after the complete F008 verification chain (object
  digests, canonical bytes, model validity, identities, row/object agreement, exact
  scopes). Unverifiable evidence is never returned.
- Q: Is `get_visual_evidence` from the planning document in scope? → A: No. Exact
  visual artifact production is F011. F009 offers no visual tool; visual need surfaces
  only through the F008 missing-evidence and visual-escalation notices inside compile
  results. The planning sketch in `docs/05` is updated at convergence to match.

## User Scenarios & Testing

### User Story 1 - Open a Safe Session and Navigate Evidence (Priority: P1)

As a local MCP client, I can open one pinned-protocol session over stdio and navigate
the prepared corpus — list documents, check source status, read outlines, exact blocks
and accepted rich evidence — without the server ever touching a path I supply or the
network.

**Why this priority**: A correctly bounded session and body-minimizing navigation are
the foundation every other tool builds on and the primary confused-deputy boundary.

**Independent Test**: Start the server against a mixed text/rich workspace, complete
the initialize handshake, call every navigation tool by registered identifier, and
verify bounded verified output, untrusted-data envelopes and zero filesystem,
provider or network reach.

**Acceptance Scenarios**:

1. **Given** a prepared workspace and a client that sends `initialize` with the pinned
   protocol revision, **When** the session opens, **Then** the server returns its
   identity, exact protocol revision and a tools-only capability set, and rejects any
   tool call that arrives before initialization completes.
2. **Given** registered document identifiers, **When** the client lists documents,
   checks one source status or reads one outline, **Then** every result is body-free
   structural data verified against the catalog, with stable pagination bounds.
3. **Given** a block or rich-evidence projection identifier, **When** the client
   retrieves exact content, **Then** the body is verified against content-addressed
   storage and returned inside the structural untrusted-data envelope, never as bare
   text.
4. **Given** any parameter containing a filesystem path, path traversal, URL, shell
   fragment or control characters, **When** any tool is called, **Then** the value is
   treated purely as an identifier candidate, fails validation or lookup with one
   sanitized stable error and causes no path resolution or file access.

---

### User Story 2 - Search Evidence and Compile Verified Context (Priority: P2)

As a local MCP client, I can search prepared evidence and compile bounded context with
an auditable receipt, receiving handles and accounting by default and explicit bounded
payloads only on request.

**Why this priority**: Retrieval and bounded compilation are the evidence handoff MCP
exists to expose; they must reuse the exact verified services without moving business
logic into the transport layer.

**Independent Test**: Search with lexical queries and filters, compile a task across
two documents under a small budget, inspect the receipt, and compare every result with
the equivalent CLI output for the same workspace.

**Acceptance Scenarios**:

1. **Given** a lexical query with optional document, version, kind, trust, page or
   slide filters, **When** `search_document` runs, **Then** results match the verified
   F005 service exactly, are capped by the declared limit and label every snippet as
   untrusted data.
2. **Given** a task, bounded document list, budget, unit and mode, **When**
   `compile_context` runs, **Then** the exact F008 compilation persists atomically and
   the response returns receipt/bundle handles, decision counts, accounting and
   notices without bodies by default.
3. **Given** `include_bundle` set explicitly, **When** compilation completes, **Then**
   the bounded bundle payload is included only while the complete serialized response
   stays within the response cap, and every evidence item remains delimited untrusted
   data.
4. **Given** a receipt identifier, **When** `get_context_receipt` runs, **Then** the
   receipt is returned only after complete digest, canonical, model, identity, row and
   scope verification, and any tamper produces one stable integrity error.

---

### User Story 3 - Fail Closed at Every Boundary (Priority: P3)

As an operator, every malformed request, oversize input, unknown identifier, hostile
payload, cancellation, deadline or storage fault produces a bounded sanitized error
from one versioned taxonomy, and no tool call can mutate sources, exceed its limits or
leak document content into diagnostics.

**Why this priority**: MCP is the first machine-facing boundary; confused-deputy,
enumeration and injection resistance plus stable failure semantics are acceptance
concerns, not hardening afterthoughts.

**Independent Test**: Drive the hostile-input matrix (malformed framing, oversized
messages, batch arrays, unknown methods/tools, path-bearing and enumerated
identifiers, prompt-injection queries, cancellation and deadline injection, catalog
and CAS corruption) and verify uniform sanitized outcomes with zero partial writes.

**Acceptance Scenarios**:

1. **Given** malformed JSON, an oversized line, a batch array, an unknown method or a
   protocol-version mismatch, **When** the message arrives, **Then** the server answers
   with the documented stable error category and remains able to serve later valid
   requests or exits cleanly on EOF.
2. **Given** sequential probes of random, near-miss or historically deleted
   identifiers, **When** lookups fail, **Then** every failure returns the same
   sanitized `not_found` category with no existence, timing, path or catalog detail
   beyond the documented envelope.
3. **Given** a query or task containing prompt injection, URLs, commands or
   document-shaped instructions, **When** search or compilation returns content,
   **Then** all returned text stays structurally labelled untrusted data and no side
   effect, path resolution, network request or instruction execution occurs.
4. **Given** cancellation mid-compilation or a deadline overrun, **When** the
   operation stops, **Then** no catalog-visible compilation is created, the client
   receives the stable cancelled or deadline category and earlier valid compilations
   remain unchanged.

---

### User Story 4 - Launch and Operate the Server Locally (Priority: P4)

As a local user or client integrator, I can start the server through the existing CLI,
discover the exact tool surface programmatically and rely on documented limits,
errors, audit logging and rollback.

**Why this priority**: A stable launch verb and honest operational documentation make
the boundary usable without weakening any existing command.

**Independent Test**: Launch `openardp mcp` in a fresh workspace, run `tools/list`,
compare descriptors with the published contract, exercise startup failures (missing
or incompatible workspace) and confirm all pre-existing CLI behavior is unchanged.

**Acceptance Scenarios**:

1. **Given** an initialized workspace, **When** `openardp mcp` starts, **Then** it
   serves exactly the published tool set on stdio and exits cleanly on stdin EOF
   without modifying any existing CLI command or output envelope.
2. **Given** a missing, incompatible or corrupted workspace, **When** the server
   starts, **Then** it fails with the existing sanitized startup classification and
   never opens a partial or repair-mutated workspace.
3. **Given** `tools/list`, **When** a client inspects the surface, **Then** every
   descriptor states its name, exact version, input schema, output bounds and the
   explicit notice that returned document text is untrusted data, matching the
   published contract byte-for-byte in deterministic order.

### Edge Cases

- Empty workspace, a document without a READY head, mixed text and rich corpora, or a
  corpus larger than the list/outline pagination caps.
- A request line at exactly the size limit versus one byte over; a result page exactly
  at the cap; a serialized response that would exceed the response cap.
- Identifiers that are valid UUIDs but unknown, malformed UUIDs, SHA-256 receipt IDs
  with wrong length or casing, duplicate document IDs in one compile call and more
  scopes than the compiler cap.
- Queries with quotes, Unicode, control characters, path-like text, URLs, prompt
  injection or the maximum accepted lexical item count.
- A task or bundle at the minimum budget envelope, an exact-fit budget, one-unit
  overflow, or `include_bundle` with a bundle larger than the response cap.
- A second `initialize`, tool calls before initialization, notifications with unknown
  names, request IDs as string, number or omitted, and duplicate request IDs.
- Cancellation before retrieval, during candidate verification, after CAS publication
  or immediately before catalog commit; deadline expiry at each bounded checkpoint.
- Workspace opened while a CLI ingestion is in progress; catalog locked, too new,
  drifted or checksummed-migration mismatch at startup or mid-session.
- stdin EOF mid-message, an output pipe that closes early, and shutdown while a
  cancelled compilation is unwinding.

## Requirements

### Functional Requirements

- **FR-001**: The server MUST communicate over exactly one local stdio transport using
  newline-delimited UTF-8 JSON-RPC 2.0 messages; it MUST NOT open a network listener,
  Unix socket, named pipe or any remote transport.
- **FR-002**: Each inbound line MUST be bounded at 64 KiB (fixed), parse as one JSON
  object and be processed as a single request or notification; batch arrays, embedded
  newlines and non-object messages MUST be rejected with a stable framing error. No
  more than 64 non-cancellation frames may await sequential dispatch; overflow MUST
  cancel active work and close the session with a sanitized protocol error instead of
  accumulating unbounded memory.
- **FR-003**: The session MUST implement `initialize`, `notifications/initialized`,
  `ping`, `tools/list` and `tools/call` under the pinned protocol revision
  `2025-06-18`; any other revision, method or pre-initialization tool call MUST fail
  with a documented stable category.
- **FR-004**: Declared capabilities MUST be exactly tools; resources, prompts,
  sampling, logging control, subscriptions and roots MUST NOT be offered or honored.
- **FR-005**: `tools/list` MUST return the complete tool descriptors — name, exact
  interface version, input schema, output bounds and untrusted-data notice — in
  deterministic order and byte-stable canonical form.
- **FR-006**: The tool set MUST be exactly: `list_documents`, `get_source_status`,
  `get_document_outline`, `get_block`, `search_document`, `list_evidence`,
  `get_evidence`, `compile_context` and `get_context_receipt`. No write, ingestion,
  reindex, deletion, export, watcher or visual-extraction tool may exist.
- **FR-007**: Every tool MUST reach state exclusively through the existing service
  ports (`DocumentQueryService`, `SearchService`, `RichEvidenceService`,
  `ContextCompilerService`); the interface layer MUST NOT open files, databases,
  sockets or provider components directly.
- **FR-008**: Tool parameters MUST be object-scoped identifiers, query text, filters
  and bounded numerics only; no parameter may accept, resolve or imply a filesystem
  path. `get_source_status` MUST accept a document identifier only, never the path
  target form the CLI permits.
- **FR-009**: Every body-bearing result (block text, rich retrieval body, search
  snippet, bundle evidence) MUST be enclosed in the structural untrusted-data
  envelope with media type and explicit data-only role; tool descriptions MUST state
  that returned document text is untrusted data and never an instruction.
- **FR-010**: All tool input MUST be validated through the existing domain parsers and
  bounded models before any service call; invalid input MUST fail with one sanitized
  stable category and no service side effect.
- **FR-011**: Every tool output MUST be bounded by documented per-tool caps (list
  size, outline items, search limit, body bytes, response bytes); truncation MUST be
  explicit and deterministic.
- **FR-012**: The complete serialized response MUST stay within a documented response
  byte cap; compile results MUST default to body-free handles and accounting, and an
  explicit `include_bundle` opt-in MUST fail with a stable limit category rather than
  exceed the cap.
- **FR-013**: `compile_context` MUST invoke the exact F008 compile-and-persist path
  with the declared estimator, policy and limits; its only durable effect is the
  additive immutable derived bundle/receipt publication and atomic catalog commit,
  and it MUST NOT mutate sources, heads, existing evidence or configuration.
- **FR-014**: `get_context_receipt` MUST run the complete F008 verification chain
  before returning any receipt field; integrity failure MUST return one stable
  category and no partial receipt.
- **FR-015**: Every request MUST run under a documented deadline (default 30 s,
  configurable 1–120 s) checked before dispatch and threaded into the compiler's
  bounded cancellation checkpoints; overrun MUST yield the stable deadline category.
  The deadline does not interrupt a blocked stdin read between requests.
- **FR-016**: `notifications/cancelled` MUST map to the compiler's cancellation port;
  the stdio reader MUST be able to observe it while a request is running. Cancellation
  MUST produce the stable cancelled category, prevent catalog commit and leave earlier
  compilations untouched. Unknown or completed request identifiers MUST be ignored.
- **FR-017**: All failures MUST map to one versioned error taxonomy
  (`mcp_error_version: 1`) with stable machine codes — protocol/framing, unsupported
  version, unknown tool, invalid params, not found, conflict, integrity/workspace,
  cancelled, deadline and internal — carried in JSON-RPC error objects without
  tracebacks, paths, document bodies, query text or configuration detail.
- **FR-018**: Lookup failures for unknown, malformed or non-existent identifiers MUST
  return one uniform sanitized not-found outcome with no distinguishable existence
  signal beyond the documented envelope.
- **FR-019**: Operational logging MUST record only tool name, request identifier,
  outcome code, identifier digests and timings; it MUST never record query text, task
  text, evidence bodies, source paths, native payloads or secrets.
- **FR-020**: The server MUST be single-user and single-workspace, bound to one
  explicitly configured local store directory; it MUST exit cleanly on stdin EOF and
  MUST NOT mutate the workspace on startup, including no implicit migration or
  repair.
- **FR-021**: The implementation MUST use the Python standard library plus existing
  project dependencies only; no MCP SDK, async framework or network library may be
  added, and the locked dependency set MUST remain unchanged.
- **FR-022**: Responses for identical inputs over an unchanged corpus MUST be
  byte-identical canonical JSON except documented volatile fields (the source-status
  observation timestamp and server-provided timing metadata), which MUST be named in
  the contract.
- **FR-023**: The CLI MUST add one `openardp mcp` verb that composes and runs the
  server against the configured store; every existing command, JSON envelope, exit
  classification and human output MUST remain unchanged.
- **FR-024**: Startup MUST fail closed with the existing sanitized classification when
  the workspace is missing, incompatible, too new, locked or corrupted; the server
  MUST NOT serve a partially verified workspace.
- **FR-025**: The eleven existing public schemas, all identity vectors, the F006
  conformance corpus, workspace revision 6 and every F001–F008 behavior MUST remain
  byte-for-byte and semantically unchanged; F009 adds no new persisted contract root.
- **FR-026**: All behavior MUST be covered by synthetic, network-disabled tests —
  including framing, lifecycle, confused-deputy, path, ID-enumeration, injection,
  limit, cancellation, deadline, corruption and CLI cases — passing on Linux, macOS
  and Windows.
- **FR-027**: Public documentation MUST describe installation, client configuration,
  the exact tool reference, security boundary, limits, error taxonomy, audit
  behavior, compatibility and rollback without claiming universal security, sandbox
  strength or remote suitability.

### Non-Goals and Compatibility Impact

- **Non-goal**: No write, ingestion, reindex, deletion, retention, export/import,
  watcher or scheduling tool; no mutation of sources or existing evidence.
- **Non-goal**: No streamable HTTP or any network transport, multi-user access,
  authentication or authorization framework; the boundary is one local user on one
  configured workspace.
- **Non-goal**: No visual-evidence extraction tool (F011), no semantic/embedding
  search, no model provider calls, no MCP resources or prompts.
- **Non-goal**: No new persisted public contract root, no workspace migration and no
  change to the eleven frozen schemas or identity vectors.
- **Non-goal**: No third-party MCP SDK dependency; the transport codec is a narrow
  stdlib implementation behind the interface layer.
- **Compatibility impact**: Additive application surface only — one new CLI verb, the
  experimental `MCP interface 0.1.0` application contract (tool descriptors plus error
  taxonomy) and interface-layer modules. Contract, workspace, provider-profile and
  export-profile versions are unchanged. The `docs/05` planning sketch is aligned at
  convergence to remove the not-yet-existing visual tool from the delivered set.

### Key Entities

- **MCP Session**: One stdio lifecycle under the pinned protocol revision with
  tools-only capabilities, per-request deadlines and cancellation routing.
- **Tool Descriptor**: Stable published description of one read-only tool — name,
  interface version, input schema, output bounds and untrusted-data notice.
- **Tool Request/Result**: Bounded identifier-scoped input and verified output whose
  body-bearing fields always use the untrusted-content envelope.
- **Error Envelope**: Versioned sanitized failure object with one stable machine code,
  fixed JSON-RPC code mapping and a body-free message.
- **Session Limits**: Documented caps for message bytes, per-tool pagination, body
  bytes, response bytes, scopes and deadline.
- **Audit Record**: Body-free operational log entry with tool, request identifier,
  outcome code, identifier digests and duration.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The reviewed quickstart completes initialize → list → outline → search →
  compile → receipt against a mixed workspace with zero network calls and zero socket
  creation.
- **SC-002**: Across 20 identical scripted tool sequences over an unchanged corpus,
  all responses are byte-identical canonical JSON modulo the documented volatile
  fields.
- **SC-003**: In 100% of boundary probes, a request line at the cap succeeds and one
  byte over fails; every per-tool limit truncates deterministically at its exact cap.
- **SC-004**: Every body-bearing field in every reviewed response is enclosed in the
  untrusted-data envelope; bare document text occurs zero times.
- **SC-005**: In 100% of confused-deputy and path probes (absolute, relative,
  traversal, URL, shell fragment), no filesystem access occurs and every outcome is
  one documented sanitized category.
- **SC-006**: Every injected fault — framing, version, unknown tool, invalid params,
  unknown ID, conflict, corruption, cancellation, deadline — maps to exactly one
  documented taxonomy code; undocumented codes occur zero times.
- **SC-007**: Cancellation and storage-fault injection at every compilation phase
  yields zero partial catalog-visible compilations and zero mutations of earlier
  valid compilations.
- **SC-008**: Query text, task text, evidence bodies and source paths appear zero
  times in reviewed error envelopes, default logs and audit records.
- **SC-009**: All eleven public schemas, both established identity-vector files, the
  F008 context vectors and the F006 conformance corpus remain byte-identical to the
  F008 base.
- **SC-010**: The full locked gate passes on Linux, macOS and Windows with at least
  85% branch coverage, no tracked-file drift and successful source/wheel builds.
- **SC-011**: `tools/list` output matches the published contract descriptors exactly,
  and the delivered tool set contains zero write-capable, path-accepting or network
  tools.
- **SC-012**: Existing CLI snapshot and integration suites pass unchanged, and server
  startup against missing, incompatible or corrupted workspaces fails closed in 100%
  of probes.

## Assumptions

- The MCP peer is a local client process launched by the same single user; trust
  comes from the local boundary plus least privilege, not from authentication.
- The pinned protocol revision `2025-06-18` satisfies the MVP tool lifecycle; a later
  revision or transport is a separate additive decision.
- stdio framing follows the MCP newline-delimited convention; clients using
  header-based framing are unsupported by design.
- `compile_context` persistence is acceptable derived-data behavior because receipts
  must remain auditable after the call; retention and deletion stay with F013.
- The existing F008 cancellation port and bounded checkpoints are sufficient for
  deadline enforcement; no preemptive threading or subprocess kill is introduced.
- Response caps are safety bounds, not throughput claims; large evidence remains
  reachable by handle through repeated bounded calls.
