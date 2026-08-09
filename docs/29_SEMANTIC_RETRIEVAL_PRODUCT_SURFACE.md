# Semantic Retrieval Product Surface

Feature 030 introduced the exact F029 v0.3 hybrid multilingual retrieval profile as an opt-in product capability.
Feature 035 advances new semantic compilations to the exactly identified `1.3.0` profile when the configured provider
advertises prepared-corpus support, while preserving `1.2.0` for historical replay and compatible third-party providers.
Lexical retrieval remains the provider-free default. The score floor, Rich-first precedence, exact
deduplication, quotas, verification and abstention remain explicit identity-bound behavior.

## CLI

New compilation selects lexical retrieval when `--retrieval-profile` is omitted. Semantic compilation is explicit:

```bash
uv run --extra semantic openardp context "question" --document DOCUMENT_ID --budget 262144 \
  --retrieval-profile semantic \
  --semantic-bundle /Users/Shared/openardp-multilingual-e5-small-v1 \
  --semantic-source-lock model-bundles/multilingual-e5-small-v1/source-lock.json \
  --store .openardp --json
```

Bundle and source-lock options are an all-or-none trusted local pair. They are rejected for lexical compilation. A
semantic receipt can be replayed only after the same pair constructs a provider with the exact persisted recipe and
algorithm identity; missing capability, explicit profile disagreement and any recipe drift fail closed.

Output remains handle-first and body-free unless the existing `--include-bundle` switch is explicit. Public failures do
not include task/evidence text, paths or provider exception details.

## MCP

MCP interface `0.2.0` adds only an optional `retrieval_profile` enum to `compile_context`. Omission means `lexical`.
The operator may authorize one semantic provider when starting the stdio process:

```bash
uv run --extra semantic openardp mcp --store .openardp \
  --semantic-bundle /Users/Shared/openardp-multilingual-e5-small-v1 \
  --semantic-source-lock model-bundles/multilingual-e5-small-v1/source-lock.json
```

Clients never receive path, provider, model, policy, limit or executable authority. An unconfigured semantic request
returns the stable `invalid_params` category without lexical fallback. One provider worker is reused within the session
and closed on normal exit or failure; embeddings remain bounded disposable process memory.

## Current prepared execution profile

The F035 profile prepares the exact ordered semantic corpus once in the isolated E5 worker. Warm requests carry only the
query and opaque corpus identity. A second bounded compiler-local cache retains verified rich retrieval text for exact
lexical rescoring; returned matches are CAS-reverified. Both caches bind the exact snapshot and limits and are discarded
on drift or process close. Neither creates a vector database, durable index or provider-neutral document representation.

Warm catalog checks use a body-free digest of the accepted rich attempt and all ordered reference, projection and
retrieval object mappings. This avoids rebuilding thousands of provider-native models while still comparing the cache
with authoritative SQLite facts. Selected content is independently hash-verified again during bundle materialization.
Canonical additive budgeting is byte-identical to historical full-bundle measurement for every built-in estimator;
unknown estimators fail closed.

## Operational evidence

The frozen F030 benchmark measures two cold/warm pairs over fresh workspaces and the unchanged F024/F025 workload. Each
pair reuses one verified E5 provider across workspaces, so warm cache reuse is measured without replaying a receipt whose
runtime audit facts differ. A standard-library-only validator recomputes identities, aggregation, gates, privacy and the
complete result manifest.

```bash
uv run --all-extras python scripts/run_semantic_surface_benchmark.py \
  --pdf-bundle /Users/Shared/openardp-pdf-bundle-2.114.0-v1 \
  --e5-bundle /Users/Shared/openardp-multilingual-e5-small-v1 \
  --output /tmp/openardp-f030
python3 -I -S scripts/validate_semantic_surface_benchmark.py --result /tmp/openardp-f030
```

The reference evidence is macOS arm64-specific. Linux and Windows product behavior remains covered by model-free CI,
but their model timing is unmeasured. The benchmark covers one 492,794,646-byte pinned semantic bundle and one small
redistributable corpus; it makes no answer-generation, broad-domain quality, accelerator-portability or production-SLO
claim.

The committed two-run result is `SEMANTIC_SURFACE_READY`. Cold query wall time totals 348.695 seconds; warm time totals
252.880 seconds (72.5216% of cold, or 27.4784% lower). All 121,828 warm passage scores are cache hits, both within-run
and across-run timing-free projections are identical, and peak provider-worker RSS is 1,500,725,248 bytes (1.398 GiB),
109,887,488 bytes below the frozen ceiling.

F035 adds a separate counterbalanced phase benchmark over unchanged F025 plus one post-freeze F034 milestone. Its
`run-manifest.json` discloses each provider-worker peak RSS and exact recipe; `phases.json` reconciles compiler, source and
provider durations without bodies, questions, user names, host names or paths. The F034 result is reported independently
from F025 candidate acceptance and is retained even when generalization is negative.

The binding macOS arm64 result is valid: F025 precision improves from `29/673` to `29/669` with every protected quality
metric non-regressing. Warm p50 falls from 7.391 s to 2.369 s (67.94%) and warm p95 from 21.194 s to 3.175 s (85.02%).
Cold samples remain separately disclosed and noisy; no cold-start improvement is claimed. Peak provider-worker RSS is
1,365,327,872 bytes. The unchanged F034 candidate exactly reproduces all frozen F029 quality metrics in two deterministic
fresh workspaces, so holdout generalization is positive without holdout tuning.

## Downstream evidence-review utility

F036 reuses the immutable body-free F034/F035 observations without rerunning parsers or models. A provider-free reviewer
checks whether the first `1`, `3`, `5`, `10` or `64` selected evidence items contain every required atom and source in
relevant citation-valid evidence; unsupported questions succeed only through explicit empty abstention. Budget three was
frozen from the F025 development plateau before the one-time F034 projection.

At the primary budget, F025 task completion remains `11/19` for both F029 and F035 (`9/17` answerable and `2/2` safely
abstained), while warm p50/p95 time-to-ready remains 67.94%/85.02% lower. On F034, the lexical baseline completes 61% of
tasks, while F029 and F035 complete 76%; the semantic result rises to 81% only at the 64-item ceiling. Citations are 100%
valid and source fitness is 100% on F025 and 90% on F034 for retrieved relevant sources.

```bash
uv run python scripts/run_downstream_utility_benchmark.py --output /tmp/openardp-f036
python3 -I -S scripts/validate_downstream_utility_benchmark.py /tmp/openardp-f036
```

This validates bounded evidence-packet utility and review effort, not human reading time, comprehension, generated-answer
correctness, domain readiness or a release decision. The next evidentiary boundary is a preregistered blinded human study
or a fixed answer-generation study whose prompts, model identity and grading policy are frozen before evaluation.

## Persistence and rollback

No embedding, vector, provider-native model state or universal vector index enters SQLite, CAS, schemas or receipts.
Removing the additive surface requires no workspace migration; existing lexical and semantic receipts remain governed
by their exact algorithm identities.
