# OpenARDP Independent Retrieval Holdout

- **Validity:** `HOLDOUT_BASELINE_VALID`
- **Quality:** `HOLDOUT_BELOW_TARGETS`

This milestone-only XQuAD holdout measures retrieved evidence and citations,
not generated answers. F025 remains the development benchmark.

## Exact metrics

| Treatment | Full | Atoms | Sources | Precision | MRR | Citations | Abstain |
|---|---:|---:|---:|---:|---:|---:|---:|
| f027_lexical_direct | 0.566667 | 0.610000 | 0.610000 | 0.242063 | 0.581481 | 1.000000 | 1.000000 |
| f029_semantic_direct | 0.788889 | 0.810000 | 0.810000 | 0.179039 | 0.722090 | 1.000000 | 1.000000 |

## Multilingual atom recall

- en: 0.883333 -> 0.966667
- de: 0.250000 -> 0.550000
- es: 0.150000 -> 0.600000

## Query runtime

- f027_lexical_direct: p50 109724834 ns; p95 148531417 ns; total 10055038176 ns
- f029_semantic_direct: p50 198435750 ns; p95 271781916 ns; total 25569226288 ns

## Evidence boundary

- Provider requests: 100
- Passages scored: 12200
- Passage-cache hits: 12078
- Peak provider-worker RSS bytes: 1155907584
- Embeddings remain disposable worker memory and are not persisted.
- Quality blockers: atom_recall, evidence_precision, full_support, mrr, source_recall
- Validity blockers: none
- Failures: none
