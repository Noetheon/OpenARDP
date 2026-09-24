# F040 — Agent-ready document access

**Status:** Implemented; validation results in [implementation notes](implementation-notes.md)
**Created:** 2026-09-24
**Decision record:** [ADR 0020](../../docs/adr/0020-token-efficient-agent-access.md)
**Contract:** [MCP agent tools](contracts/mcp-agent-tools.md) (MCP interface 0.3.0)
**Supersedes in part:** [F009 MCP tool surface](../009-read-only-mcp/contracts/mcp-read-only-tools.md) as the default
server tool set, and the [F038 pilot](../038-local-document-pilot-readiness/spec.md) as a precondition for further work
([F041](../041-lean-governance/spec.md))

## Task served

An agent such as Claude Code, Codex or another MCP client, working for a person with a folder of PDFs, Office files and
notes, needs to answer a question from those files. It must find the right passage, read only the part it needs and
quote it correctly with file, page and line, without spending its context window on listings, hashes and JSON
envelopes.

Improvement is observed as:

- fewer agent-visible tokens per answered question;
- a real MCP client that connects and works;
- quotes that are checked against the exact source version.

## Problems addressed

1. Real MCP clients hung or were rejected: stdin blocked until EOF, one protocol revision was pinned and results were
   not in `content` blocks.
2. The F009 tools needed UUIDs, and a mandatory listing cost about 9,000 tokens for 65 documents.
3. There was no find → read range → verify quote path and no page, slide or line locations for rich documents.
4. The Docling worker crashed on multi-core Linux (`RLIMIT_AS` against thread and CUDA address-space reservation).
5. Adding documents meant one `ingest` call per file, after a separate `init`.

## Acceptance criteria

1. **Connection:** the official MCP Python client connects over stdio, negotiates `2025-11-25`, lists tools and calls
   each agent tool. Responses arrive while stdin stays open. Offered revisions `2025-06-18`, `2025-03-26` and
   `2024-11-05` are accepted, and an unknown revision negotiates the latest.
2. **Tool set:** by default, `openardp mcp` offers five read-only tools with titles, annotations and server
   instructions: `list_documents`, `find`, `read`, `outline` and `verify_quote`. `--tools legacy|full` keeps the F009
   tools. Correctable failures are `isError` results with a hint, and the error taxonomy is in `_meta`.
3. **Find:** `find` accepts a question or keywords in English or German. It returns ranked passages from all prepared
   documents with file, page or slide, line range, heading path and a short snippet, at most three per document before
   others are shown.
4. **Read:** `read` selects by page or slide, line range or section heading. It is bounded by `max_tokens`, has
   numbered lines and reports where to continue.
5. **Verify:** `verify_quote` confirms a quote exactly or after normalizing whitespace, quote marks, dashes, markup and
   case, including `...` gaps. It reports the location and exact version, reports a quote that exists only in another
   cited version as outdated, and otherwise returns the closest passage.
6. **Integrity:** returned text never comes from the index alone (ADR 0009 and ADR 0020). A modified index cannot
   change returned text or make an invented quote verify, and it is repaired automatically. Changed or missing source
   files are reported.
7. **CLI:**
   - `add` accepts files and folders, initializes a missing workspace, skips unchanged files and reports added, updated,
     unchanged, failed and skipped files with a hint per failure.
   - `docs`, `find`, `read`, `toc`, `verify`, `refresh` and `agent-view` print compact text, or the standard JSON
     envelope with `--json`.
   - Errors print a one-line hint.
8. **Portable view:** `agent-view DIR` writes Markdown copies and an `INDEX.md` with outlines and token sizes for
   agents without MCP. It never overwrites or deletes files it did not write.
9. **Audit path:** `context` accepts document names or none (automatic selection). Bundle, receipt and replay
   semantics are unchanged.
10. **Parser worker:** rich parsing works on multi-core Linux hosts, with memory still bounded (`RLIMIT_DATA` on Linux,
    single-threaded BLAS and OpenMP).
11. **Quality gates:** all repository gates pass without new default dependencies, schema changes or catalog
    migrations.

## Decisions

- Agent texts are disposable derived views (exact source text, or `docling-core` Markdown from the retained native
  artifact) in a separate agent cache. They are never evidence authority and never a second complete document model.
- The index locates. Returned content is rebuilt from CAS and catalog facts once per representation and process.
- The MCP server stays stdlib-only. The default tool set changes to `agent`, and the F009 tools remain opt-in.
- Tokens are estimated as characters divided by four. Measurements report agent-visible tokens, including the tool
  listing on every turn.

## Out of scope

Answer generation, embeddings in `find`, new providers or cloud calls, MCP resources and prompts, the stateless
`2026-07-28` protocol revision and write tools.
