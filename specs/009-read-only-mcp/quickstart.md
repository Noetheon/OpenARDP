# Quickstart: Read-only MCP

## Install and prepare a workspace

```bash
uv sync --all-extras --locked
uv run --locked openardp init --store .openardp --json
uv run --locked openardp ingest notes.md --store .openardp --json
uv run --locked openardp ingest report.docx --store .openardp --json
uv run --locked openardp list --store .openardp --json
```

Capture the document IDs from the body-free list result.

## Start the MCP server

```bash
uv run --locked openardp mcp --store .openardp
```

The server speaks newline-delimited JSON-RPC 2.0 on stdin/stdout, pinned to MCP
protocol revision `2025-06-18`. It opens no network listener and exits on stdin EOF.

## Handshake and discovery

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"example","version":"0"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
```

`tools/list` returns the nine read-only tools in fixed order with closed input
schemas, output bounds and the untrusted-data notice.

## Navigate evidence

```json
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_documents","arguments":{}}}
{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"get_document_outline","arguments":{"document_id":"DOCUMENT_ID"}}}
{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"get_block","arguments":{"block_id":"BLOCK_ID"}}}
```

Block text arrives inside the `openardp-evidence-v1` untrusted-data envelope, never
as bare text.

## Search and compile

```json
{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"search_document","arguments":{"query":"\"exact controls\"","limit":20}}}
{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"compile_context","arguments":{"task":"Which exact controls are documented?","document_ids":["DOCUMENT_ID_1","DOCUMENT_ID_2"],"budget_limit":12000,"unit":"tokens","mode":"verification"}}}
```

Expected compile result:

- one receipt ID and one bundle ID;
- exact sorted scopes, decision counts and budget accounting;
- no evidence body by default (`include_bundle` is an explicit bounded opt-in);
- any visual need reported as an explicit escalation notice, never invented detail.

```json
{"jsonrpc":"2.0","id":8,"method":"tools/call","params":{"name":"get_context_receipt","arguments":{"receipt_id":"sha256:RECEIPT_HEX"}}}
```

The receipt is returned only after complete verification.

## Boundary behavior to expect

- Any parameter containing a path, traversal, URL or shell fragment fails with
  `invalid_params` or `not_found` and causes no file access.
- Unknown identifiers of any kind return one uniform `not_found` envelope.
- Errors carry `data.category` from `mcp_error_version: 1` with fixed body-free
  messages.
- A request runs at most 30 seconds by default; `notifications/cancelled` stops a
  running compilation without a partial result.
- At most 64 non-cancellation frames wait for sequential dispatch; overflow unwinds
  active work and closes the bounded session instead of growing memory.

## Required local validation

```bash
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy src
uv run --locked mypy src --platform win32
uv run --locked pytest
uv run --locked python scripts/generate_schemas.py --check
uv run --locked python scripts/validate_evidence_contracts.py \
  conformance/evidence/v0.1.0/manifest.json
uv run --locked python scripts/validate_repository.py
git diff --check
uv build
```

The implementation notes record exact counts, frozen hashes, transcript fixtures,
tradeoffs, rollback and remote Linux/macOS/Windows evidence.
