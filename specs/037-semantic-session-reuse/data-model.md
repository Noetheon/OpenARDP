# F037 Data Model

All new state is private and disposable.

- Session slot: full immutable estimator identity plus one compiler instance. Empty -> ready on successful construction; changed identity replaces ready; any semantic compile exception -> empty.
- Passage cache: map object ID -> `(exact text, vector)`. A valid new request replaces its key set with that request's unique objects, retaining shared entries. Conflicting text is invalid. Bounds apply before mutation.
- Active corpus: one corpus ID -> ordered `(evidence ID, object ID)` pairs plus exact retrieval limits. Successful preparation replaces it. Direct scoring invalidates it. Prepared scoring rejects unknown/evicted IDs, changed limits or missing objects.

Persisted models and identifiers are unchanged. CAS/catalog remain authoritative at delivery.
