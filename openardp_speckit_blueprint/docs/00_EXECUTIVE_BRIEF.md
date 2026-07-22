# Executive brief

## Vision

A person edits a Word document, PowerPoint or PDF as usual. A local watcher or enterprise connector notices the new
version. OpenARDP prepares the document in the background and stores a reusable representation. Later, Codex or another
agent asks for an outline, matching blocks, exact tables, selected images or an evidence bundle instead of reopening and
reprocessing the whole file.

## Core promise

- First use performs ingestion and enrichment.
- Repeated use of an unchanged file performs no parsing.
- Changed files create a new immutable version.
- Only affected derived artifacts are recomputed.
- Every returned item points back to its exact source location.
- The original can always be requested when interpretation is uncertain.

## Critical reality check

For some file formats, especially PDF, a parser may still need to examine the complete new version before it can know what
changed. The initial MVP therefore guarantees **cache reuse across identical versions** and **incremental downstream
recomputation**, not magical byte-level incremental PDF parsing. Native Open XML part hashing can later optimize DOCX/PPTX.

## Why this is not just another RAG project

Existing tools already parse documents, expose MCP conversion tools and perform hybrid retrieval. OpenARDP's unique scope is:

1. a portable and validated package contract;
2. durable document/version/block identity;
3. content-addressed original and derived artifacts;
4. explicit dependency and invalidation graphs;
5. source-versus-derived trust separation;
6. budget-aware, evidence-preserving context compilation;
7. automation from local save events to Microsoft 365 change streams;
8. reproducible evaluation of latency, cost, quality and security.

## Recommended first decision

Build a reference implementation **on top of Docling**, not a new parsing engine. Evaluate MinerU as an optional parser for
complex PDF workloads and MarkItDown as a lightweight fallback/export adapter.

## MVP definition of done

The MVP is complete when a clean machine can:

1. ingest a TXT/MD and a representative PDF/DOCX/PPTX through adapters;
2. skip unchanged files without invoking a parser;
3. create a new version for changed files;
4. preserve block-level source locations and original assets;
5. search exact text using SQLite FTS5;
6. compile a token-budgeted context bundle;
7. expose read-only MCP tools to Codex;
8. run a local watcher safely;
9. pass schema, security and adversarial document tests;
10. publish a reproducible benchmark comparing raw-file, text-only and OpenARDP workflows.
