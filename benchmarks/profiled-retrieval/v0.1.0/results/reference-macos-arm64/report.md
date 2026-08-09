# OpenARDP F035 Profiled Retrieval Optimization

- Validity: `valid`
- Development candidate: `accepted`
- Holdout generalization: `positive`

| Metric | F029 | F035 |
|---|---:|---:|
| full_support | 0.529412 | 0.529412 |
| atom_recall | 0.500000 | 0.500000 |
| source_recall | 0.722222 | 0.722222 |
| evidence_precision | 0.043091 | 0.043348 |
| mrr | 0.461438 | 0.461438 |
| citation_integrity | 1.000000 | 1.000000 |
| unsupported_abstention | 1.000000 | 1.000000 |

- Warm p50 ns: 7391075333 -> 2369442291
- Warm p95 ns: 21193910125 -> 3174844959
- Phase evidence is body-free; selected bodies and embeddings are not persisted.
- The holdout verdict is reported even when negative and was not used for tuning.
