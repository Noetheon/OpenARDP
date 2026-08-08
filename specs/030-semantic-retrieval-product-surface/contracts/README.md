# F030 product-surface contracts

## CLI

`openardp context` adds:

- `--retrieval-profile lexical|semantic` (omitted means lexical for new compilation);
- `--semantic-bundle PATH`;
- `--semantic-source-lock PATH`.

Bundle and source lock are an all-or-none pair and are required for semantic compile/replay. Semantic-only options with a
lexical profile are rejected. Replay with no explicit profile infers lexical versus semantic from the verified receipt;
semantic replay still requires the exact local capability and rejects algorithm drift.

`openardp mcp` accepts the same two local startup paths as an all-or-none pair. They are server configuration, never MCP
tool input.

## MCP 0.2.0

`compile_context` adds one optional input:

```json
{"retrieval_profile":{"enum":["lexical","semantic"],"type":"string"}}
```

Omission means lexical. A semantic request against a provider-free server yields the stable `invalid_params` category;
it never falls back. No MCP input accepts a path, model identity, provider policy, resource override or executable value.

## Benchmark v0.1.0

The result directory contains only the frozen protocol, two raw body-free observations, summary, decision, manifest and
human report. The standard-library validator rejects unknown/missing files, identity drift, non-canonical JSON,
privacy-forbidden keys and incorrect aggregation or decisions.
