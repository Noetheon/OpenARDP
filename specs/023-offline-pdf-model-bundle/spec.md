# Feature Specification: Offline PDF Model Bundle

**Feature Branch**: `codex/f023-offline-pdf-model-bundle`

**Created**: 2026-08-02

**Status**: Converged — see the [authoritative feature map](../../spec-kit/FEATURE_MAP.md)

**Input**: Reproducibly provision and measure the complete offline model boundary required for OpenARDP PDF ingestion.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Provision One Reproducible PDF Bundle (Priority: P1)

As a local operator preparing an offline installation, I can explicitly build one reviewed PDF model bundle from immutable
upstream revisions and obtain a complete manifest, provenance record and redistribution notices.

**Why this priority**: F020 could not exercise PDF because the exact local assets had never been provisioned. A provider
cache assembled from mutable branches is not sufficient evidence for a dependable or air-gapped product.

**Independent Test**: Provision into a new destination from an empty provider cache, independently hash every regular
file and reconstruct the bundle identity solely from committed source locks and the generated manifest.

**Acceptance Scenarios**:

1. **Given** an empty destination and network access for this explicit action, **When** provisioning completes, **Then**
   the destination contains exactly the reviewed runtime files, license texts, provenance and path-independent manifest.
2. **Given** the same immutable sources, **When** provisioning is repeated elsewhere, **Then** file bytes, manifest and
   bundle identity are identical even though absolute paths differ.
3. **Given** a failed, interrupted or mismatching download, **When** provisioning stops, **Then** no partially accepted
   destination is published and the failure contains no credentials, cache paths or raw response body.

---

### User Story 2 - Convert PDFs Without Any Network or Hidden Cache (Priority: P1)

As an offline operator, I can ingest PDF bytes through the existing isolated Docling path using only the validated bundle,
with every model-download and remote-service path disabled.

**Why this priority**: A downloadable archive is not an offline capability unless the real parser succeeds with sockets
denied and with an empty provider cache.

**Independent Test**: Extract the bundle to a fresh path, redirect all provider caches to empty temporary directories,
deny socket construction before provider import and convert the frozen synthetic PDF in a spawned worker.

**Acceptance Scenarios**:

1. **Given** a valid extracted bundle and empty provider caches, **When** the frozen PDF is ingested with network denied,
   **Then** conversion succeeds and returns verified native and thin evidence without a network attempt.
2. **Given** no bundle, an incomplete bundle or one changed byte, **When** PDF ingestion is requested, **Then** it fails
   closed before provider execution and returns no partial evidence.
3. **Given** valid model bytes plus an extra regular file, link or unsupported path, **When** validation runs, **Then** the
   bundle is rejected rather than silently broadening the executable/data boundary.

---

### User Story 3 - Transfer and Verify the Bundle Offline (Priority: P1)

As an operator moving assets into an air-gapped environment, I can create a deterministic portable package, transfer it,
extract it safely and verify it independently before OpenARDP uses any model file.

**Why this priority**: Offline provisioning requires a closed transfer artifact rather than an undocumented directory
that must be trusted after copying.

**Independent Test**: Build the portable package twice, compare its digest, extract it into fresh disjoint roots, verify
every path and byte, then prove that traversal, links, duplicate entries, trailing data and archive expansion violations
fail closed.

**Acceptance Scenarios**:

1. **Given** a validated bundle, **When** a portable package is created twice, **Then** the package bytes and digest are
   deterministic for the same bundle.
2. **Given** a fresh offline machine with the locked Python distribution set and the portable package, **When** the
   package is safely extracted and verified, **Then** no network access or provider cache is needed for PDF conversion.
3. **Given** a hostile or corrupt package, **When** extraction is attempted, **Then** nothing is published outside the
   destination and no unverified bundle becomes usable.

---

### User Story 4 - Reproduce the Offline PDF Readiness Decision (Priority: P2)

