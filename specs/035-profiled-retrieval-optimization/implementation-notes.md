# F035 Implementation Notes

## Outcome

F035 is implemented and independently validated. New semantic product compilations use the exact experimental `1.3.0`
profile when the provider implements the optional preparation capability; non-prepared providers and F029 `1.2.0`
receipts retain the compatible legacy composition. Provider-free lexical retrieval remains the default.
The committed macOS arm64 result is `valid`, the F025 development candidate is `accepted`, and the unchanged F034
holdout generalization verdict is `positive`.

## Acceptance criteria and implementation

- Body-free monotonic observations split snapshot resolution, discovery, classification, materialization, budgeting and
  finalization. Semantic discovery further reports enumeration, provider, admission and reconciliation; provider work
  reports passage encoding, query encoding and similarity. The independent validator requires complete non-overlapping
  parent/child reconciliation.
- The optional prepared-provider port sends verified passages once and later sends only query plus an opaque exact-corpus
  handle. Worker state binds ordered evidence/object identities, complete provider recipe and resource limits, remains
  bounded/process-local and disappears on close, timeout or failure.
- Warm semantic candidates reuse one exact compiler-lifetime snapshot entry. Rich metadata is reconciled through an
  authoritative catalog digest; text metadata retains complete catalog reconstruction. Every delivered body is still
  read and hash-verified from CAS.
- The retained lexical tier uses a bounded 64 MiB exact-snapshot rich-text cache. It recomputes lexical and relevance
  scores per query, CAS-verifies every returned match and compares the accepted-attempt/evidence-object digest with current
  SQLite facts. Drift fails closed.
- Prepared `1.3.0` replaces repeated whole-bundle fixed-point serialization with exact additive canonical-prefix
  accounting. Tests require byte-identical bundles and receipts for UTF-8 bytes, Unicode characters and conservative
  tokens. Unknown estimators fail closed; legacy selection keeps the historical path.
- Algorithm identity binds prepared semantic/lexical behavior, selected-object verification, rich precedence, admission,
  allocation, provider recipe/policy/limits and additive budgeting. No schema, workspace revision or persisted identifier
  changes.

## Candidate search and negative evidence

The unchanged F029 F025 baseline was full support `9/17`, atom recall `1/2`, source recall `13/18`, precision `29/673`,
MRR `353/765`, citation integrity `1/1` and unsupported abstention `1/1`.

The original 25% relative precision hypothesis failed. Top-K 40 and score floors around 0.80–0.81 approached a 23%
precision gain only by losing protected Q09/Q10/Q11 atoms or sources. Per-document caps of 8–12 also regressed recall.
Top-K 192/256 and larger ranked prefixes did not improve protected recall or MRR. A semantic-only path was much faster
and improved precision/source recall, but regressed full support from `9/17` to `8/17` and MRR from `0.461438` to
`0.423105`; it was rejected.

Before candidate/holdout freeze, the specification was clarified: all protected metrics must be non-regressing, at least
one absolute metric must improve strictly, and the failed 25% precision hypothesis remains explicit. The frozen candidate
keeps floor `800000`, Top-K `128`, ranked prefix `4` and lexical allocation, increases semantic per-document admission
from 32 to 64, and enables exact prepared execution.

## Binding benchmark evidence

Reference evidence: `benchmarks/profiled-retrieval/v0.1.0/results/reference-macos-arm64/`.

- Validity: `valid`; F025 candidate: `accepted`; F034 generalization: `positive`.
- F025 timing-free projections are identical across both fresh workspaces for both profiles.
- F025 quality is unchanged except selected evidence falls from 673 to 669 with all 29 relevant selections retained.
  Precision rises from `0.043091` to `0.043348` (+0.598% relative); every other protected metric is identical.
- Warm p50 falls from `7,391,075,333 ns` to `2,369,442,291 ns` (67.94% lower).
- Warm p95 falls from `21,193,910,125 ns` to `3,174,844,959 ns` (85.02% lower).
- Counterbalanced summed F025 query wall falls from `422,073,147,832 ns` to `264,418,740,461 ns` (37.35% lower).
- Cold query observations are disclosed separately: F029 `[66,091,666,584; 7,390,441,250] ns`; F035
  `[15,240,627,500; 174,220,626,209] ns`. They show order/host noise and are not promoted to a cold-start gain.
- Peak provider-worker RSS across four runs is `1,365,327,872` bytes. The prepared cache remains bounded derived memory;
  no embeddings or text are persisted in benchmark evidence.
- F034 candidate metrics are byte-for-byte equal to the frozen F029 baseline: full support `71/90`, atom/source recall
  `81/100`, precision `41/229`, MRR `5459/7560`, and complete citation integrity/unsupported abstention. Both fresh
  F034 timing-free projections are identical.

## Verification

The implementation was checked with focused domain/unit/integration suites, a real offline E5 prepared-provider test,
Ruff, format, strict mypy, full pytest, repository validation, package build, the binding benchmark producer and its
independent validator. The final convergence commands and repository-wide counts are recorded in the merge commit/PR
evidence rather than duplicated here.

## Remaining limits and next boundary

- The gain applies to repeated questions within one compiler/provider lifetime; it makes no cross-process warm-start SLO.
- F025 absolute retrieval quality remains modest despite the strict precision improvement. F034 confirms no regression,
  not that retrieval is sufficient for every domain.
- Only the reviewed multilingual-E5 bundle and macOS arm64 timing host are measured. Linux/Windows behavior is covered by
  model-free tests, not equivalent model timing.
- F035 evaluates retrieval and evidence integrity, not generated answer correctness. The next bounded feature should prove
  downstream task utility against a fixed consumer/human protocol without tuning on F034 or weakening source checks.
