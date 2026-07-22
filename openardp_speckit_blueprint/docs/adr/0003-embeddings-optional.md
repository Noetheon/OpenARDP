# ADR 0003: Embeddings are optional derived caches

Status: Accepted for blueprint

## Decision

The core requires lexical search and structural navigation. Embeddings are optional, namespaced by provider/model/profile
and disposable.

## Rationale

Embeddings are not portable universal meaning, may leak sensitive semantics, add compute/cost and can become stale when
models change. Exact identifiers/numbers are often served better by lexical/structured retrieval.

## Consequences

- MVP remains offline and lightweight.
- Semantic search quality can be added without changing canonical data.