As a maintainer, I can run and independently validate a versioned benchmark that reports whether PDF is genuinely ready
offline and exposes its storage, time, memory and output-quality costs.

**Why this priority**: The project constitution forbids replacing the F020 `unavailable` observation with an unsupported
claim. Readiness must be based on retained machine evidence, including unfavorable measurements.

**Independent Test**: Run the frozen protocol from a fresh extracted bundle and empty caches, regenerate all summaries
and the decision from raw observations, then alter one observation to prove independent validation fails.

**Acceptance Scenarios**:

1. **Given** a valid bundle and reference environment, **When** the benchmark runs, **Then** it records file/archive size,
   validation latency, cold/warm wall and CPU time, peak memory, output size, projections and exact correctness judgments.
2. **Given** retained raw evidence, **When** the independent validator runs, **Then** it recomputes all summaries,
   identities and the readiness decision without trusting report prose.
3. **Given** a timeout, nondeterministic output, missing anchor, network attempt, resource breach or target miss, **When**
   the report is generated, **Then** the unfavorable result remains explicit and PDF is not labelled ready.

---

### User Story 5 - Audit Model Rights and Supply Chain (Priority: P2)

As a maintainer or downstream redistributor, I can see which immutable upstream revisions and licenses supplied every
bundle file and can distinguish verified bytes from legal review assertions.

**Why this priority**: Hashes prove identity, not permission. Sustainable redistribution requires both mechanical
provenance and reviewable licensing facts without claiming legal certainty.

**Independent Test**: Reconcile every bundled file to exactly one locked upstream source and license assertion, verify
the included license texts and reject unknown, conflicting or mutable source records.

**Acceptance Scenarios**:

1. **Given** the reviewed source lock, **When** an auditor follows the provenance, **Then** each payload file maps to one
   repository, immutable revision, upstream path, digest, byte length and license identifier.
2. **Given** a missing or ambiguous license assertion, **When** provisioning is requested, **Then** it fails before
   publication and no redistribution-ready claim is emitted.
3. **Given** complete assertions, **When** the report is generated, **Then** it describes review evidence without calling
   the automated check legal advice or ownership proof.

### Edge Cases

- A mutable branch advances after the committed immutable revision was selected.
- A hosting service returns a pointer file, HTML error page, truncated stream or bytes with the expected length but wrong
  digest.
- Destination, cache or archive paths contain links, aliases, non-regular files, case-fold collisions or Unicode
  normalization collisions.
- Provisioning is interrupted before download, during hashing, after staging or immediately before publication.
- The destination already exists, lacks sufficient capacity or resides on a filesystem without atomic directory rename.
- Archive metadata attempts absolute/traversal paths, devices, links, duplicate entries, extreme expansion or timestamp
  nondeterminism.
- A bundle is complete but contains an unlisted file or a listed file no longer required by the frozen PDF profile.
- Provider environment variables point to populated global caches while the offline proof expects empty caches.
- The first PDF conversion initializes models slowly or reaches the existing worker time/memory limits.
- CPU inference differs across supported platforms or produces stable evidence with non-identical provider internals.
- Upstream license metadata changes without any payload-byte change.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST preserve F020's committed PDF `unavailable` observation as historical evidence and MUST
  publish new F023 evidence separately.
- **FR-002**: The supported bundle MUST contain only assets required by the exact F007 Docling `2.114.0` PDF profile:
  layout and accurate table structure, with OCR, remote services, external plugins and enrichments disabled.
- **FR-003**: Every upstream source MUST be locked by repository identifier and full immutable revision; mutable branch,
  tag-only or latest-version resolution MUST NOT occur during verification or offline use.
- **FR-004**: The committed source lock MUST declare an allowlist of upstream paths, SHA-256, byte length, source URL,
  destination path and reviewed license identifier for every payload file.
- **FR-005**: Connected provisioning MUST be an explicit operator/maintainer action and MUST NOT run during package
  installation, import, workspace open, ingestion without supplied assets, tests or ordinary CLI startup.
