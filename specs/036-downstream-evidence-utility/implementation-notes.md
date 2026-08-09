# F036 Implementation Notes

## Outcome

F036 is implemented. It adds no production retrieval behavior, provider, answer generator, dependency, schema or
persistent state. The committed macOS arm64 result is `valid`; the F025 downstream candidate is `accepted`; and the
protocol-frozen F034 downstream generalization verdict is `positive`.

## Method and trust boundary

- The provider-free reviewer consumes only immutable F034/F035 body-free observations. It never reads question text,
  reference answers or document bodies and never invokes a parser, model, retrieval provider or network service.
- Answerable completion requires every required atom and source within the selected prefix, counting only relevant
  citation-valid evidence. Unsupported completion requires explicit abstention and an empty selection.
- The complete `1/3/5/10/64` curve and primary budget three were selected on permitted F025 development evidence before
  computing the F034 aggregates. F034 baseline and F035 candidate identities remain unchanged and their comparison is
  explicitly unpaired and timing-free.
- Source coverage, source fitness, citation integrity, review-item effort and retrieval time-to-ready remain separate.
  No item-count-to-human-time conversion or answer-correctness claim is made.
- Publication is bounded, atomic and manifest-last. The separate stdlib-only validator imports neither producer nor
  evaluator logic and reconstructs every raw row, aggregate, decision, report and digest from the authoritative inputs.

## Binding evidence and findings

Reference evidence: `benchmarks/downstream-utility/v0.1.0/results/reference-macos-arm64/`.

- The package contains 2,380 review observations and is approximately 1.3 MiB.
- At budget three, F025 F029/F035 task completion is `11/19` (`0.578947`): `9/17` answerable questions complete and both
  unsupported questions abstain safely. Atom/source coverage is `19/46` (`0.413043`) and `10/18` (`0.555556`);
  relevant citations and source fitness are complete.
- Increasing F025 review budget from three to 64 adds atom/source coverage (`19/46` to `23/46`, `10/18` to `13/18`) but
  completes no additional answerable task. F035 inspects four fewer tail items than F029 (`669` versus `673`).
- F035 preserves every primary downstream metric and deterministic projection while warm time-to-ready p50 falls from
  `7,391,075,333 ns` to `2,369,442,291 ns` (67.94%) and p95 from `21,193,910,125 ns` to `3,174,844,959 ns` (85.02%).
- On F034, primary task completion is 61% lexical, 76% F029 semantic and 76% F035. F029/F035 rise to 81% only at the
  64-item ceiling. F035 is non-regressing against F029 for every declared utility/trust metric at every budget.
- F034 relevant citations are 100% valid and source fitness is 90%. The remaining 19/90 answerable misses at the ceiling
  are retrieval failures, not a context-budget shortage hidden by aggregation.

## Verification

Focused evaluator, adversarial publication, duplicate-member, drift and independent-validator tests pass. The committed
reference package validates with isolated Python. Repository-wide Ruff and format checks cover 420 files; strict mypy
covers 129 source modules; all 1,788 tests pass with four skips and 85.41% coverage; repository validation,
maintainability/hygiene audits and wheel/sdist build pass. The exact convergence commands were:

```text
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run python scripts/validate_repository.py
uv run python scripts/audit_maintainability.py --policy quality/maintainability-policy.json
uv run python scripts/audit_repository_hygiene.py --root .
uv build
python3 -I -S scripts/validate_downstream_utility_benchmark.py benchmarks/downstream-utility/v0.1.0/results/reference-macos-arm64
```

## Limits, rollback and next boundary

- This is a deterministic evidence-review proxy, not a blinded human study or generated-answer evaluation. It proves the
  required benchmark support is present in a bounded trusted packet, not that a consumer interprets it correctly.
- F025 is small and NASA/CISA-specific; F034 is XQuAD-derived and multilingual but not a broad domain sample. Timings are
  inherited from the measured macOS arm64 F035 result; no new cross-platform model timing is claimed.
- The largest next impact is a frozen miss-analysis/error-attribution slice over the 19 F034 answerable ceiling misses,
  followed by one targeted retrieval intervention evaluated on a new untouched holdout. A human or fixed-generation
  study should follow only once packet coverage is adequate for its intended task, unless the study's purpose is
  explicitly to measure current failure.
- Rollback is deletion of the F036 benchmark scripts, result package, tests and documentation references. No migration,
  cache invalidation or workspace repair is required.
