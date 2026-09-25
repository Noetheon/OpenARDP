# ADR 0020: Serve agents through disposable agent texts with read-time verification

Status: Accepted for Feature 040

Date: 2026-09-24

## Context

Coding and chat agents are the main consumers of prepared documents. A project audit found that they could not use
OpenARDP efficiently or, over MCP, at all:

- The stdio server read requests with a blocking `read(n)` and answered only after end of input, so a real client got
  no reply. It accepted only protocol revision `2025-06-18`, so clients that offered `2025-03-26` or `2025-11-25`
  were rejected. Tool results were bare JSON instead of MCP `content` blocks.
- The nine F009 tools require UUIDs. A typical question first needs `list_documents`, which cost about 9,000 tokens
  for 65 documents, and results spend most of their tokens on hashes, scopes and trust envelopes rather than text.
- Nothing let an agent go from a question to the exact page or lines, read only that range and check a quote before
  citing it.
- The isolated Docling worker failed on multi-core Linux hosts: `RLIMIT_AS` also counts address space that OpenBLAS
  and CUDA-enabled torch reserve at import, so imports failed before any document was parsed.

ADR 0008 keeps provider-native artifacts authoritative and forbids a second complete provider-neutral document
representation. ADR 0009 treats indexes as accelerators whose returned content must be verified.

## Decision

1. **Agent texts.** Each READY head gets one disposable agent text. TXT, Markdown and CSV use the exact decoded source,
   so line numbers are source line numbers. For PDF, DOCX and PPTX, `docling-core` renders Markdown in-process from the
   retained DoclingDocument. No source bytes are parsed. Page and slide markers (`<!-- page N -->`) let agents cite
   locations. The renderer identity (`openardp-docling-markdown/1+docling-core-<version>`) is recorded with the text.
   Without `docling-core`, a provider-free rendering of the accepted projections is used. An agent text is a lossy
   derived view for reading, never evidence authority or a replacement for the native artifact.
2. **Agent index.** Passages of about 700 characters, cut at headings and blocks and addressed by line range, live in
   `<workspace>/agent-cache/agent-index.sqlite3`. The index uses SQLite FTS5 with diacritic folding and prefix terms. It
   is format-versioned, rebuilt from the catalog when unreadable or foreign, and reconciled with catalog heads on every
   call: version, representation, source path and renderer.
3. **Read-time verification.** The index only locates passages. Returned text, snippets, headings, pages and document
   identity come from a copy rebuilt from authoritative sources:
   - the CAS source object for text sources;
   - for rendered sources, the accepted native object that the catalog names, after its SHA-256 is rechecked;
   - the catalog for path, version and media type.

   The rebuild runs once per representation and process and is bounded in memory. An index entry that disagrees is
   replaced. Quote verification narrows candidates with the index but confirms every positive result against the
   verified text. A damaged or forged index can therefore hide a match, but cannot make altered text appear or a quote
   verify.
4. **Surfaces.**
   - The CLI adds `add` (folders, idempotent, auto-initializing), `docs`, `find`, `read`, `toc`, `verify`,
     `agent-view` and `refresh`.
   - `openardp mcp` defaults to the `agent` tool set: `list_documents`, `find`, `read`, `outline` and `verify_quote`.
     These are read-only tools with titles and annotations, compact text results, server instructions and `isError`
     results with a corrective hint.
   - `--tools legacy` keeps the nine F009 tools and `--tools full` offers both. All results now use `content` blocks
     (MCP interface 0.3.0).
   - The server negotiates `2025-11-25`, `2025-06-18`, `2025-03-26` and `2024-11-05` and reads stdin without waiting
     for a full buffer.
5. **Audit path unchanged.** Context bundles, selection receipts and exact replay remain the audit path. Their
   identities, schemas and policies do not change. `context` may now resolve names and select documents automatically.
6. **Parser worker limits.** On Linux the worker limits `RLIMIT_DATA` (heap) instead of `RLIMIT_AS` and runs BLAS and
   OpenMP single-threaded. Other platforms keep `RLIMIT_AS`.

## Consequences

- Measured on the same MCP tasks, the agent path used 16–34 percent of the tokens of the F009 path: about 3,000 instead
  of 9,000–19,000 tokens per task, counting the tool listing on every turn. The listing itself is 819 instead of 1,376
  tokens. The tasks and procedure are recorded in the F040 implementation notes. This is a token measurement, not a
  human-value or answer-quality claim.
- Verification cost is part of every measurement. Text sources verify in milliseconds. A rendered document costs one
  re-render per process: about 1.2 s extra per CLI call for DOCX/PPTX (loading `docling-core` plus rendering), and once
  per document for the long-running MCP server.
- Negative verification results rest on the index being complete. Positive results never do.
- Clients that call the nine F009 tools must pass `--tools legacy` or `--tools full` and read results from `content`.
- Schemas, persisted identifiers, catalog tables and default dependencies are unchanged. The catalog gains one narrow
  read-only query for the accepted native object. The agent cache can be deleted at any time.

## Alternatives considered

- Serve text from the index: rejected by ADR 0009.
- Verify through the complete rich evidence bundle on every call: rejected after measuring 4–5 s per CLI call, because
  the agent text derives only from the native object.
- Store rendered texts in CAS and keep the binding in the index: rejected, because the binding would be no more
  trustworthy than the index.
- Record the binding as a catalog derivation: deferred. It would remove the per-process re-render but needs a contract
  and a migration.
- Adopt the official MCP SDK: deferred to avoid a new dependency tree while the stdlib server passes the official client.
- Embedding-based `find`: not needed for this workflow. Optional semantic retrieval remains separate (ADR 0019).
