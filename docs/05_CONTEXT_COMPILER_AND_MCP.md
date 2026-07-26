# Context compiler, CLI and MCP contracts

**Status:** Planned Feature 008/009 contract guidance. The currently delivered CLI verbs are documented in the
[README](../README.md); no MCP server exists through Feature 005A.

## 1. Context compiler objective

Construct the smallest evidence bundle that can support the requested task under a budget and policy. It is not simply a
top-k vector search.

## 2. Selection stages

1. Resolve document scope and required freshness.
2. Classify task requirements deterministically where possible:
   - exact facts/numbers;
   - summarization;
   - visual/layout review;
   - cross-document comparison;
   - source verification.
3. Retrieve lexical candidates.
4. Optionally add semantic candidates.
5. Expand structural parents/children and captions.
6. Enforce evidence-type rules.
7. Deduplicate and rank.
8. Allocate budget across metadata, exact text, tables and visual evidence.
9. Emit bundle plus selection trace and omitted-candidate reasons.

## 3. Evidence rules

- Numeric questions include exact table cells or source text, not only summaries.
- Visual/layout questions include the relevant image/page crop.
- Source-verification questions include source locator and integrity state.
- Generated summaries are labelled and never presented as quoted source text.
- Low-confidence OCR includes the original crop.

## 4. Budgeting

Use a pluggable tokenizer estimator. The core operates with a conservative character/byte estimator when no provider is
configured. Store both estimated and actual provider token counts when available.

Budget reserve:

- 10% response/system reserve;
- 10% provenance/metadata reserve;
- remainder for evidence, configurable by caller.

## 5. Context bundle

See `schemas/context-bundle.schema.json`. The bundle contains:

- query/task;
- source version scope;
- selected items and representation level;
- exact content or artifact handles;
- provenance;
- trust/sensitivity;
- estimated size;
- selection trace;
- warnings and missing evidence.

## 6. Target CLI surface

The following is a roadmap sketch, not a current command contract. Feature-specific specs may refine or reject later
verbs. In particular, export/import/verify remain an experiment:

```text
openardp init [--store PATH]
openardp ingest PATH [--profile PROFILE] [--force]
openardp watch PATH [--recursive] [--debounce SECONDS]
openardp list
openardp status PATH|DOCUMENT_ID
openardp outline DOCUMENT_ID [--version VERSION]
openardp search QUERY [--document ID] [--kind KIND] [--limit N]
openardp get BLOCK_ID [--representation exact|summary|visual]
openardp context QUERY --document ID [--budget N] [--mode MODE]
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
