# Minimum Relevance and Explicit Abstention

Feature 026 adds a deterministic eligibility floor to the existing verified context-candidate path. It does not claim
semantic understanding. The policy uses only bounded normalized task signals and CAS-reverified candidate content, then
records integer-only coverage facts in a body-free receipt extension.

## Behavior

- Unicode task and candidate text is normalized with NFC and case folding.
- A frozen function-word list removes low-information task terms.
- Identifiers, acronyms, dates and standalone calendar years receive explicit high-information weight.
- Repetition never increases score; only unique task-signal coverage counts.
- Every explicit volatile-time signal and calendar year in a task must occur in the same candidate.
- Candidates below the inclusive 250,000-millionths floor are rejected as `insufficient_relevance` before budget
  selection.
- A valid empty discovery or an all-relevance-rejected result returns no items and emits `no_relevant_evidence` in both
  the context bundle and selection receipt.

Integrity, cancellation, configuration, trust, sensitivity, freshness and resource-limit outcomes remain distinct.
Historical receipts retain the legacy lexical algorithm identity and the CLI selects that profile when replaying them.
No original, evidence identity, persisted workspace schema or public JSON schema changes.

## Binding F025 comparison

The two-workspace reference under
`benchmarks/relevance/v0.1.0/results/reference-macos-arm64/` uses the unchanged F025 corpus, question set and protocol
identities. The independent standard-library validator returns `RELEVANCE_ABSTENTION_READY` with result ID
`sha256:ff3f9d25763073cabcc8a5a8e7fb95714aa4d521df3189b76db5e3e32cbb91c3`.

| Question | F025 selected | F026 selected | Full support retained | F026 abstained |
|---|---:|---:|---:|---:|
| Q02 | 64 | 7 | yes | no |
| Q03 | 64 | 64 | yes | no |
| Q06 | 64 | 16 | yes | no |
| Q13 | 64 | 10 | yes | no |
| Q14 | 64 | 11 | yes | no |
| Q17 | 64 | 0 | n/a | yes |
| Q18 | 64 | 0 | n/a | yes |
| Q19 | 64 | 10 | yes | no |

All six frozen positive questions retain complete atom/source support and complete citation integrity. Both frozen
unsupported questions now emit genuine zero-evidence abstention. Semantic result projections are identical across the
two fresh executions. The tool-observed run completed in approximately 103 seconds, below the predeclared five-minute
gate; timing is not included in the deterministic result identity.

## Limits and rollback

This is exact lexical filtering, not ranking, diversity, translation or embedding retrieval. Q03 still fills the
64-candidate cap, and the benchmark is an eight-question diagnostic slice rather than population evidence. False
abstention remains possible for paraphrases or cross-language questions, so consumers must treat the heuristic as
disposable retrieval metadata rather than source truth.

F027 is responsible for lexical ranking, diversity and source quotas. F028 adds CSV ingestion. F029 evaluates optional
provider-neutral semantic and multilingual retrieval against the same frozen F025 benchmark. The F026 profile can be
rolled back by composing the explicit legacy candidate sources and legacy algorithm identity; persisted F026 receipts
remain policy-bound and fail closed under a mismatched replay profile.

## Reproduction

```bash
uv run python scripts/run_relevance_benchmark.py \
  --pdf-bundle /Users/Shared/openardp-pdf-bundle-2.114.0-v1-measured \
  --output /Users/Shared/openardp-f026-result
uv run python scripts/validate_relevance_benchmark.py \
  --result /Users/Shared/openardp-f026-result
```
