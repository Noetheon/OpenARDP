# Context compiler, CLI and MCP contracts

**Status:** Feature 008 delivered the deterministic context compiler, the public
`ContextBundle 0.2.0`, the experimental `SelectionReceipt 0.1.0` and the `context` /
`context-receipt` CLI verbs documented below. Feature 009 delivers the bounded
read-only stdio MCP interface documented here. Feature 030 adds an explicit optional
semantic retrieval profile to both surfaces while preserving lexical defaults. Feature 011 adds explicit visual
materialization and verified handle-only context candidates; HTTP remains later.

## 1. Context compiler objective

Construct the smallest evidence bundle that can support the requested task under a budget and policy. It is not simply a
top-k vector search.

## 2. Delivered selection stages (F008)

1. Resolve each requested document to one exact READY snapshot scope.
2. Discover lexical candidates from the verified FTS accelerator, the bounded
   rich-projection scan and already materialized canonical visual descriptors; every
   candidate is reverified against catalog and content-addressed facts.
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
- Visual/layout questions select an already materialized descriptor as a
  `visual_handle`. If none exists for the exact current scope, VISUAL mode preserves
  `visual_evidence_required`; compilation never invokes a renderer or interpreter.
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
    [--unit bytes|characters|tokens] [--mode MODE] [--include-bundle] \
    [--retrieval-profile lexical|semantic]
openardp context TASK --replay RECEIPT_ID [--unit UNIT] [--retrieval-profile PROFILE]
openardp context-receipt RECEIPT_ID
openardp mcp --store PATH [--tools agent|full|legacy] [--deadline-ms N] [--response-cap-bytes N] \
    [--semantic-bundle PATH --semantic-source-lock PATH]
```

`context` also accepts document names or path suffixes for `--document`. Without `--document`, it selects up to 32
documents that match the task (or all prepared documents when nothing matches). The agent commands (`add`, `docs`,
`find`, `read`, `toc`, `verify`, `agent-view` and `refresh`) are described in
[Agent access](32_AGENT_ACCESS.md).

Replay accepts only task, unit and receipt: the recorded snapshot, policy and budget
are authoritative. New compilation remains lexical unless `semantic` is explicit. Semantic compile/replay additionally
requires the exact verified external bundle and source lock; replay infers the persisted profile when the option is
omitted and rejects provider/algorithm drift. Default output is body-free handles plus accounting; only
`--include-bundle` returns the digest-checked untrusted-data payload. Ordinary commands
support `--json`; `mcp` reserves stdout for newline-delimited JSON-RPC and accepts no
CLI JSON envelope switch. Watch, export, import, verification, garbage collection,
doctor and HTTP remain separate work packages. F011 visual CLI operations are explicit
mutations outside MCP and accept only registered identifiers.

## 7. Delivered MCP tools — read-only stdio

The interface is experimental `0.3.0`
([F040 contract](../specs/040-agent-ready-access/contracts/mcp-agent-tools.md)). It negotiates MCP protocol revisions
`2025-11-25`, `2025-06-18`, `2025-03-26` and `2024-11-05`, answering with the newest one for an unknown request. Every
result is an MCP `content` block. Correctable failures are `isError` results with a hint, and the versioned error
taxonomy is in `_meta`.

The default `agent` tool set has five read-only tools with compact text results. Each result locates text by file,
page or slide and line, and names the exact version:

1. `list_documents` — prepared documents with type, size in tokens and source freshness.
2. `find` — ranked passages for a question or keywords across all documents.
3. `read` — one page, slide, section or line range, bounded by `max_tokens`.
4. `outline` — headings or pages with line numbers and section sizes.
5. `verify_quote` — exact or normalized quote verification, outdated-version detection and the closest passage.

`--tools legacy` publishes the nine F009 tools below, and `--tools full` publishes both sets. Their JSON values are
unchanged but are now carried as text content:

1. `list_documents` — body-free summaries, at most 256.
2. `get_source_status` — identifier-scoped freshness/integrity.
3. `get_document_outline` — at most 1,000 structural items.
4. `get_block` — one verified block in an untrusted-data envelope.
5. `search_document` — verified lexical results, at most 100 enveloped snippets.
6. `list_evidence` — at most 256 body-free rich projections.
7. `get_evidence` — one verified rich retrieval body.
8. `compile_context` — exact compile-and-persist, handle-first and lexical by default; optional `retrieval_profile`
   selects a process-authorized semantic capability without accepting paths or provider settings.
9. `get_context_receipt` — fully verified body-free F008 receipt.

Descriptors, parameter schemas, bounds and error fixtures live under
`tests/fixtures/mcp/` (`tools-list.json` is the agent listing; `tools-list-0.2.0.json` keeps the previous legacy
listing). The normative contracts are `specs/040-agent-ready-access/contracts/mcp-agent-tools.md` and, for the legacy
tools, `specs/009-read-only-mcp/contracts/mcp-read-only-tools.md`.

## 8. MCP safety

- No ingestion, reindex, delete, export, arbitrary file, network or external
  side-effect tool exists. `compile_context` may only publish reproducible immutable
  derived bundle/receipt objects through the exact F008 atomic path.
- Tool descriptions explicitly state document text is untrusted data.
- Legacy tools take stored identifiers. Agent tools also accept a document's file name or path suffix, resolved only
  among already prepared documents, never as a filesystem path.
- Semantic bundle/source-lock paths are trusted server-start arguments only. A client requesting `semantic` from an
  unconfigured server receives `invalid_params`; the server never falls back to lexical retrieval.
- Inbound lines are fixed at 64 KiB; complete responses default to 1 MiB and may be
  configured only from 64 KiB through 4 MiB at launch.
- Deadlines default to 30 seconds (allowed 1–120 seconds); cancellation is cooperative
  at bounded F008 checkpoints and never exposes partial catalog state.
- Bodies are never truncated. Oversize body/response calls fail with the stable
  versioned taxonomy; body-free pages expose explicit truncation.
- Audit records contain only fixed tool names, request-id digests, outcomes and timing.

## 9. Codex integration

Configure a local client to execute `openardp mcp --store /absolute/workspace` over
stdio; [Agent access](32_AGENT_ACCESS.md) shows the Claude Code and Codex configuration. With the default tool set,
use `find` or `outline` first, `read` only the needed range and `verify_quote` before citing. With the audit tools,
prefer `get_document_outline` or handle-first `compile_context` before exact body tools. Visual evidence is not an MCP tool. F011 lets the unchanged
`compile_context` tool select a pre-materialized exact descriptor-object handle through
the existing bundle shape; it still reports `visual_evidence_required` when no current
record exists and never grants MCP rendering authority.

To authorize semantic retrieval for that process, add both `--semantic-bundle` and
`--semantic-source-lock` at server start. The client may then send only
`"retrieval_profile":"semantic"`; model selection, paths, limits and policies remain outside MCP authority.
