# ADR 0002: SQLite catalog and filesystem CAS for the MVP

Status: Proposed

## Decision

Use SQLite (including FTS5) for metadata/search and a SHA-256 content-addressed filesystem object store for large artifacts.

## Rationale

Local-first, portable, transactional, low operational overhead and sufficient for the target benchmark. It avoids forcing
Docker, PostgreSQL or a vector database on initial users.

## Consequences

- Single-node write scaling only.
- Enterprise migration requires ports and data migration tooling.
- Keep SQL/catalog concerns behind interfaces.
