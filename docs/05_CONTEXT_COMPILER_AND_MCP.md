# Context compiler, CLI and MCP contracts

**Status:** Feature 008 delivered the deterministic context compiler, the public
`ContextBundle 0.2.0`, the experimental `SelectionReceipt 0.1.0` and the `context` /
`context-receipt` CLI verbs documented below. MCP tools remain planned Feature 009
guidance; no MCP server exists.

## 1. Context compiler objective

Construct the smallest evidence bundle that can support the requested task under a budget and policy. It is not simply a
top-k vector search.

## 2. Delivered selection stages (F008)

1. Resolve each requested document to one exact READY snapshot scope.
2. Discover lexical candidates from the verified FTS accelerator and the bounded
   rich-projection scan; every hit is reverified against content-addressed bodies.
3. Classify freshness, trust zone, sensitivity and duplicates under the declared
   policy into selected-eligible, rejected and stale partitions.
4. Order candidates by the documented total order (high value, coverage, occurrences,
   scope, source order, representation, evidence id).
5. Admit greedily under one fixed-point estimator budget with ten-percent response
   reserve; record exact per-item costs.
6. Emit the bundle, the body-free receipt with exhaustive decision inventories, and
   honest missing-evidence/visual-escalation entries.

Semantic candidates, structural expansion and provider tokenizers remain later work
packages; the estimator is an exact versioned replaceable port with built-in
byte/character/conservative-token identities.

## 3. Evidence rules

- Numeric questions include exact table cells or source text, not only summaries.
- Visual/layout questions include the relevant image/page crop. Until visual
  extraction exists, VISUAL mode escalates `visual_evidence_required` honestly.
- Source-verification questions include source locator and integrity state.
- Generated summaries are labelled and never presented as quoted source text.
- Low-confidence OCR includes the original crop.

## 4. Delivered budgeting (F008)

The compiler measures complete canonical bundle bytes with one exact versioned
estimator (`openardp.utf8-bytes`, `openardp.unicode-characters` or
`openardp.conservative-utf8-tokens`, each `1.0.0`). The ledger reserves ten percent of
the limit for the response, admits whole items until the ceiling and records base,
incremental, used and remaining units. Estimated and actual usage are identical by
construction; provider token counts remain a later estimator implementation.

## 5. Context bundle

See `schemas/context-bundle-0.2.0.schema.json`. The bundle contains:

- query/task;
- source version scope;
- selected items and representation level;
- exact content or artifact handles;
- provenance;
- trust/sensitivity;
- estimated size;
- selection trace;
- warnings and missing evidence.

## 6. CLI surface

Delivered context verbs (stable JSON envelopes; human output may change):

```text
openardp context TASK --document ID [--document ID ...] --budget N \
    [--unit bytes|characters|tokens] [--mode MODE] [--include-bundle]
openardp context TASK --replay RECEIPT_ID [--unit UNIT]
openardp context-receipt RECEIPT_ID
```

Replay accepts only task, unit and receipt: the recorded snapshot, policy and budget
are authoritative. Default output is body-free handles plus accounting; only
`--include-bundle` returns the digest-checked untrusted-data payload. The remaining
roadmap sketch (watch/export/import/verify/gc/doctor/mcp) stays subject to its own
feature specs:

```text
openardp init [--store PATH]
openardp ingest PATH [--profile PROFILE] [--force]
openardp watch PATH [--recursive] [--debounce SECONDS]
openardp list
openardp status PATH|DOCUMENT_ID
openardp outline DOCUMENT_ID [--version VERSION]
openardp search QUERY [--document ID] [--kind KIND] [--limit N]
openardp get BLOCK_ID [--representation exact|summary|visual]
openardp export DOCUMENT_ID --output FILE
openardp import FILE
openardp verify FILE
openardp gc --dry-run
openardp doctor
openardp mcp [--transport stdio|streamable-http]
```

All commands support `--json` for stable machine-readable output. Human output may change; JSON output follows versioned
schemas.

## 7. MCP tools — MVP read-only

### `list_documents`

Returns IDs, titles, current versions, states and last ingestion time.

### `get_document_outline`

Returns hierarchy and block handles without full body text.

### `search_document`

Inputs: query, scope, filters, limit. Returns evidence candidates with scores and source locations.

### `compile_context`

Inputs: query/task, document IDs, budget, mode and evidence policy. Returns a context bundle or a persisted bundle handle.

### `get_block`

Returns exact normalized source content for one block.

### `get_visual_evidence`

Returns a resource/file handle for a page, slide, image or crop; it should not base64-embed large assets by default.

### `get_source_status`

Reports source/representation freshness, warnings and missing assets.

## 8. MCP safety

- No write or external side-effect tool in MVP.
- Tool descriptions explicitly state document text is untrusted data.
- Resource access is constrained to registered artifacts.
- Paths supplied by clients are resolved against configured roots and canonicalized.
- Large outputs are persisted and returned by handle to avoid context truncation.
- Audit tool calls without logging document bodies.

## 9. Codex integration

Codex supports local/remote MCP servers and reads repository `AGENTS.md`. Provide an installation snippet and an OpenARDP
skill only after the server tools are stable. The skill should instruct Codex to call `get_document_outline` or
`compile_context` before opening raw Office/PDF files and to request original visual evidence when required.
