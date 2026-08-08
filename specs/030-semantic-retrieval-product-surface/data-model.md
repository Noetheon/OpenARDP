# Data Model: Semantic Retrieval Product Surface

F030 adds no persisted product entity or public evidence schema. The following interface-local concepts govern
composition and operational evidence.

## RetrievalProfile

- Values: `lexical`, `semantic`.
- Default: `lexical` when omitted for a new compile or MCP request.
- Replay: inferred from the persisted algorithm when omitted; an explicit value must agree.
- Identity: the profile itself is not persisted separately. The receipt's existing algorithm identity remains
  authoritative.

## SemanticCapability

- Optional process-owned capability containing one `SemanticRetrievalProvider`.
- Constructed only from an explicit verified bundle/source-lock pair.
- State: `absent` → `verified/lazy` → `worker-ready` → `closed`.
- The worker may retain disposable passage vectors only between requests in the same process.
- No path or provider object crosses into domain, catalog, CAS, receipt or MCP request data.

## SemanticSurfaceObservation

Body-free benchmark observation with:

- run identifier and exact protocol/corpus/provider recipe identities;
- bundle verification duration and exact asset bytes/file count;
- cold and warm compilation wall time;
- request, passage, cache-hit and peak-worker-RSS counters;
- receipt/selection projection digests rather than tasks, paths or evidence bodies;
- platform facts limited to declared OS, architecture and Python/runtime versions.

## SemanticSurfaceDecision

- `SEMANTIC_SURFACE_READY`: identity/privacy/determinism gates pass, cache reuse is at least 90%, warm time does not exceed
  cold time and peak worker RSS is no greater than 1.5 GiB.
- `SEMANTIC_SURFACE_NOT_READY`: any required gate fails; unfavorable metrics remain published.

Timing and RSS are descriptive observations excluded from deterministic cross-run projection equality but included in
the complete result identity and independent validation.
