# Research: Provider-Neutral Multilingual Retrieval

## Decisions

1. Use dense retrieval rather than a hand-written benchmark dictionary. A curated translation/synonym list would encode
   the answers and invalidate the comparison.
2. Use `multilingual-e5-small` because the upstream model card declares MIT licensing, 94-language support, 12 layers,
   384 dimensions and the exact asymmetric `query:`/`passage:` retrieval convention. The small profile is still about
   493 MiB for the minimal SafeTensors/tokenizer files, so it remains optional and external to Git.
3. Use Transformers directly rather than add SentenceTransformers. Mean pooling and L2 normalization follow the upstream
   example and reduce dependency surface. `trust_remote_code=False`, `local_files_only=True` and SafeTensors are fixed.
4. Keep passage vectors only in one persistent isolated worker. Re-embedding the corpus for every question would measure
   waste; persisting a vector index would require a broader cache lifecycle and catalog feature not needed for this
   bounded evaluation.
5. Quantize cosine similarity to signed millionths, then admit nonnegative scores at a pre-run `800000` floor. The model
   card warns that absolute E5 scores cluster high; therefore unsupported protection additionally requires every exact
   volatile-time signal from F026 to appear in the candidate. The binding run may honestly fail this frozen policy.
6. Reuse F027 allocation after semantic scoring. Similarity is not allowed to defeat exact deduplication, per-document
   quota or fair multi-source interleaving.
7. Evaluate all nineteen untouched direct questions. The comparison is diagnostic, not statistically representative and
   cannot support a universal semantic-quality claim.

## Rejected Alternatives

- Cloud embeddings: violate local-first defaults, add egress/privacy variability and recurring cost.
- Benchmark-frozen operator terms as provider output: circular and already measured as manual assistance.
- Persist raw vectors in SQLite or public contracts: unnecessary, provider-specific and outside this bounded feature.
- Use model scores as evidence truth: scores only rank verified evidence and never alter citations/source authority.
- Replace lexical retrieval: exact identifiers and resource-light default behavior remain valuable and proven.
