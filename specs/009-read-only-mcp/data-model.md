# Data Model: Read-only MCP

## Version dimensions

| Dimension | F009 value | Changes when |
|---|---|---|
| application | package release | code ships |
| MCP interface | `0.1.0` experimental | tool set, descriptor shape, limits or error semantics change |
| MCP protocol | pinned `2025-06-18` | only via a new additive transport/lifecycle decision |
| error taxonomy | `mcp_error_version: 1` | error code set or mapping changes |
| workspace | SQLite revision `6` (unchanged) | not changed by F009 |
| persisted contracts | eleven frozen schemas (unchanged) | not changed by F009 |
| provider profile | unchanged | not changed by F009 |

## McpSessionConfig

| Field | Rule |
|---|---|
| `protocol_revision` | constant `2025-06-18`; any other client revision is rejected |
| `interface_version` | constant `0.1.0`; reported in `serverInfo` and descriptors |
| `max_line_bytes` | 64 KiB; one byte over fails the message, not the session |
| `max_pending_frames` | fixed 64 non-cancellation frames; overflow unwinds active work and closes the session |
| `response_bytes_cap` | default 1 MiB; configurable 64 KiB–4 MiB at launch |
| `deadline_ms` | default 30,000; configurable 1,000–120,000 at launch |
| `store` | one explicit local workspace directory; never derived from client input |

Configuration is fixed at server start; clients cannot widen limits per request.

## Lifecycle state machine

```text
START --initialize(revision match)--> INITIALIZING
INITIALIZING --notifications/initialized--> READY
READY --tools/list | tools/call | ping--> READY
any state --stdin EOF--> EXIT (clean, no mutation)
```

Rules:

- `initialize` is valid exactly once; a second call is `invalid_request`.
- `tools/call` and `tools/list` before initialization complete are `invalid_request`.
- `ping` is accepted in any state and answers with an empty result object.
- Unknown methods are `invalid_request` (`-32601` mapping); unknown notifications are
  discarded without response.
- A bounded reader observes `notifications/cancelled` while sequential application
  dispatch is active and sets the cooperative flag for the named active/queued request
  only; cancellation of an unknown or finished request is a no-op.

## Tool descriptors

Each descriptor published by `tools/list` carries:

| Field | Rule |
|---|---|
| `name` | one of the nine fixed tool names |
| `interface_version` | `0.1.0` |
| `description` | states purpose, read-only nature and the untrusted-data notice |
| `input_schema` | closed JSON object schema of bounded parameters |
| `output_bounds` | pagination cap, body cap and truncation semantics |

Descriptor order is the fixed tool-name order; the canonical serialization of the
complete list is fixture-pinned.

## Tool I/O projections

All outputs are projections of existing domain models; no new persisted entity
exists. Body-bearing fields reuse the F008 `UntrustedContentEnvelope`
(`content_role: "untrusted_data"`, delimiter `openardp-evidence-v1`, media type,
body).

| Tool | Input (bounded) | Output projection |
|---|---|---|
| `list_documents` | none | up to 256 `DocumentSummary` entries; body-free |
| `get_source_status` | `document_id` (UUID only) | `SourceStatus`; `checked_at` is a documented volatile field |
| `get_document_outline` | `document_id`, optional `version_id` | up to 1,000 `OutlineItem` entries; labels truncated at 512 chars |
| `get_block` | `block_id` | `ContentBlock` with `text` replaced by the untrusted envelope |
| `search_document` | `query`, optional `document_id`, `version_id`, `kind`, `trust`, `page`, `slide`, `limit` (default 20, max 100) | `SearchOutcome` with enveloped snippets; query echo excluded |
| `list_evidence` | `document_id`, optional `version_id` | up to 256 body-free `EvidenceProjection` entries |
| `get_evidence` | `evidence_projection_id`, optional `document_id` | verified projection plus enveloped UTF-8 body |
| `compile_context` | `task` (1–4,096 chars), `document_ids` (1–32), `budget_limit`, `unit`, optional `mode`, `include_bundle` (default false) | receipt/bundle handles, counts, budget ledger, notices; optional bounded bundle with enveloped items |
| `get_context_receipt` | `receipt_id` (`sha256:` + 64 lowercase hex) | fully verified body-free `SelectionReceipt` |

Notes:

- `search_document` excludes the CLI's raw query echo from the machine-facing result;
  the query is caller-supplied and never re-broadcast by the server.
- A single returned body (block, rich retrieval, bundle item) is never truncated:
  truncation would falsify evidence. A verified body larger than the body cap fails
  the call with the stable limit category; pagination caps truncate only
  body-free lists, explicitly and deterministically.
- `compile_context` maps `unit` to the exact F008 estimator identities
  (`bytes`, `characters`, `tokens`) and defaults `mode` to `mixed`; replay is not a
  separate tool in F009.
- Response-cap accounting measures the complete serialized result object; exceeding
  the cap fails the call with `invalid_params`-family `response_cap_exceeded`
  semantics mapped to the stable limit category rather than truncating JSON mid-byte.

## Error envelope

JSON-RPC error object shape:

```json
{
  "code": -32000,
  "message": "fixed body-free text",
  "data": {
    "mcp_error_version": 1,
    "category": "stable_machine_code"
  }
}
```

| Category | JSON-RPC code | Meaning |
|---|---:|---|
| `invalid_request` | -32600 / -32601 / -32602 | framing, unknown method, malformed params envelope |
| `unsupported_protocol_version` | -32602 | client revision differs from the pinned revision |
| `unknown_tool` | -32602 | tool name outside the fixed set |
| `invalid_params` | -32602 | input rejected by domain validation or response-cap limit |
| `not_found` | -32000 | any unknown or non-existent identifier; uniform shape |
| `conflict` | -32001 | state conflicts (busy, ambiguous, replay-mismatch family) |
| `integrity_or_workspace` | -32002 | catalog/CAS/verification drift or workspace failure |
| `cancelled` | -32003 | cooperative cancellation observed at a checkpoint |
| `deadline_exceeded` | -32004 | per-request deadline elapsed |
| `internal` | -32603 | sanitized fallback; never a traceback or detail |

Mapping reuses the CLI classification so identical failures read identically across
interfaces. `message` strings are fixed constants; client-supplied values never
appear in any error field.

## Audit record

One structured log entry per completed request:

| Field | Rule |
|---|---|
| `tool` | fixed tool name |
| `request_id_digest` | SHA-256 of the request identifier, never the raw value |
| `outcome` | taxonomy category or `ok` |
| `duration_ms` | integer monotonic duration |
| `identifier_digests` | digests of addressed object identifiers where applicable |

Query text, task text, evidence bodies, source paths, native payloads and raw request
identifiers are never logged.

## Volatile fields

Determinism (FR-022) covers every response field except:

- `get_source_status.checked_at` (observation timestamp);
- framing-level timing metadata, if a client requests it.

Both are documented here and excluded from byte-stability fixtures.