- **FR-006**: Provisioning MUST stream into a disjoint staging directory, enforce per-file and aggregate byte limits,
  verify length and SHA-256 before publication and remove or leave only clearly unaccepted staging data after failure.
- **FR-007**: A valid bundle MUST include the exact runtime payload, canonical manifest, immutable provenance record,
  redistribution notices and complete reviewed license texts.
- **FR-008**: Bundle identity MUST remain the existing RFC 8785/SHA-256 `ModelBundleManifest` identity and MUST be
  independent of absolute paths, host, cache and creation time.
- **FR-009**: Validation MUST reject missing, extra, duplicate, linked, non-regular, traversal, case-colliding,
  normalization-colliding, length-mismatched or digest-mismatched files before provider import.
- **FR-010**: Validation MUST operate offline, perform no mutation and complete using only the bundle root, committed
  source lock and bounded local resources.
- **FR-011**: Portable packaging MUST be deterministic for identical bundle bytes and MUST use a bounded,
  independently verifiable archive profile with normalized metadata and sorted entries.
- **FR-012**: Safe extraction MUST reject absolute/traversal paths, links, devices, duplicate names, unlisted files,
  excessive entries, per-file overflow, aggregate expansion overflow and trailing unconsumed data.
- **FR-013**: Package extraction MUST publish only a completely verified fresh destination and MUST NOT overwrite an
  existing bundle or write outside the selected destination.
- **FR-014**: The existing PDF conversion boundary MUST require a validated bundle and MUST use only the files declared
  by its manifest; no global cache or environment variable may satisfy a missing bundle file.
- **FR-015**: Offline proof MUST redirect provider/model caches to fresh empty directories, deny socket construction
  before provider import and treat any network attempt as a hard failure.
- **FR-016**: PDF conversion MUST retain the existing CPU-only, one-thread, bounded-worker profile and existing source,
  page, time, address-space, output and projection limits.
- **FR-017**: Successful conversion MUST retain exact source identity, a complete canonical provider-native artifact,
  thin provider-neutral projections, verified evidence anchors and the bundle identifier in the parser recipe.
- **FR-018**: Repeated conversions from identical PDF bytes and bundle MUST not invoke connected provisioning and MUST
  produce the same accepted evidence identities and canonical native bytes on the declared binding environment.
- **FR-019**: A versioned benchmark MUST retain raw body-free observations for bundle inventory, deterministic package,
  validation, cold conversion, warm conversions, offline/cache isolation, output correctness and resource bounds.
- **FR-020**: Timing groups MUST declare warm-up and retained sample counts and report p50, p95, median absolute
  deviation and deterministic confidence intervals where sample size permits.
- **FR-021**: Measurements MUST include logical bundle/package bytes, regular-file count, provisioning bytes and duration,
  validation wall/CPU time, conversion wall/CPU time, peak resident memory, native bytes, projection count and page count.
- **FR-022**: Benchmark artifacts MUST contain no absolute paths, source text, extracted bodies, credentials, hostnames,
  usernames, cache contents, raw exceptions or remote response bodies.
- **FR-023**: An independent validator MUST recompute file inventories, manifest/package identities, summaries,
  correctness judgments and the final decision from retained evidence rather than trusting generated Markdown.
- **FR-024**: PDF readiness MUST fail closed on any missing/corrupt asset, network attempt, nondeterministic accepted
  output, source/evidence mismatch, timeout, resource-limit breach or incomplete benchmark coverage.
- **FR-025**: The feature MUST report measured results as workload- and environment-bounded and MUST NOT imply semantic
  answer quality, general real-world PDF quality or release readiness.
- **FR-026**: Errors, logs and results MUST expose only stable categories, counts, opaque identities, declared revisions,
  byte totals and durations; credentials, bodies, absolute paths and raw provider/network exceptions are prohibited.
- **FR-027**: Model weights and generated portable packages MUST remain outside Git history; the repository MUST retain
  only source locks, manifests/templates, deterministic tooling and body-free benchmark evidence.
