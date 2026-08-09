# Profiled Retrieval Evidence Contract

The normative benchmark profile is `benchmarks/profiled-retrieval/v0.1.0/protocol.json`. Published evidence contains:

- `observations.json`: body-free per-query baseline/candidate quality, timing and exact algorithm identity;
- `phases.json`: setup and query phase durations/counters with parent reconciliation keys;
- `summary.json`: independently recomputable quality totals and p50/p95 paired ratios;
- `decision.json`: separate `validity`, `development_candidate` and `holdout_generalization` verdicts;
- `run-manifest.json`: exact inputs, provider/bundle/profile identities, counterbalanced order, file digests and run identity;
- `report.md`: human-readable projection of the same facts.

The producer writes into a private staging directory and publishes the directory atomically with the manifest last. The
validator rejects duplicate JSON members, extra files, symlinks, path disclosure, body/question fields, unknown phases,
negative or unreconciled durations, identity drift, missing paired runs, threshold overrides and result-led F034 changes.

The prepared-provider contract is optional. `prepare` accepts already verified passages and returns a deterministic,
process-local handle. `score_prepared` accepts only a query, that handle and existing resource/cancellation limits. It must
return exactly one fixed-point score for every prepared evidence/object identity. Unknown, stale or recipe-mismatched
handles fail closed. `close`, timeout or worker failure invalidates every handle and deletes all embeddings.

The prepared lexical accelerator is likewise optional and process-local. It binds one exact snapshot and compile limits,
stores at most 64 MiB of verified rich retrieval text, recomputes lexical/relevance observations per query and rehashes
every returned match. Current catalog authority is the SHA-256 digest of the accepted attempt plus ordered
reference/projection/retrieval object mappings. Drift invalidates the cache. Selected bodies are independently verified
again by the compiler.

For prepared `1.3.0`, additive canonical-prefix budgeting must produce byte-identical bundles and receipts to historical
full-reserialization measurement for every built-in estimator. The manifest binds both counterbalanced F025 provider
recipes and both F034 provider recipes, all provider metrics, exact algorithm identities and every result-file digest.
