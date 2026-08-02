# Research: Offline PDF Model Bundle

## Exact runtime model boundary

**Decision**: Provision only the five files consumed by the delivered Docling `2.114.0` CPU PDF profile: Heron layout
`config.json`, `preprocessor_config.json`, `model.safetensors`, and accurate TableFormer `tm_config.json` plus weights.

**Rationale**: The existing profile enables layout and accurate table structure while disabling OCR, picture, chart,
code/formula and remote enrichment. Docling's exact pinned source resolves layout through
`docling-project/docling-layout-heron` and TableFormer through `docling-project/docling-models` `v2.3.0`. Downloading the
default/all catalog would add hundreds of megabytes of unreachable models and widen supply-chain risk.

**Alternatives considered**: all Docling models; default downloader set; layout-only; TableFormer fast mode. The first two
contradict minimal scope, layout-only cannot satisfy the delivered profile, and fast mode changes parser behavior.

## Immutable upstream revisions

**Decision**: Resolve Heron's mutable `main` reference once to full revision
`8f39ad3c0b4c58e9c2d2c84a38465abf757272d8` and retain TableFormer tag `v2.3.0` only together with resolved full revision
`fc0f2d45e2218ea24bce5045f58a389aed16dc23`. Provisioning requests only those full revisions and allowlisted paths.

**Rationale**: Docling pins the TableFormer tag but leaves the default layout at `main`. Reproducibility requires a full
content revision, and the source lock must survive later branch/tag movement.

**Alternatives considered**: trust branches/tags at provision time; vendor opaque provider-cache snapshots; pin only
weight files. Each leaves configs, repository movement or file selection unbound.

## Licensing evidence

**Decision**: Record the upstream model-card assertions `Apache-2.0` for Heron and `CDLA-Permissive-2.0` for
`docling-models`; include complete official license texts and a per-file notice, while explicitly labelling this a reviewed
assertion rather than legal advice or training-data provenance proof.

**Rationale**: Hashes identify bytes but not redistribution rights. Both upstream repositories expose permissive license
metadata, yet neither selected runtime subtree supplies a complete portable license set on its own.

**Alternatives considered**: omit license files; copy only model-card prose; claim license verification proves legal
ownership. These are incomplete or overstate automated evidence.

## Installation layout and identity

**Decision**: Keep control material outside the parser's exact asset root:
`install/manifest.json`, `provenance.json`, notices/licenses, and `install/assets/...`. The existing
`ModelBundleManifest` inventories only exact runtime files under `assets/`; its RFC 8785/SHA-256 ID remains authoritative.

**Rationale**: A manifest cannot include its own digest. Separating control material permits a completely closed runtime
tree and lets ordinary PDF CLI use `assets/` plus the adjacent manifest without accepting metadata as model input.

**Alternatives considered**: self-referential manifest inside model root; allow arbitrary extra files; invent a second
model identity. All weaken exact validation or compatibility.

## Deterministic transfer package

**Decision**: Use a closed uncompressed ZIP profile with sorted UTF-8 POSIX member names, fixed DOS epoch, fixed
regular-file modes, no comments/extra fields/encryption, `ZIP_STORED` for every member and a single top-level directory.
Extraction rejects links, devices, traversal, duplicates, collisions, unexpected members, trailing bytes and
declared/actual expansion drift.

**Rationale**: Python 3.12 supplies portable deterministic ZIP read/write primitives without a new dependency.
Uncompressed members keep package bytes independent of platform zlib versions; the sub-1-MiB container overhead is
negligible beside the approximately 366.6-MiB exact runtime payload and remains explicitly measured.

**Alternatives considered**: tar (uncompressed package necessarily exceeds bundle size); tar.gz (weaker random-access
member reconciliation and platform metadata pitfalls); zstd (new native dependency); provider cache copy (not closed).

## Provisioning transaction

**Decision**: An explicit script downloads one file at a time into a sibling staging directory, enforces source-lock size
ceilings, hashes before mapping into the install tree, writes deterministic control artifacts, fsyncs, verifies the full
installation, then atomically renames into a previously absent destination.

**Rationale**: Network and disk cannot share a transaction. Every durable state is therefore either an unaccepted staging
tree or one fully validated published installation; ordinary startup never resumes or repairs it.

**Alternatives considered**: download directly into destination; reuse hidden Hugging Face cache layout as authority;
overwrite/update an installed bundle. These expose partial/mutable state.

## Offline proof

**Decision**: Extract the portable package to a fresh path, point every known Hugging Face/Transformers/Docling cache to
fresh empty directories, enable their offline flags, deny socket construction before worker/provider import and invoke the
actual isolated PDF parser. At least three accepted fresh-worker outputs must agree on canonical native and evidence IDs.

**Rationale**: Merely setting `enable_remote_services=False` governs provider APIs, not model downloads. Empty-cache plus
socket denial proves the supplied asset tree is complete.

**Alternatives considered**: rely on airplane mode; parse with the developer's populated cache; mock the provider. None
proves the shipped runtime boundary.

## Benchmark and decision policy

**Decision**: Publish `benchmarks/pdf-bundle/v0.1.0` with inventory/package/validation/conversion/resource/correctness
observations. `PDF_OFFLINE_READY` requires complete coverage, exact package/install reconciliation, zero network attempts,
deterministic accepted output, anchored evidence and all declared size/resource targets; any miss yields
`PDF_OFFLINE_NOT_READY` without waiver.

**Rationale**: One successful parse cannot expose storage, startup or memory cost and must not silently overwrite F020's
historical `unavailable` fact. Independent validation prevents generated prose from becoming authority.

**Alternatives considered**: update F020 in place; report only elapsed time; omit unavailable/failed samples. All violate
measured-claims governance.