- **FR-028**: Unit and cross-platform CI tests MUST use small synthetic model-bundle fixtures and no network; the actual
  heavyweight reference bundle and conversion are an explicit local benchmark input, not an implicit CI download.
- **FR-029**: The default installation and non-PDF behavior MUST add no network call, cloud service, telemetry, mandatory
  model dependency or new workspace migration.
- **FR-030**: F024 corpus selection and F025 semantic question/source evaluation MUST remain out of scope.

### Non-Goals and Compatibility Impact

- **Non-goal**: Enable OCR, VLMs, picture classification/description, chart/code/formula enrichment or remote services.
- **Non-goal**: Judge real-world parsing quality, semantic answer quality or model-training provenance.
- **Non-goal**: Commit, silently download or automatically update model weights.
- **Non-goal**: Replace Docling, its native representation or the existing provider-neutral projection contract.
- **Compatibility impact**: Additive maintainer tooling, benchmark artifacts and stricter model-root validation. No
  workspace migration or persisted identifier/schema algorithm changes; the F007 provider profile version may advance
  only if required to bind the newly closed file-set semantics.

### Key Entities

- **Model Source Lock**: Immutable upstream repository/revision plus an allowlisted mapping of exact source bytes,
  destination paths and reviewed licensing assertions.
- **Offline PDF Bundle**: Closed regular-file tree containing the exact runtime payload and review material.
- **Model Bundle Manifest**: Existing path-independent canonical inventory and identity consumed by the parser boundary.
- **Portable Bundle Package**: Deterministic bounded transfer representation of one validated bundle.
- **Provisioning Observation**: Body-free fact about one explicit connected retrieval and publication attempt.
- **Offline PDF Benchmark Run**: Frozen protocol, environment buckets, observations, summaries and decision for one
  validated bundle and PDF fixture set.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Two provisions from empty destinations produce byte-identical manifests, identical bundle IDs and zero
  unreviewed payload files.
- **SC-002**: Independent validation detects 100% of the defined missing, extra, link, traversal, collision, truncation,
  length, digest and archive-tampering cases before model use.
- **SC-003**: The complete reviewed runtime bundle is no larger than 450 MiB logical bytes and the deterministic portable
  package adds no more than 1 MiB of fixed container overhead.
- **SC-004**: Three fresh-worker conversions of the frozen synthetic PDF with empty caches and sockets denied complete
  within the existing 120-second per-run limit and 4 GiB address-space bound on the binding environment.
- **SC-005**: All accepted repeated conversions have zero network attempts, exact source identity, identical canonical
  native bytes, identical evidence identities and at least one page-anchored evidence projection.
- **SC-006**: Bundle validation completes in at most 5 seconds p95 and uses at most 512 MiB peak resident memory on the
  declared binding environment.
- **SC-007**: The frozen benchmark retains 100% of required observation groups and its independent validator reproduces
  every summary and the `PDF_OFFLINE_READY` or `PDF_OFFLINE_NOT_READY` decision exactly.
- **SC-008**: A clean cross-platform repository run passes all existing quality gates without network access or model
  download, while the actual heavyweight reference result is independently reproducible from the documented package.
- **SC-009**: Every bundled payload file maps to exactly one immutable source revision and one reviewed license assertion;
  no automated output describes that mapping as legal advice or proof of ownership.

## Assumptions

- The binding reference environment is the current Apple-silicon macOS host; Linux and Windows CI validate portable
  semantics with synthetic bundles rather than repeatedly downloading approximately 400 MiB of weights.
- The exact F007 profile needs the default layout model and accurate TableFormer files only; disabled OCR and enrichment
  models are intentionally excluded from the complete runtime boundary.
- A connected maintainer can access the reviewed upstream hosting service once to create a portable package; all later
  validation and PDF execution must work offline.
- Hosting availability and download speed are measured observations, not product performance targets.
- License assertions are evidence for human review and redistribution hygiene, not legal advice.
