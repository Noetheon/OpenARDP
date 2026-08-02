# Redistributable real-world corpus and structural baseline

## Result

Feature 024 adds `openardp-realworld/v0.1.0`, an exact 6,634,970-byte offline corpus containing one PDF, DOCX, PPTX,
CSV, Markdown and plain-text source. The independently validated binding result is
`REALWORLD_BASELINE_READY`: all six assets were processed twice with identical source, recipe, native and ordered-block
identities, zero network attempts and complete body-free observation coverage.

This is a structural result for six selected English public-sector files. It is not evidence of semantic answer quality,
general document-population accuracy, a stable CSV product API, legal certainty or publisher endorsement.

## Corpus selection

Three original NASA Technical Reports Server files cover long-form PDF, Word and presentation structure around ethical
AI, science prioritization and open science. At review time each retained NTRS record stated `PUBLIC_USE_PERMITTED` or
`GOV_PUBLIC_USE_PERMITTED`, marked the chosen download non-draft and reported no third-party material.

Three exact files from official `cisagov/kev-data` commit
`564b8c59f9039926e2d9548ba5b334db45cb6b50` cover a 1,656-row operational CSV, its Markdown documentation and the
revision's CC0 1.0 text. The snapshot is historical benchmark data, not a current vulnerability feed.

Every payload is committed unchanged. `corpus-lock.json` binds its source URL/revision, path, media type, SHA-256, byte
length, authorship/publisher facts and one reviewed rights record. Minimal NTRS/Git metadata snapshots are also bound
into the RFC 8785/SHA-256 corpus identity:

`sha256:5e505148c7e9004a9c1ae7bd68c66addfc9ae3377be7e3057a81d7a1996649bd`

## Offline verification and explicit reproduction

Ordinary verification imports no parser and opens no network connection:

```bash
uv run python scripts/validate_realworld_corpus.py
```

The producer-side verifier and a separate stdlib-only validator require a closed tree, exact digests/lengths, all six
formats, one source/right mapping per payload, retained NASA/CISA metadata, valid Office containers and no missing,
extra, linked, special, case-colliding or normalization-colliding path.

Publisher reproduction is the only connected action. It accepts only reviewed HTTPS hosts and response media, follows
only allowlisted redirects, enforces 8 MiB per-file/16 MiB aggregate limits, stages exact bytes, verifies the complete
corpus and atomically publishes an absent destination. Two fresh reproductions matched the committed identity exactly in
11,750,031,917 ns and 10,802,469,792 ns.

## Parser paths and first-run findings

TXT and Markdown use the deterministic core text parser. DOCX, PPTX and PDF use the isolated Docling 2.114.0 profile;
PDF consumes only the separately validated F023 bundle. The CSV is completely parsed by an isolated stdlib-only F024
probe that emits hashes/counts rather than table bodies. It is benchmark tooling because the core does not expose stable
CSV ingestion.

The first binding run was intentionally retained outside the committed result as `REALWORLD_BASELINE_NOT_READY`. It
exposed two genuine limits:

- F016's complete TXT/CSV conformance producer rejects the real CSV because its repeated native/retrieval output exceeds
  the deliberate 1 MiB response bound. The F024 probe processes all 1,656 rows while keeping its response below 1 MiB.
- The real PPTX contains provider geometry slightly/partly outside slide bounds and one zero-area box. OpenARDP now clips
  only the visible region with explicit warning codes and uses an opaque native pointer where no honest rectangle exists;
  the complete native artifact remains unchanged.

The PPTX also contains one picture node whose native subtree exceeds the existing 8 MiB per-retrieval-body limit. The
resolver reaches the target and rejects materialization at the limit; the benchmark retains `pointer_bounded_count = 1`
while the small evidence projection and anchor remain retrievable. This is a real limitation, not a hidden success.

## Binding measurements

The complete run took 44,105,787,042 ns on the declared macOS arm64/Python 3.12 environment. Resource values are
workload/environment bounded; child peak RSS is a conservative process-family maximum.

| Asset | Format | Units | Pages | Tables | Wall p50 / p95 | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|
| CISA CC0 text | TXT | 14 | 0 | 0 | 0.143 / 0.184 ms | 69,353,472 B |
| CISA README | MD | 17 | 0 | 0 | 0.105 / 0.134 ms | 69,369,856 B |
| CISA KEV | CSV | 1,656 | 1 | 1 | 85.085 / 85.114 ms | 69,435,392 B |
| NASA AI workshop | DOCX | 678 | 0 | 8 | 3.246 / 3.297 s | 479,248,384 B |
| NASA ethical AI | PDF | 632 | 35 | 6 | 15.606 / 15.720 s | 1,725,415,424 B |
| NASA open science | PPTX | 209 | 13 | 0 | 2.824 / 2.969 s | ≤1,725,415,424 B |

The PPTX RSS is an upper bound inherited from the process-family high-water mark after PDF execution, not a claim that
the PPTX itself allocated that amount.

## Reproduce the result

```bash
uv run python scripts/run_realworld_corpus_benchmark.py \
  --pdf-bundle /absolute/path/to/validated-f023-bundle \
  --output /absolute/path/to/f024-result
uv run python scripts/validate_realworld_corpus_benchmark.py \
  --result /absolute/path/to/f024-result
```

The independent validator does not import the benchmark producer or evaluator. It reconstructs row coverage, summaries,
decision, report, file hashes and run identity from retained body-free observations. F025 must pin this exact corpus ID
and separately judge semantic questions, evidence relevance and source quality.
