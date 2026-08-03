# Lexical Ranking, Diversity and Source Quotas

Feature 027 adds a provider-free allocation stage after F026 freshness, trust and relevance classification and before
the existing context budgeter. It is disposable retrieval policy: originals, verified evidence, provenance and content
identities remain authoritative and unchanged.

## Behavior

- Eligible candidates retain the proven representation, lexical term-coverage and occurrence hierarchy; normalized
  F026 score, matched weight and matched signals deterministically break ties.
- Later candidates referring to an already retained exact CAS body are rejected as
  `duplicate_content_candidate`.
- The first four globally ranked candidates preserve early answer quality. Remaining candidates are grouped by document
  version and fairly interleaved one per queue per round.
- A document version contributes at most 16 candidates; eligible tails are audited as `source_quota_exceeded`.
- Diversity never reserves empty slots, admits below-floor evidence or changes trust/integrity precedence.
- New CLI compilations use the combined F026+F027 identity. Replay detects and composes legacy, F026-only or F027
  profiles from the recorded algorithm identity and fails closed for any other mismatch.

## Binding paired result

The reference result under `benchmarks/ranking/v0.1.0/results/reference-macos-arm64/` runs the F026 control and F027
treatment over each of two freshly ingested workspaces using unchanged F025 corpus, question and protocol identities.
The stdlib-only validator returns `LEXICAL_RANKING_READY` with result ID
`sha256:a622eceb35a99838bfb1e23e7f05f9af3a2ef48bcdc8dbbb82234ad67c693cfd`.

| Direct positive metric | F026 | F027 | Outcome |
|---|---:|---:|---|
| Evidence precision | 0.050847 | 0.068182 | improved by 34.1% relative |
| Mean reciprocal rank | 0.638889 | 0.638889 | unchanged |
| Source recall | 1.000000 | 1.000000 | unchanged |

All six frozen positive questions retain full support and citation integrity. Q17/Q18 still abstain with zero selected
evidence. Q03 falls from 64 to 34 selected items: three eligible documents contribute 16, 16 and 2 items, while 121
over-quota and 9 exact-body duplicate candidates are explicitly audited. Both fresh semantic projections are identical.

## Diagnostic revisions and limits

The first measured policy ranked normalized relevance ratio first. It improved MRR but pushed a focused answer block that
matched 3 of 9 long-question signals from rank 2 to rank 164 and then beyond the quota. The second policy restored lexical
strength but immediate round-robin moved early answers and regressed MRR. The accepted policy therefore freezes a
four-item ranked prefix before fair interleaving. These unfavorable intermediate results informed the general algorithm;
no question identifier, answer or expected source is available to runtime code.

The eight-question slice is not population-wide retrieval evidence. Precision remains low in absolute terms because F026
admits many lexically related but non-supporting blocks, and exact lexical retrieval still cannot solve paraphrase or
cross-language gaps. F028 owns stable CSV ingestion; F029 owns optional provider-neutral semantic/multilingual evaluation.

## Reproduction

```bash
uv run python scripts/run_ranking_benchmark.py \
  --pdf-bundle /Users/Shared/openardp-pdf-bundle-2.114.0-v1-measured \
  --output /Users/Shared/openardp-f027-result
uv run python scripts/validate_ranking_benchmark.py \
  --result /Users/Shared/openardp-f027-result
```
