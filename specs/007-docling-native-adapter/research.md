# Research: Docling Native Adapter

## Decision 1 — Pin Docling as an optional provider extra

**Decision**: Add `docling==2.114.0` under an optional `docling` project extra and
lock the complete cross-platform graph with uv. Keep the base package dependent only on
its current provider-neutral libraries.

**Rationale**:

- Release 2.114.0 was published on 2026-07-20, supports Python 3.10–3.14 and
  Linux/macOS/Windows on x86_64 and arm64, and is the current reviewed release.
- PyPI records MIT licensing, Trusted Publishing provenance, source commit
  `30ac7809612ec157792109f40482e14bc2c55001`, and Sigstore publication
  attestations.
- The package delegates to exactly matched `docling-slim[standard]==2.114.0`.
- An optional extra preserves the small local-first core and lets F006 consumers validate
  evidence without importing a parser provider.
- Repository CI already synchronizes `--all-extras`, so optional does not mean untested.

**Rejected alternatives**:

- Mandatory base dependency: rejected because it makes the provider and its large
  scientific graph unavoidable for contract-only consumers.
- Loose `2.x` range: rejected because native shape, security behavior and reproducibility
  would drift under the same provider profile.
- Unlocked source checkout: rejected because it weakens repeatability and supply-chain
  review.

**Primary evidence**:

- <https://pypi.org/project/docling/2.114.0/>
- <https://docling-project.github.io/docling/getting_started/installation/>
- <https://github.com/docling-project/docling/releases/tag/v2.114.0>

## Decision 2 — Allowlist only PDF, DOCX and PPTX

**Decision**: Construct the converter with an explicit format allowlist and do not expose
any other Docling backend in F007.

**Rationale**:

- The feature prompt names exactly these formats.
- Docling has published 2026 advisories for EasyOCR model extraction, USPTO XML,
  METS-GBS archives/XML, LaTeX paths, HTML URI/path handling and HTML rendering.
  Version 2.114.0 is newer than the documented patched releases, but unused high-risk
  formats still should not be reachable.
- The selected release plus format allowlisting, source-byte streaming, offline mode and
  worker isolation provide layered defense.

**Rejected alternatives**:

- Expose every format supported by the installed provider: rejected as unreviewed scope
  and avoidable attack surface.
- Depend on suffix detection alone: rejected because the adapter must receive an explicit
  reviewed media type and still let the provider reject malformed content.

**Primary evidence**:

- <https://github.com/docling-project/docling/security/advisories>
- <https://docling-project.github.io/docling/reference/document_converter/>

## Decision 3 — Strictly offline profile with local PDF assets

**Decision**: Disable OCR, picture enrichment/captioning, remote services and automatic
downloads. DOCX and PPTX use declarative local backends. PDF requires a configured local
artifact root plus a validated model-bundle manifest.

**Rationale**:

- Official guidance states that Docling runs offline when model artifacts are
  pre-provisioned and `PdfPipelineOptions.artifacts_path` points to them.
- Official advanced options state that default first use may download models; relying on
  that default would violate OpenARDP's no-egress baseline.
- A path-independent manifest of relative file names, lengths, SHA-256 identities and
  license identifiers makes the model bundle reviewable and recipe-significant.

**Rejected alternatives**:

- Transparent first-use download: rejected because it is network egress, supply-chain
  mutation and an availability/privacy surprise.
- Hash only the local directory path: rejected because paths do not identify bytes and
  leak operator-specific details.
- Vendor model weights: rejected because model licensing, repository size and release
  governance are outside F007.

**Primary evidence**:

- <https://docling-project.github.io/docling/faq/#how-do-i-run-completely-offline>
- <https://docling-project.github.io/docling/usage/advanced_options/>

## Decision 4 — Retain canonical complete DoclingDocument JSON

