# OpenARDP Provider-Neutral Retrieval Evaluation

**Decision:** `PROVIDER_RETRIEVAL_READY`

This frozen comparison runs the unchanged F025 questions directly against the F027
lexical profile and the explicit offline F029 multilingual provider. It evaluates
retrieved evidence and citations, not generated prose.

## Exact direct-treatment metrics

| Treatment | Full | Atoms | Sources | Precision | MRR | Citations | Abstain |
|---|---:|---:|---:|---:|---:|---:|---:|
| f027_lexical_direct | 0.411765 | 0.347826 | 0.444444 | 0.039855 | 0.333333 | 1.000000 | 1.000000 |
| f029_semantic_direct | 0.529412 | 0.500000 | 0.722222 | 0.043091 | 0.461438 | 1.000000 | 1.000000 |

## German cross-language questions

- Q04: atom recall 0.000000 -> 1.000000; full support 0.000000 -> 1.000000.
- Q08: atom recall 0.000000 -> 1.000000; full support 0.000000 -> 1.000000.

## Runtime boundary

- F027 summed query wall ns: 65792142584
- F029 summed query wall ns: 174406208082
- Provider requests: 19
- Passages scored: 60914
- Passage-cache hits: 57708
- Peak provider-worker RSS bytes: 1233502208
- Embeddings remained disposable worker memory and are absent from this result.
- Both unsupported questions must abstain; no benchmark query rewriting is used.

## Gate outcome

- Blockers: none
- Failures: none
