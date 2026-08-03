# Implementation Notes: F027

## Acceptance criteria restated

Implement deterministic lexical ordering, exact CAS-body deduplication, bounded per-document allocation and real source
diversity after F026 relevance filtering. Preserve Q02/Q03/Q06/Q13/Q14/Q19 support/citations, Q17/Q18 abstention,
historical replay, direct MRR and source recall. Compare F026/F027 against unchanged F025 inputs twice, publish body-free
independently validated evidence, pass all repository gates and keep F028 CSV/F029 provider retrieval out of scope.

## Delivered structure

- `domain/context_ranking.py`: immutable policy, rank key and pure exhaustive allocator.
- `services/context_ranking.py`: extracted historical classifier and compatibility helpers, reducing the compiler hotspot.
- `services/context_compiler.py`: thin optional allocation integration and combined identity binding.
- `interfaces/context_composition.py` and CLI: explicit legacy, F026-only and default F027 profiles including replay.
- paired runner, stdlib-only validator, committed result, docs and governance inventories.

## Measured evidence

The binding result is `LEXICAL_RANKING_READY`, ID
`sha256:a622eceb35a99838bfb1e23e7f05f9af3a2ef48bcdc8dbbb82234ad67c693cfd`. F026 versus F027 direct positive precision is
3/59 (0.050847) versus 3/44 (0.068182); MRR remains 23/36 (0.638889); source recall remains 1/1. All six positive support
and citation gates, two abstention gates and two-workspace determinism pass. Q03 selects 34 candidates across three
documents (16/16/2), with 121 quota and 9 duplicate decisions audited.

## Tradeoffs and residual risk

The four-item prefix intentionally favors early lexical quality before diversity. Sixteen is a conservative document
quota, not a universally optimal value. The benchmark is an eight-question diagnostic and absolute evidence precision
remains low; lexical retrieval still misses paraphrase and cross-language evidence. F029 will evaluate optional providers
without changing this frozen baseline.

## Validation record

The clean staged-tree worktree used `uv sync --locked --all-extras`. Ruff checked and format-checked 341 files; strict
mypy passed for 97 source files; independent repository validation, sdist/wheel build and every pre-commit hook passed.
The explicit full suite passed 1,625 tests with 3 skips and 85.29% branch coverage in 167.63 seconds. The initial core-only
sync correctly lacked optional Docling/visual import providers, so it was not treated as a code failure or final gate.
Remote branch/PR evidence is appended after publication.
