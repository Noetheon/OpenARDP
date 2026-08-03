# Provider-Neutral Multilingual Retrieval

Feature 029 adds an explicit optional semantic retrieval profile without changing the local lexical default, authoritative
evidence, persisted schemas or catalog. The provider sees only bounded text from a verified exact snapshot and returns
fixed-point scores. Selected content still resolves from the existing CAS/catalog evidence path; embeddings remain
disposable worker memory.

## Runtime and trust boundary

The first adapter uses `intfloat/multilingual-e5-small` at exact revision
`f470c6a1a906014160ece1968c484b275f0396de`. Its six-file, 492,794,646-byte bundle is provisioned outside Git from a
committed source lock and verified as a closed regular-file tree before use. Runtime loading is local-only, SafeTensors
only, rejects remote code, sets Hugging Face/Transformers offline mode and denies socket creation before importing the
optional model libraries.

The spawned persistent worker applies the upstream `query: ` / `passage: ` prefixes, attention-mask mean pooling, L2
normalization and cosine similarity. Scores are quantized to signed integer millionths. Its cache is keyed by exact CAS
object identity and retains only model-specific passage tensors until the worker closes; no vector enters SQLite, CAS,
receipts or benchmark results.

## Hybrid retrieval and abstention

The F029 profile intentionally supplements rather than replaces F027:

1. F027 exact lexical candidates are CAS-reverified, evaluated by the minimum-relevance policy and retained as the
   higher-priority fallback tier.
2. Accepted RichEvidence projections take precedence over generic representation rows; TXT/Markdown/CSV use their exact
   canonical block bodies.
3. E5 scores all bounded snapshot passages. Candidates below 0.800000 or failing the exact volatile-time guard are
   excluded.
4. Eligible semantic candidates receive a four-item ranked prefix, a 32-item per-document cap and deterministic document
   round-robin before the global Top-128. This prevents the 1,656-row CSV source from starving smaller sources.
5. F027 exact-body deduplication, 16-item source quota and fair allocation exhaust the lexical tier before semantic
   additions. Successful empty results emit `no_semantic_evidence`.

The ordinary local compiler remains lexical and provider-free. Semantic composition is explicit and its receipt algorithm
identity binds provider recipe, model bundle, limits, score policy, fallback tier, diversity policy and Rich-first
precedence.

## Frozen benchmark evidence

All revisions reuse the unchanged F024 corpus and F025 nineteen questions, support atoms and source judgments. They use
the F028 CSV product path, the exact offline F023 PDF bundle and two fresh workspaces. No operator query, translation
dictionary, answer generator or threshold tuning is used.

Two unfavorable results are retained rather than overwritten:

- v0.1 proved that semantic-only global Top-128 regressed overall support because the large CSV source dominated before
  quotas.
- v0.2 proved overall non-regression after hybrid/source-balanced allocation but exposed that generic representation rows
  shadowed accepted PDF/DOCX/PPTX RichEvidence.
- v0.3 fixes only that representation precedence and is `PROVIDER_RETRIEVAL_READY` under every predeclared gate.

| Direct treatment | Full support | Atom recall | Source recall | Precision | MRR | Citations | Unsupported abstention |
|---|---:|---:|---:|---:|---:|---:|---:|
| F027 lexical | 41.1765% | 34.7826% | 44.4444% | 3.9855% | 33.3333% | 100% | 100% |
| F029 hybrid semantic | 52.9412% | 50.0000% | 72.2222% | 4.3091% | 46.1438% | 100% | 100% |

Q04 and Q08 each improve from zero atom/full support to complete support. Both unsupported questions still select no
evidence. All timing-independent semantic rows are byte-identical across the two fresh v0.3 workspaces.

## Cost and operating interpretation

The macOS arm64 reference run scores 3,206 passages per question. The first request builds the cache; the following
18 requests account for 57,708 cache hits out of 60,914 passage scores (94.73%). Summed query wall time is 65.79 seconds
for F027 and 174.41 seconds for F029, about 2.65 times slower. Peak E5 worker RSS is 1,233,502,208 bytes. The complete
two-workspace run takes 555.65 seconds including repeated ingestion and model initialization.

This profile is therefore useful for repeated multilingual/paraphrase workloads where the passage cache can be amortized;
it is not a replacement for cheap exact identifier lookup. The benchmark covers one small redistributable NASA/CISA
corpus and does not establish population-wide accuracy, generation quality, accelerator portability or production SLOs.

## Reproduction

```bash
uv run python scripts/verify_embedding_bundle.py \
  --source-lock model-bundles/multilingual-e5-small-v1/source-lock.json \
  --bundle /Users/Shared/openardp-multilingual-e5-small-v1

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --all-extras python \
  scripts/run_provider_retrieval_benchmark.py \
  --protocol-version 0.3.0 \
  --pdf-bundle /Users/Shared/openardp-pdf-bundle-2.114.0-v1 \
  --e5-bundle /Users/Shared/openardp-multilingual-e5-small-v1 \
  --output /tmp/openardp-f029

python3 -I -S scripts/validate_provider_retrieval_benchmark.py \
  --protocol-version 0.3.0 \
  --result /tmp/openardp-f029
```
