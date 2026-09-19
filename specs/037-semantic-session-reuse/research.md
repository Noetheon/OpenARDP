# F037 Research and Decisions

1. The real stdio MCP path constructs a new semantic compiler on each `compile_context` request, discarding the candidate source's prepared corpus cache. Keep one compiler keyed by full estimator identity. A multi-estimator map would keep stale worker handles and adds unnecessary lifetime complexity.
2. The E5 worker currently counts historical entries against a new request and accumulates corpus handles. Retain only the requested unique object set and one handle; shared vectors survive a scope change. No LRU or disk cache is needed.
3. Object identity is authoritative content identity. Conflicting bodies for the same ID, including within a request, must fail before state mutation. Multiple evidence IDs may legitimately share one object/vector.
4. A prepared ID binds retrieval limits. Store and verify the exact original limits on prepared scoring; checking only passage count is insufficient.
5. Runtime/model failures already tear down the provider worker. Drop the MCP compiler slot too; the next request prepares fresh. No silent retry.
6. No scoring/ranking or frozen benchmark changes belong here. Relevance adjudication and actual user value are separate later work packages.

Clarification result: no unresolved implementation, compatibility or trust-boundary questions. User tasks are required only for the later pilot.
