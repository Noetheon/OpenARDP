# ADR 0004: Read-only MCP first

Status: Accepted for blueprint

## Decision

Initial MCP tools only retrieve documents, evidence and context bundles. They do not modify files or invoke external side
effects.

## Rationale

Documents are untrusted inputs and indirect prompt injection is a core risk. Read-only tools sharply reduce authority while
the retrieval model is validated.

## Consequences

- Authoring/publishing is a separate later surface.
- Safety testing is simpler and more meaningful.
