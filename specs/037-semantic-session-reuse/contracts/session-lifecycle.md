# Internal Semantic Session Lifecycle

This is a private lifecycle constraint, not a new interoperability contract.

1. One MCP server retains at most one semantic compiler, keyed by complete estimator identity. Lexical requests do not consume or invalidate it.
2. Repeated compatible semantic requests may reuse prepared state. Current catalog snapshots, request policies, limits and CAS delivery verification remain mandatory.
3. Any failed semantic compilation drops the server slot. A subsequent request starts fresh; no automatic retry conceals failures.
4. Worker `prepare` and direct `score` validate count/byte bounds and object/body consistency before changing caches. They retain only requested unique object vectors. Equal objects can support distinct evidence IDs.
5. Successful `prepare` replaces all previous prepared handles and binds exact retrieval limits. `score_prepared` rejects an evicted ID or different limits. Direct `score` invalidates prepared handles. An evicted deterministic corpus ID may become active again only after successful re-preparation of identical contents and limits (A-B-A); no new identity algorithm is introduced.
6. Worker failures may discard all disposable state. Public outputs, source identities and stored evidence remain unchanged.
