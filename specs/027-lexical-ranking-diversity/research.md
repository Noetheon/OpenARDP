# Research: F027

## Binding baseline

F025 corpus, question, protocol and oracle identities are unchanged. F026 is the paired control; Q02, Q03, Q06, Q13,
Q14 and Q19 are the frozen positive slice, while Q17 and Q18 are unsupported. Both algorithms run against the same
freshly ingested workspace in each repetition so ingestion variance cannot favor either profile.

## Decisions

1. Use exact lexical F026 observations, not BM25, because the verified candidate bodies and bounded integer facts already
   exist and an index score must not become evidence authority.
2. Use document-scope round-robin instead of maximal-marginal-relevance: it is explainable, provider-free and does not
   require an arbitrary similarity metric.
3. Use a hard quota of 16 per document. It equals the current default item budget, prevents one source from monopolizing
   larger requests and remains harmless where only one document is relevant.
4. Preserve a four-item global ranked prefix before round-robin allocation. The second diagnostic run proved that
   immediate interleaving preserved support and improved precision but moved an otherwise rank-2 answer to rank 4 and
   regressed paired MRR. A small declared prefix preserves early answer quality while the remaining allocation still
   diversifies and enforces quotas.
5. Deduplicate only exact CAS body identities. Approximate dedupe risks discarding distinct evidence and belongs outside
   this deterministic slice.
6. Preserve the established lexical coverage/occurrence hierarchy and use normalized F026 relevance to break ties. The
   first diagnostic run proved that ratio-first ordering penalized a focused answer block matching 3 of 9 task signals:
   it fell from rank 2 to rank 164 and was then correctly, but harmfully, removed by the quota. The revised general rule
   retains lexical answer density while still improving deterministic ties; no benchmark identifier enters runtime.

## Rejected alternatives

- Random shuffling: non-reproducible and not relevance-aware.
- Per-representation quotas: one document could still monopolize context through multiple projections.
- Guaranteed source count: would inject weak evidence and invalidate abstention.
- Benchmark-tuned question weights: leaks evaluation data into runtime.
