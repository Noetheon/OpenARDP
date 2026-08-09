# OpenARDP F036 Downstream Evidence Utility

- Validity: `valid`
- F025 candidate: `accepted`
- F034 generalization: `positive`
- Primary review budget: 3 evidence items; complete curve: 1, 3, 5, 10, 64.

## F025 primary utility

| Metric | F029 | F035 |
|---|---:|---:|
| task_completion | 0.578947 | 0.578947 |
| answerable_completion | 0.529412 | 0.529412 |
| atom_coverage | 0.413043 | 0.413043 |
| source_coverage | 0.555556 | 0.555556 |
| citation_integrity | 1.000000 | 1.000000 |
| source_fitness | 1.000000 | 1.000000 |
| safe_abstention | 1.000000 | 1.000000 |

- Warm time-to-ready p50 ns: 7391075333 -> 2369442291
- Warm time-to-ready p95 ns: 21193910125 -> 3174844959

## F034 primary utility

| Treatment | Task complete | Atoms | Sources | Source fitness | Citations |
|---|---:|---:|---:|---:|---:|
| f027_lexical_direct | 0.610000 | 0.610000 | 0.610000 | 0.900000 | 1.000000 |
| f029_semantic_direct | 0.760000 | 0.760000 | 0.760000 | 0.900000 | 1.000000 |
| f035_candidate | 0.760000 | 0.760000 | 0.760000 | 0.900000 | 1.000000 |

## Evidence boundary

- F034 comparison is unpaired and timing-free across two previously frozen benchmark packages.
- Results contain no question text, reference answer, document body, embedding or local path.
- Item counts are review-effort proxies, not measured human reading time.
- Completion proves benchmark support is present in a bounded citation-valid packet; it does not prove human
  comprehension, generated-answer correctness, domain readiness or universal retrieval quality.