**Decision**: The native export profile `openardp-docling-document-json-v1` calls the
provider's lossless document export with aliases and explicit nulls retained, validates
the value as safe interoperable JSON, and stores deterministic RFC 8785 bytes. Docling
2.114 emits `origin.binary_hash` as an unsigned 64-bit integer that can exceed the
I-JSON safe-integer range; the profile losslessly serializes exactly that scalar as its
decimal string. Every digit remains recoverable, while any other unsafe integer or
non-finite value fails closed. No native field is projected away or otherwise rewritten.

**Rationale**:

- `DoclingDocument.export_to_dict` is the provider's supported lossless JSON boundary.
- RFC 8785 Appendix D requires application-level handling for integers outside the
  interoperable IEEE-754 range; decimal-string encoding avoids truncation.
- Canonical storage removes object-order and number-spelling ambiguity while retaining
  the complete provider document value.
- Conversion runtime timings, machine/platform fields and local input paths are not part
  of the provider document and would undermine reproducibility/privacy if the entire
  `ConversionResult` were retained.
- The separate descriptor records exact component versions, profile, model identity and
  nondeterminism caveats.

**Rejected alternatives**:

- Store Markdown/HTML: rejected because those are lossy exports.
- Store a pickled provider object: rejected because it is executable deserialization and
  Python-specific.
- Store complete `ConversionResult`: rejected because it mixes native document evidence
  with nondeterministic runtime telemetry and local path facts.
- Normalize all provider nodes into OpenARDP models: rejected by ADR 0008.

**Primary evidence**:

- <https://docling-project.github.io/docling/reference/docling_document/>
- [ADR 0008](../../docs/adr/0008-preserve-provider-native-representations.md)

## Decision 5 — Derive a small deterministic evidence view

**Decision**: Traverse only reviewed Docling JSON collections and generate bounded
candidates in provider order:

1. text and heading nodes enter a deterministic Unicode text view and receive half-open
   text-span anchors;
2. table cells receive table-cell anchors scoped to the table `self_ref`;
3. pictures with valid provenance receive fixed-point page-region anchors;
4. other reviewed nodes receive opaque provider-pointer anchors;
5. unrecognized nodes remain available in native JSON but are not guessed into a neutral
   semantic type.

**Rationale**:

- This covers F006 anchor types without duplicating the provider tree.
- Native `self_ref` values are JSON references, not filesystem paths or URLs.
- Exact traversal and tie-breaking rules make ordering testable.
- Conservative omission is safer than inventing meaning for unknown provider labels.

**Rejected alternatives**:

- Project every native field: rejected as a second full rich IR.
- Use provider object instances in contracts: rejected as provider/runtime leakage.
- Treat pointer strings as arbitrary JSONPath/path expressions: rejected because that
  expands authority beyond reviewed native references.

## Decision 6 — Reuse representation lifecycle and add rich catalog facts

**Decision**: Keep the existing document/source/representation acquisition, lease,
failure, head and event machinery. Add a checksummed migration with:

- one rich-artifact row per READY representation;
- one body-free row per evidence record;
- object references for descriptor, provider-native JSON, native F006 record, bundle,
  references, projections and retrieval bodies.

The existing F002 manifest and exact source object remain on the base representation.
Rich facts commit in the same SQLite transaction as READY/head/event publication.

**Rationale**:

- The current lifecycle already handles idempotent acquisition, stale leases, retries,
  append-only events and head advancement.
- A dedicated rich extension preserves existing text semantics and avoids overloading
  the historical `native_object_id`, which currently identifies exact source bytes.
- Object references keep F007 artifacts visible to later reachability/retention work.

**Rejected alternatives**:

- A separate job/catalog framework: rejected as duplicated lifecycle machinery.
- Reinterpret the existing `native_object_id` as Docling output: rejected because current
  text invariants and rows bind it to original source bytes.
- Store an unreferenced sidecar manifest only in CAS: rejected because cache validation
  and future retention could not discover it authoritatively.

## Decision 7 — Use bounded spawned IPC, not a sandbox claim

**Decision**: Extend the established spawned-worker pattern with:

