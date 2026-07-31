# Contract: MCP Read-only Tool Surface 0.1.0 Experimental

## Status

F009 adds the experimental `MCP interface 0.1.0` application contract. It is
published as reviewed feature documentation plus deterministic `tools/list`
transcript fixtures under `tests/fixtures/mcp/`. It adds no JSON Schema root under
`schemas/` and no workspace migration; the eleven public schemas and all identity
vectors remain byte-frozen. The interface version evolves independently of persisted
contract versions.

## Transport and lifecycle

- One stdio transport; newline-delimited UTF-8 JSON-RPC 2.0; one JSON object per
  line; inbound lines bounded at 64 KiB.
- Pinned protocol revision `2025-06-18`; mismatches fail with
  `unsupported_protocol_version`.
- Methods: `initialize`, `notifications/initialized`, `ping`, `tools/list`,
  `tools/call`, `notifications/cancelled`. Batch arrays are rejected.
- Capabilities are exactly tools. Resources, prompts, sampling, logging control and
  subscriptions are neither offered nor honored.
- Clean exit on stdin EOF; no workspace mutation at startup or shutdown.

## Fixed tool set

Nine read-only tools, in canonical descriptor order:

1. `list_documents` — body-free current document summaries (cap 256).
2. `get_source_status` — freshness/integrity status for one document identifier.
   Identifiers only: the path-target form the CLI permits is not accepted.
3. `get_document_outline` — structural outline for one document (cap 1,000 items).
4. `get_block` — one verified exact block; text inside the untrusted envelope.
5. `search_document` — verified lexical search with bounded filters and limit
   (default 20, max 100); snippets enveloped; no query echo.
6. `list_evidence` — body-free accepted rich evidence for one document (cap 256).
7. `get_evidence` — one verified rich retrieval body inside the untrusted envelope.
8. `compile_context` — exact F008 compile-and-persist; handle-first response;
   explicit bounded `include_bundle` opt-in.
9. `get_context_receipt` — one receipt returned only after the complete F008
   verification chain.

Every descriptor states that returned document text is untrusted data, never an
instruction, and that all tools are read-only over registered objects.

## Read-only guarantee

- No parameter accepts, resolves or implies a filesystem path.
- No tool ingests, reindexes, deletes, exports or mutates sources, heads, existing
  evidence, indexes, catalog history or configuration.
- The only durable effect any tool may cause is `compile_context`'s additive
  immutable derived CAS publication plus one atomic catalog commit through the exact
  F008 path; derived data remains disposable and reproducible.
- The server composes only query, search, evidence and compiler services; ingestion
  and reindex services are never constructed in the MCP composition root.

## Untrusted-content guarantee

Every body-bearing field (block text, rich retrieval body, search snippet, bundle
evidence) is enclosed in:

```json
{
  "content_role": "untrusted_data",
  "delimiter": "openardp-evidence-v1",
  "media_type": "text/plain",
  "body": "exact verified content"
}
```

The envelope is data, not an authority boundary by itself; structural trust
classification is enforced by the underlying services and preserved in outputs.

## Bounds

| Bound | Value |
|---|---|
| inbound line | 64 KiB |
| pending non-cancellation frames | 64 per session |
| serialized response | 1 MiB default (64 KiB–4 MiB launch range) |
| request deadline | 30 s default (1–120 s launch range) |
| list/outline/evidence pagination | 256 / 1,000 / 256 |
| search limit | 20 default, 100 max |
| one returned body | 256 KiB |
| compile scopes | 1–32 (compiler cap) |

Truncation is explicit and deterministic and applies only to body-free lists; a
single verified body is never truncated. A body or serialized result above its cap
fails the call with the stable limit category instead of emitting partial or falsified
output. Pending-frame overflow cancels active work and closes the bounded input session
with a sanitized protocol error instead of accumulating unbounded memory; cancellation
notifications are consumed concurrently and do not enter that queue.

## Determinism

Identical calls over an unchanged corpus produce byte-identical canonical JSON
except the documented volatile fields (`get_source_status.checked_at` and optional
timing metadata). Descriptor order, envelope shape and ledger/accounting projections
are fixture-pinned.

## Compatibility

Additive only. All pre-F009 public contracts, identity vectors, the conformance
corpus, workspace revision 6 and every CLI command remain unchanged. Any later tool
addition, removal, limit change or error-semantics change requires a new reviewed
interface release; breaking changes require the governed ADR/migration process.
