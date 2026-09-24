# F040 implementation notes — agent-ready document access

**Record type:** durable feature record (user-visible behavior, MCP contract, trust boundary). **Decision:**
[ADR 0020](../../docs/adr/0020-token-efficient-agent-access.md). **Contract:**
[MCP agent tools](contracts/mcp-agent-tools.md).

## What changed

| Area | Change |
|---|---|
| MCP transport | Reads with `read1` and answers each request immediately; negotiates four protocol revisions; `content` results, `isError` with hints, instructions, titles and annotations; interface 0.3.0. |
| MCP tools | Default `agent` set with five tools; `--tools legacy` or `full` keeps the nine F009 tools. |
| Agent layer | `domain/agent_text.py` and `domain/agent_query.py`: text structure, passages, query planning, quote matching. `services/agent_texts.py` and `services/agent_access.py`: build, verify, find, read, outline and verify. `adapters/agent_index.py`: FTS5 cache. `adapters/docling_markdown.py`: renderer. |
| Verification | Returned content is rebuilt from CAS and catalog facts once per representation and process, and index drift is healed. A narrow catalog query (`accepted_rich_native_object`) loads only the native object the text derives from. |
| CLI | `add`, `docs`, `find`, `read`, `toc`, `verify`, `agent-view` and `refresh`; one-line hints for classified failures (`cli_errors.py`); `context` resolves names and selects documents automatically. |
| Bulk preparation | `add` walks folders without following links, skips hidden files and the store, skips exact-current files through the HEAD freshness probe (hash comparison), reports missing paths as not found and continues after failures. |
| Parser worker | On Linux, `RLIMIT_DATA` replaces `RLIMIT_AS`; BLAS and OpenMP are single-threaded. |

No schema, persisted identifier, catalog table, migration or default dependency changed. `tests/fixtures/mcp/tools-list.json`
now pins the agent listing; `tools-list-0.2.0.json` preserves the previous listing.

## Root causes confirmed before fixing

- **MCP hang.** A live pipe received no reply within 8 s, and the reply arrived only after end of input:
  `BufferedReader.read(n)` waits for a full buffer.
- **Rejected clients.** `initialize` with `2025-03-26` or `2025-11-25` returned an error, because the server pinned
  `2025-06-18`.
- **Worker crash.** On a 4-core host the Docling worker failed at import under `RLIMIT_AS`. It passed with 2 cores or
  one BLAS thread. With `RLIMIT_DATA`, imports passed and a 5 GiB allocation was still refused.

## Measurements

The workspaces were 62 Markdown project documents (ADRs and `docs/`) and two NASA files from the redistributable
real-world corpus (DOCX, 453 lines; PPTX, 13 slides). Measurements ran on a 4-core cloud container (Xeon 2.1 GHz),
Python 3.12. Tokens are characters divided by four, the same estimator the tools report.

**Tokens per task over MCP.** The same client and questions were used for both tool sets. Each call is one turn that
carries the tool listing.

| Task | Legacy path (list, search with retries, 2× get_block, compile_context) | Agent path (find, read, verify_quote) | Share |
|---|---:|---:|---:|
| Which decision makes indexes non-authoritative, and what must be verified? | 19,070 | 3,108 | 16% |
| Why are embeddings optional? | 17,639 | 2,946 | 17% |
| What role does AI play in the data life cycle? (PPTX) | 9,025 | 3,075 | 34% |

- The tool listing is 819 tokens for the agent set, 1,376 for the legacy set and 2,102 for the full set.
- The legacy `list_documents` alone cost 9,027 tokens for 65 documents.
- Legacy lexical search found nothing for the natural-language PPTX question.
- In all three tasks the agent path placed the correct passage first: ADR 0009 Decision, ADR 0003 Decision and slide 3.
- The German question "Warum sind Embeddings optional?" returns the same top hit.
- A German question over English documents finds nothing lexically and prints a hint to use the document's language.

**Latency.**

| Operation | Result |
|---|---|
| MCP `find` over 62 Markdown documents, warm | 54–91 ms |
| MCP `read` | 4–7 ms |
| MCP `verify_quote` | 77–249 ms |
| First MCP `find` touching DOCX/PPTX, including verification rebuild | 1.1 s |
| CLI `docs` | 0.7 s |
| CLI `find` or `read` touching DOCX/PPTX | 1.9–2.1 s (4.9 s before the narrow native-object query) |
| `add`, 62 unchanged files | 0.2 s inside the command, 1.0 s for the process (3.8 s before the freshness probe) |
| `agent-view`, 62 documents | 0.9 s; `INDEX.md` is 20.8 KB, down from 28.4 KB after printing the shared source folder once |

**Official client.** The official MCP Python SDK client 2.2.0, run outside the project environment, connected over
stdio in 0.68 s:

- negotiated `2025-11-25` and received the instructions;
- listed five tools, all with `readOnlyHint: true`;
- called `find`, `outline` and `verify_quote` successfully;
- received a correct `isError` result for an unknown document.

The token counts are a measurement of agent-visible context on these tasks, not a claim about answer quality, human
time or other corpora.

## Tests added

- **Domain:** text structure, passages, query planning and quote matching.
- **Index:** round trip, filters, format reset and corruption recovery.
- **Access (integration):** refresh, freshness, references, ranking, read ranges, outline and verification, including
  versions. Tamper tests show that a forged index text or passage is not returned and is healed, that an invented quote
  in the index does not verify and that a forged path is replaced from the catalog.
- **Rich documents:** DOCX/PPTX rendering, projection fallback and the narrow native-object query, including an
  inconsistent catalog row.
- **CLI:** human and JSON output, hints and exit codes.
- **Bulk preparation:** discovery rules, symbolic links, the file cap and prior-state classification.
- **Agent view:** naming, idempotence, protection of foreign files and the index source column.
- **MCP:** tool sets, negotiation, `isError` mapping, audit outcome, semantic state eviction and a subprocess pipe
  test that fails if a reply waits for end of input.
- **Parser worker:** thread environment and memory-limit resource selection.

## Validation

Exact commands and results for the final tree are listed in the [F041 notes](../041-lean-governance/implementation-notes.md#validation),
because both features were validated together in one run.

## Tradeoffs and residual risks

- **Latency.** Verifying rendered documents costs about 1.2 s per CLI call, from loading `docling-core` and
  re-rendering. The long-running MCP server pays it once per document. Recording the renderer output as a catalog
  derivation would remove the cost but needs a contract and a migration (deferred in ADR 0020).
- **Negative results.** A "not found" answer depends on the index being complete; positive answers never do.
- **Rendering loss.** Markdown from Docling loses layout, images and some table structure. Scanned pages without a
  text layer have no text.
- **Retrieval limits.** `find` is lexical with light stemming. Cross-language questions and paraphrases can miss;
  optional semantic retrieval (F029/F030) is not wired into `find`.
- **Mixed file versions.** Line numbers of rendered documents refer to the agent text, not the original file. Page and
  slide markers are the stable citation.
- **Protocol coverage.** The stateless `2026-07-28` revision is not implemented; such clients fall back to
  `initialize`.

## Rollback

- Revert the feature commit.
- The agent cache (`<store>/agent-cache/`) can be deleted; nothing else in a workspace depends on it.
- Clients can keep the F009 tools with `openardp mcp --tools legacy`.
- Workspaces created or updated by this version remain readable by the previous version, because no catalog or CAS
  format changed.
