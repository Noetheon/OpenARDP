# Contract: MCP Error Envelope 1 Experimental

## Status

`mcp_error_version: 1` is the versioned failure taxonomy of the experimental
`MCP interface 0.1.0`. It ships as reviewed documentation plus fixture-pinned
error transcripts. It reuses the CLI exit-classification semantics so identical
failures read identically on both interfaces.

## Shape

```json
{
  "jsonrpc": "2.0",
  "id": "<echoed request id>",
  "error": {
    "code": -32000,
    "message": "fixed body-free text",
    "data": {
      "mcp_error_version": 1,
      "category": "not_found"
    }
  }
}
```

Rules:

- `message` is a fixed constant per category; client-supplied values never appear.
- `data.category` is the stable machine code clients match on; JSON-RPC `code` is a
  compatibility mapping, not the primary signal.
- No traceback, filesystem path, document body, query/task text, configuration value
  or offending input value appears in any field.

## Taxonomy

| Category | JSON-RPC code | Raised when |
|---|---:|---|
| `invalid_request` | -32600 | line not one JSON object, batch array, missing/invalid envelope fields, second `initialize`, tool call before initialization or pending-frame overflow |
| `invalid_request` | -32601 | unknown method |
| `invalid_request` | -32602 | malformed `tools/call` envelope shape |
| `unsupported_protocol_version` | -32602 | client protocol revision differs from `2025-06-18` |
| `unknown_tool` | -32602 | tool name outside the fixed set |
| `invalid_params` | -32602 | input fails bounded domain validation, or the bounded result would exceed the response cap |
| `not_found` | -32000 | any unknown, malformed-after-validation or non-existent document, block, projection or receipt identifier |
| `conflict` | -32001 | ambiguous identifier, busy state, configuration mismatch |
| `integrity_or_workspace` | -32002 | catalog/CAS/verification drift, index drift, workspace incompatible/corrupt/locked |
| `cancelled` | -32003 | `notifications/cancelled` observed at a bounded checkpoint |
| `deadline_exceeded` | -32004 | per-request deadline elapsed |
| `internal` | -32603 | sanitized fallback for any unclassified failure |

## Enumeration resistance

All identifier lookup failures produce the identical `not_found` envelope regardless
of whether the identifier is malformed-but-parseable, unknown, historically removed
or near-miss. Response size and message are constant; no existence, catalog or path
detail is disclosed.

## Service mapping

| Service/port exception family | Category |
|---|---|
| `_UsageError`-family validation, `SearchQueryRejected`, limit rejection | `invalid_params` |
| `DocumentNotFound`, `RepresentationNotFound`, `BlockNotFound`, `ContextNotFound` | `not_found` |
| `AmbiguousBlock`, representation conflicts, `ContextConfigurationMismatch` | `conflict` |
| `RepresentationIntegrityError`, `SearchIndex*`, `ObjectStoreError`, `CatalogError`, `WorkspaceError`, `ContextIntegrityFailure` | `integrity_or_workspace` |
| `ContextCompilationCancelled` | `cancelled` |
| deadline checkpoint elapsed | `deadline_exceeded` |
| anything else | `internal` |

## Privacy

Error envelopes, audit records and default logs contain identifiers, digests, codes
and timings only. Reviewed scans must find zero occurrences of query text, task text,
evidence bodies and source paths.

## Compatibility

The taxonomy is additive and versioned independently. Changing a category, mapping or
message requires a new `mcp_error_version` with migration notes and updated fixtures;
the frozen persisted contracts are unaffected.