- network denial and offline environment before provider import;
- streamed source bytes and no source path;
- timeout plus kill/close guard;
- POSIX CPU/address-space/file-descriptor limits where supported;
- explicit page, input, native-output, projection and body limits on all platforms;
- one strict JSON-safe result protocol and stable body-free error codes.

**Rationale**:

- Spawn avoids inheriting unsafe parser state and works on all supported platforms.
- The parent can terminate a hung/crashed child and validate all output before storage.
- Python monkeypatching and POSIX resource limits are useful defense-in-depth but do not
  form a universal strong sandbox, especially on Windows.

**Rejected alternatives**:

- In-process conversion: rejected because crashes/resource abuse cannot be cleanly
  contained.
- Docker-only isolation: rejected because it is not portable or a default local
  dependency.
- Claiming OS-level sandboxing: rejected because the controls differ by platform.

## Decision 8 — Fail closed on partial success and nondeterminism

**Decision**: Accept only complete provider success. Every successful parse creates an
append-only `RichParseAttempt`. A forced reparse records whether its complete native and
evidence identities converge with the accepted attempt. Differing valid output is
retained as a `DIVERGED` attempt under its own content identities, while the accepted
READY representation and current head remain unchanged.

**Rationale**:

- Partial output cannot truthfully satisfy the complete-native-artifact claim.
- Content-addressed storage naturally converges identical output and preserves differing
  output.
- Docling/model/platform changes may produce legitimate byte differences; evidence must
  measure rather than conceal them.
- Separating accepted representation state from parse-attempt evidence prevents
  nondeterministic output from silently redefining an immutable recipe/source result.

**Rejected alternatives**:

- Accept partial success with warnings: rejected for the initial profile because callers
  could mistake incomplete evidence for complete.
- Overwrite the prior native object on forced reparse: impossible under CAS and contrary
  to evidence preservation.

## Resource defaults

| Limit | Default | Accepted configuration | Failure |
|---|---:|---:|---|
| source bytes | 100 MiB | fixed by existing source boundary | `source_limit` |
| pages | 500 | 1–2,000 | `page_limit` |
| elapsed time | 120 s | 1–3,600 s | `timeout` |
| POSIX address space | 4 GiB | 1–32 GiB | `resource_limit` |
| open descriptors | 64 | 32–1,024 | `resource_limit` |
| native JSON | 256 MiB | 1–1,024 MiB | `native_output_limit` |
| projections | 100,000 | 1–100,000 | `projection_limit` |
| one retrieval body | 8 MiB | 1 KiB–64 MiB | `retrieval_limit` |
| aggregate retrieval | 256 MiB | 1–1,024 MiB | `retrieval_limit` |
| provider pointer | 2,048 code points | F006 fixed | `invalid_output` |

The worker's CPU soft limit is the configured elapsed deadline rounded up plus a small
cleanup allowance. Windows enforces portable semantic/output/time bounds but not POSIX
RLIMIT controls.

## Supply-chain review snapshot

| Dimension | Finding |
|---|---|
| Project | LF AI & Data hosted, active public repository |
| Package | `docling==2.114.0`, exact `docling-slim[standard]==2.114.0` dependency |
| Resolved provider components | `docling-core==2.87.1`, `docling-parse==7.8.1`, `docling-ibm-models==3.13.3`, `torch==2.13.0` |
| Python/platform | Python 3.10–3.14; Linux/macOS/Windows; x86_64/arm64 |
| License | Code MIT; model licenses must be reviewed independently |
| Publication | PyPI Trusted Publishing and Sigstore attestations |
| Advisories | Six published 2026 advisories; reviewed version is newer than patched releases |
| Scope reduction | Only PDF/DOCX/PPTX; no EasyOCR, XML, LaTeX, HTML or renderer path |
| Network | Disabled profile; no automatic models or remote service |
| Lock | uv lock checked on all supported CI platforms |

This is a point-in-time review, not a claim that the dependency graph is permanently
vulnerability-free.
