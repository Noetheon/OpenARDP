# Feature 009 — Read-only MCP

## Goal
Expose prepared evidence via object-scoped, least-privilege MCP tools.

## Tools
List sources, source status, search evidence, get evidence/outline, compile context and verify evidence.

## Constraints
Configured workspace only; no arbitrary paths, ingestion, deletion or mutation. Bounded pagination/output, stable versioned errors, cancellation/deadlines, per-request limits and local single-user boundary are explicit. MCP is transport only. Returned text is labelled and delimited untrusted content. Tests are offline and include confused-deputy/path/ID-enumeration cases.
