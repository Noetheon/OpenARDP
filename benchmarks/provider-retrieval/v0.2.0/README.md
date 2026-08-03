# Provider-Neutral Retrieval Benchmark v0.2.0

This protocol preserves every v0.1 input, model, score threshold and readiness gate. The immutable v0.1 binding result
remains as negative evidence. It showed that a semantic-only global Top-128 was dominated by the large CSV source before
F027 source quotas could run, even though the exact Q04 oracle evidence scored above the fixed threshold.

Before this second binding run, v0.2 freezes two structural corrections already required by the feature contract:

- minimum-relevant F027 lexical candidates are a higher-priority fallback tier, preventing exact identifier and direct
  retrieval regression;
- eligible semantic candidates receive a four-item ranked prefix, a maximum of 32 per document and deterministic fair
  document round-robin before the unchanged global Top-128.

No question, support atom, source judgment, model asset, score floor or output gate was changed. Results remain body-free,
offline, two-run and independently validated.
