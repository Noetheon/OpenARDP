# Semantic Retrieval Product Surface

Feature 030 exposes the exact F029 v0.3 hybrid multilingual retrieval profile as a usable, opt-in product capability.
It does not change retrieval quality policy: lexical F027 remains the provider-free default, and semantic selection
retains the pinned score floor, Rich-first precedence, source-balanced admission, exact deduplication, quotas,
verification and abstention behavior.

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

## Persistence and rollback

No embedding, vector, provider-native model state or universal vector index enters SQLite, CAS, schemas or receipts.
Removing the additive surface requires no workspace migration; existing lexical and semantic receipts remain governed
by their exact algorithm identities.
