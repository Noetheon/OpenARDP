# F023 implementation notes

## Acceptance criteria restatement

- Provision exactly the five runtime files consumed by the delivered Docling `2.114.0` PDF profile from full immutable
  revisions; model weights and generated packages remain outside Git.
- Publish only a fully hashed, licensed and closed installation; validation rejects every missing, extra, linked,
  colliding, corrupt or hostile archive entry before provider import.
- Produce a byte-deterministic portable package and install it safely into a fresh destination without network or hidden
  provider-cache authority.
- Convert the frozen PDF in the real isolated worker with empty caches and sockets denied, preserving exact source,
  canonical native, evidence-anchor and bundle identities inside existing resource limits.
- Retain a versioned independently validated benchmark with honest size, validation, cold/warm conversion, CPU, RSS,
  output-determinism and correctness evidence; F020 history and F024/F025 scope remain untouched.

## Analysis baseline

Spec-Kit analysis checked 30 functional requirements, 9 success criteria, 78 executable tasks and all 12 constitution
articles. Both requirements checklists passed (16/16 and 30/30); no critical contradiction, ambiguity, duplication,
coverage gap or unmapped task remained before implementation.

## Implementation result

The implementation adds a canonical source-lock and existing-contract manifest, exact closed-tree verification,
connected pinned provisioning, deterministic uncompressed ZIP transfer, safe offline installation and strict
manifest-closed parser validation. Provider caches are redirected to one fresh private worker root while offline flags
and socket denial remain active before provider import. Review texts, notices and benchmark evidence are committed;
384 MB model/package artifacts remain external.

## Measured result

Real provisioning produced source-lock ID
`sha256:232a68ac675fc8c6801b652a20e2f6adffc311aa7847e7dfb6d0759efb2bc5cb`, bundle ID
`sha256:442ab96f3d56146c63e6e98dfb7452a679571b4343e9b01e2bdb02b3eb0c74b8`, five files and
384,428,156 asset bytes. Two packages were byte-identical at 384,450,807 bytes and
`sha256:0d07aa40657419d0dafdb7184e98de494ce83cf9bd33759151fff3e3da137afa`; a fresh offline install
reconciled both trusted IDs.
Two complete connected provisions, each with a fresh internal provider cache and absent destination, independently
returned the same source-lock ID, bundle ID, five-file inventory and exact byte counts.

The binding benchmark decision is `PDF_OFFLINE_READY`. After one excluded warm-up, three fresh worker processes measured
wall p50/p95 4,169,238,625/4,270,645,500 ns, CPU p50/p95 4,218,546,000/4,268,149,000 ns and peak child RSS
1,473,970,176 bytes. The deterministic bootstrap median interval was 4,163,903,250–4,270,645,500 ns; cold wall time was
4,270,645,500 ns and warm wall p50/p95 was 4,166,570,937/4,169,238,625 ns. All runs produced
one page, two fully anchored/pointer-backed candidates and canonical native ID
`sha256:9abd05e4a76fdb49d050a42fb5aa2b0a23c7da9615643c1347aa4f95e88cf7c6`.
Three complete validations measured 149,737,917/154,701,958 ns p50/p95 at 68,108,288 bytes peak RSS. The successful
connected provision downloaded five files/384,428,156 bytes in 191,254,236,500 ns. One preceding anonymous Hub attempt
failed cleanly with no published destination or staging residue; no unfavorable evidence was relabeled as success.

## Tradeoffs and remaining risks

- `ZIP_STORED` costs no meaningful additional space over already compressed safetensors and avoids zlib-version
  nondeterminism; the measured fixed overhead is 2,310 bytes.
- The bundle is 366.6 MiB and peak RSS is about 1.47 GB, material resource costs that operators must plan for.
- Connected anonymous upstream retrieval can fail transiently and took about 191 seconds in the successful measured run;
  offline use is independent of that variability after provisioning.
- Upstream license metadata and exact texts are traceable but do not establish legal certainty or training-data rights.
- The synthetic PDF proves actual offline availability and deterministic evidence only. Real-world redistributable corpus
  coverage and semantic source-quality evaluation remain deliberately blocked on F024 and F025.

## Exact binding commands

The real lifecycle used the four command facades documented in `quickstart.md`, with fresh external paths under
`/Users/Shared`; the paths are operational context and are not embedded in evidence. The benchmark and independent
validation commands were:

```bash
uv run --locked --extra docling python scripts/run_pdf_bundle_benchmark.py \
  --bundle /path/to/offline-install --package /path/to/bundle.zip \
  --provision-duration-ns 191254236500 \
  --output benchmarks/pdf-bundle/v0.1.0/results/reference-macos-arm64
uv run python scripts/validate_pdf_bundle_benchmark.py \
  --result benchmarks/pdf-bundle/v0.1.0/results/reference-macos-arm64
```
