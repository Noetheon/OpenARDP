# F024 real-world corpus structural baseline

Decision: **REALWORLD_BASELINE_READY**

- Corpus: `sha256:5e505148c7e9004a9c1ae7bd68c66addfc9ae3377be7e3057a81d7a1996649bd`
- Payloads: 6 / 6634970 bytes
- Formats: csv, docx, md, pdf, pptx, txt
- Retained observations: 12

| Asset | Format | Blocks | Pages | Tables | Bounded pointers | Wall p50/p95 (ns) | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| cisa-kev-license | txt | 14 | 0 | 0 | 0 | 143250 / 184458 | 69353472 |
| cisa-kev-readme | md | 17 | 0 | 0 | 0 | 105104 / 134375 | 69369856 |
| cisa-known-exploited-vulnerabilities | csv | 1656 | 1 | 1 | 0 | 85084625 / 85113500 | 69435392 |
| nasa-ai-strategic-planning-workshop | docx | 678 | 0 | 8 | 0 | 3245755854 / 3296945375 | 479248384 |
| nasa-ethical-ai-framework | pdf | 632 | 35 | 6 | 0 | 15606485958 / 15719788416 | 1725415424 |
| nasa-open-science-and-ai | pptx | 209 | 13 | 0 | 1 | 2824012604 / 2969379208 | 1725415424 |

This result covers exact offline structural parsing and retrievability for six selected English public-sector files. It does not establish semantic answer correctness, ranking or citation quality, general document-population quality, legal certainty or publisher endorsement.
