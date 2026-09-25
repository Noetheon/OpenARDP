# Contract: MCP agent tools — interface 0.3.0 (experimental)

## Status

This contract defines `MCP interface 0.3.0`. It is experimental application behavior that the tests and
`tests/fixtures/mcp/tools-list.json` pin down. It adds no JSON Schema under `schemas/` and no workspace migration.
The [F009 tool contract](../../009-read-only-mcp/contracts/mcp-read-only-tools.md) still describes the nine legacy tools,
except for the result wrapping described below. The
[F009 error envelope](../../009-read-only-mcp/contracts/mcp-error-envelope.md) still defines the error taxonomy.
`tests/fixtures/mcp/tools-list-0.2.0.json` keeps the previous legacy listing for comparison.

## Transport and lifecycle

- stdio, newline-delimited UTF-8 JSON-RPC 2.0, one object per line, inbound lines bounded at 64 KiB. The server reads
  whatever input is available and answers each request immediately. It exits cleanly at end of input.
- `initialize` answers with the client's `protocolVersion` if it is one of `2025-11-25`, `2025-06-18`, `2025-03-26` or
  `2024-11-05`, and with `2025-11-25` otherwise. A missing, non-string or longer than 64-character version is an
  invalid request.
- The result carries `capabilities: {"tools": {"listChanged": false}}`, `serverInfo` and, for the `agent` and `full`
  tool sets, `instructions`.
- Tool calls are accepted after the `initialize` response, even before `notifications/initialized`.
- Unknown methods, including the stateless `server/discover`, return JSON-RPC `-32601`, so dual-era clients fall back to
  `initialize`.

## Tool sets

`openardp mcp --store PATH [--tools agent|full|legacy]` (default `agent`):

| Tool set | Tools |
|---|---|
| `agent` | `list_documents`, `find`, `read`, `outline`, `verify_quote` |
| `legacy` | the nine F009 tools |
| `full` | the five agent tools, then the legacy tools except the duplicate `list_documents` (13 tools) |

Every listed tool has `name`, `title` (agent tools), `description`, `inputSchema` (JSON Schema 2020-12 object with
`additionalProperties: false`) and `annotations`: `readOnlyHint: true`, `destructiveHint: false`,
`idempotentHint: true` and `openWorldHint: false`.

## Agent tools

A document reference is a file name, a path suffix, a unique part of the name, the full id or a hex suffix of the id of
at least six characters (the 8-character short id shown in results). An ambiguous reference fails and lists the
candidates.

| Tool | Arguments | Bounds |
|---|---|---|
| `list_documents` | none | up to 1,000 documents plus pending sources |
| `find` | `query` (required, 1–1,000 characters, may be multi-line), `document`, `limit` | `limit` 1–20, default 8; at most three hits per document before others are shown |
| `read` | `document` (required), one of `page`, `lines` or `section`, and `max_tokens` | `max_tokens` 50–20,000, default 2,000 |
| `outline` | `document` (required) | up to 200 entries |
| `verify_quote` | `quote` (required, up to 4,000 characters, may be multi-line), `document`, `version` | `version` is a `sha256:` id or a hex prefix of at least 8 characters |

For `read`:

- `page` is `3`, `3-5` or `3-` (page or slide numbers).
- `lines` is `120`, `120-180` or `120-`. A single number reads from that line on.
- `section` is a heading text, matched exactly first and then as a substring.

## Result format

A successful result is `{"content": [{"type": "text", "text": ...}], "isError": false}` holding compact text. Legacy
tools return their unchanged JSON value serialized as canonical text in the same envelope. Text is untrusted document
data, and the instructions say so. Examples from a synthetic Markdown file:

```text
find → 1 of 1 matching passages for heavy*, referenc*, weight*:
       1. guide.md:5-6 [1c1cfded] ≈25 tok — § Field guide > Calibration
          Calibrate the sensor every morning before the first measurement. The reference weight is 500 grams.
       Next: read a hit's lines or page for full text; verify quotes before citing.

read → guide.md · lines 3-6 of 10 · ≈29 tokens · version ac128907
       (a fenced block of tab-numbered lines, then a continuation line if truncated)

outline → guide.md — md, 10 lines, ≈51 tokens, version ac128907
          L1 # Field guide (≈51)
          L3 ## Calibration (≈29)

verify_quote → VERIFIED (exact): guide.md:6 — version ac128907, source file unchanged.
```

Rich documents are cited as `file p.N (Lx-y)` or `file slide N (Lx-y)`. Line numbers refer to the agent text, which for
TXT, Markdown and CSV is the source file itself. Results name the short version id and report a source file that
changed or disappeared since it was imported.

`verify_quote` returns one of three results:

- `VERIFIED (exact|normalized)` with the location;
- `OUTDATED` when the quote is only in the cited earlier version;
- `NOT FOUND` with the closest passage and its similarity.

## Errors

A correctable tool failure is a successful JSON-RPC response carrying an `isError: true` result:

```json
{
  "content": [{"type": "text", "text": "Error: <category message>. <corrective hint>"}],
  "isError": true,
  "_meta": {"openardp/error": {"code": -32000, "message": "requested evidence was not found",
            "data": {"mcp_error_version": 1, "category": "not_found"}}}
}
```

The categories are invalid parameters, not found, conflict (including an ambiguous reference or an index that is
still warming up) and integrity or workspace. Protocol failures, cancellation and deadline expiry remain JSON-RPC
errors with the F009 envelope. Messages never contain document text, paths or stack traces.

## Integrity rules

- The agent index under `agent-cache/` only locates passages.
- Returned text, snippets, headings, pages, paths and versions come from a copy rebuilt from CAS and catalog facts,
  once per representation and server process.
- A disagreeing index entry is replaced before anything is returned.
- A positive verification is always confirmed against that verified copy.
