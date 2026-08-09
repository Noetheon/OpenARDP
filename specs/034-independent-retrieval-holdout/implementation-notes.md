# F034 Implementation Notes

## Acceptance criteria

- Reproduce exactly 20 Markdown sources and 100 ordered questions from pinned XQuAD commit
  `7d30520c717524000f0d9d2f9c10a069acd9d285` without network access at benchmark time.
- Bind corpus, questions, schema, protocol, license, notices and upstream identities and reject drift, duplicate JSON
  members, path escape, symlinks and unexpected inventory.
- Run the unchanged F027 lexical and F029 semantic profiles twice in fresh workspaces with the reviewed local E5 bundle.
- Publish bounded body-free evidence atomically and independently recompute metrics and separate validity/quality verdicts.
- Preserve F025 as the development set and F034 as milestone-only validation evidence.

## Delivered evidence

The deterministic generator produced corpus ID
`sha256:a5047bbd768cd2927da302da94ded5fa8449a2a3df097ec482f9f6ca708eaca3`, question-set ID
`sha256:5648e59596d1e6bc95cf786f5bdf8a9da8856d8d1f6ee072621014be1b848c61` and protocol ID
`sha256:371bfeafc35d80b792aed06cf5394356bcba83cc4fb2510e682ef29cf2f4e91e`.

The two fresh baseline runs produced identical timing-free projections and no runtime or citation failures. The independent
validator returned `HOLDOUT_BASELINE_VALID` and `HOLDOUT_BELOW_TARGETS`. The semantic profile improved overall atom and
source recall from `0.610000` to `0.810000` and full support from `0.566667` to `0.788889`. German atom recall improved
from `0.250000` to `0.550000`; Spanish improved from `0.150000` to `0.600000`. Citation integrity and unsupported
abstention were `1.000000`.

The result is deliberately unfavorable where the evidence is unfavorable. Semantic evidence precision was `0.179039`,
MRR `0.722090`, and five predeclared quality checks remained below target: atom recall, evidence precision, full support,
MRR and source recall. Query-distribution wall p50/p95 was 110/149 ms for lexical and 198/272 ms for semantic. The E5
worker peak RSS was 1,155,907,584 bytes. These are baseline measurements, not isolated cold/warm phase measurements.

## Verification

```bash
uv run --locked python scripts/generate_retrieval_holdout.py \
  --upstream /Users/Shared/openardp-xquad-source-20260809 \
  --check --repository-root .
uv run --locked python scripts/run_retrieval_holdout.py \
  --e5-bundle /Users/Shared/openardp-multilingual-e5-small-v1 \
  --output benchmarks/retrieval-holdout/v0.1.0/results/reference-macos-arm64
uv run --locked python scripts/validate_retrieval_holdout.py \
  --result benchmarks/retrieval-holdout/v0.1.0/results/reference-macos-arm64
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

## Tradeoffs and next boundary

XQuAD is a public external holdout rather than a secret test set. Independence therefore comes from the frozen pre-run
identities and milestone-only policy, not access control. Questions cover aligned encyclopedic passages, not every future
OpenARDP domain. F034 changes no ranking, caching or provider behavior.

The next bounded feature should profile ingestion, candidate discovery, provider startup/encoding/scoring, allocation and
verification separately on F025. Optimization should then raise absolute recall and precision while reducing warm latency;
F034 must remain byte-identical until the resulting candidate receives one milestone evaluation.
