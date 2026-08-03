# OpenARDP Provider-Neutral Retrieval Evaluation

**Decision:** `PROVIDER_RETRIEVAL_NOT_READY`

This frozen comparison runs the unchanged F025 questions directly against the F027
lexical profile and the explicit offline F029 multilingual provider. It evaluates
retrieved evidence and citations, not generated prose.

## Exact direct-treatment metrics

| Treatment | Full | Atoms | Sources | Precision | MRR | Citations | Abstain |
|---|---:|---:|---:|---:|---:|---:|---:|
| f027_lexical_direct | 0.411765 | 0.347826 | 0.444444 | 0.039855 | 0.333333 | 1.000000 | 1.000000 |
| f029_semantic_direct | 0.411765 | 0.347826 | 0.444444 | 0.058824 | 0.333333 | 1.000000 | 1.000000 |

## German cross-language questions

- Q04: atom recall 0.000000 -> 0.000000; full support 0.000000 -> 0.000000.
- Q08: atom recall 0.000000 -> 0.000000; full support 0.000000 -> 0.000000.

## Runtime boundary

- F027 summed query wall ns: 65933390334
- F029 summed query wall ns: 119014172292
- Provider requests: 19
- Passages scored: 32053
- Passage-cache hits: 30366
- Peak provider-worker RSS bytes: 1209548800
- Embeddings remained disposable worker memory and are absent from this result.
- Both unsupported questions must abstain; no benchmark query rewriting is used.

## Gate outcome

- Blockers: german_q04_strict_improvement, german_q08_strict_improvement
- Failures: none
