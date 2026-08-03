# Contract: lexical allocation v1

1. Input candidates have already passed freshness, trust, sensitivity and optional F026 relevance checks.
2. Rank by preferred representation, lexical term coverage and occurrences; then descending integer relevance score,
   matched weight, matched signal count and stable scope/source/evidence keys.
3. Retain the first candidate for each exact non-null CAS body object identity and reject later ones as
   `duplicate_content_candidate`.
4. Emit the first four globally ranked admitted candidates unchanged. Remove them from document queues, sort remaining
   queues by their first candidate rank and emit one candidate per nonempty queue per round.
5. Emit at most 16 candidates per document; reject the remainder as `source_quota_exceeded`.
6. The allocator is pure, deterministic, body-free and cannot change evidence, provenance or trust.
