# OpenARDP Semantic End-to-End Evaluation

**Decision:** `SEMANTIC_E2E_NOT_READY`

This diagnostic evaluates the delivered evidence layer, not prose generation. Direct
questions and frozen operator terms are reported separately; operator assistance is not
semantic retrieval. CSV remains an explicit
unsupported product format.

## Exact results

| Treatment | Full | Recall | Precision | MRR | Sources | Citations | Abstain | DE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| openardp_direct | 0.352941 | 0.326087 | 0.011029 | 0.288622 | 0.500000 | 1.000000 | 0.000000 | 0.000000 |
| openardp_operator | 0.823529 | 0.869565 | 0.050704 | 0.789661 | 0.888889 | 1.000000 | 0.000000 | 1.000000 |

## Boundaries

- Semantic rows identical across two fresh workspaces: `true`.
- Supported-format ingestion: `1.000000`.
- Hard failures: `none`.
- Decision blockers: `direct_abstention, direct_atom_recall, direct_evidence_precision, direct_full_support, direct_german_atom_recall, direct_mrr, direct_source_recall`.
- Retained capability gaps: `csv_product_ingestion_unsupported, direct_cross_language_retrieval_absent, unsupported_false_positive_selection`.

F015 `NO-GO`, F020 `CONDITIONALLY_WORTHWHILE`, and F024
`REALWORLD_BASELINE_READY` remain historical
evidence. This result changes only the bounded semantic/source-quality assessment.
