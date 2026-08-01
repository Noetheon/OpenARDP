# Security model v2

**Status:** Active security requirements and future acceptance boundary. Controls not listed as delivered in the
[README](../README.md) remain roadmap obligations.

## Primary security objective

Prepared document content must remain **data**, not gain authority as agent instructions.

## Mandatory classifications

- `SOURCE_DATA_UNTRUSTED`
- `DERIVED_INTERPRETATION_UNTRUSTED`
- `TRUSTED_POLICY`
- `EXECUTABLE_INSTRUCTION`

Ingestion adapters may only emit the first two. Promotion to trusted policy or executable instruction requires an explicit out-of-band administrative action and is out of scope for v0.1.

## Threats

- indirect prompt injection in source text, tables, images or metadata;
- path traversal and archive bombs;
- parser exploitation and resource exhaustion;
- stale derivative reuse;
- metadata drift between index and authoritative records;
- hash substitution or incomplete integrity checks;
- unsafe URI resolution;
- arbitrary file access through MCP;
- cross-document data exfiltration;
- malicious Docling/native payloads;
- deceptive visual evidence.

## Required controls

- isolated parser worker with network denied by default; treat this as defense-in-depth rather than a portable strong sandbox;
- strict input, page, time, memory and output limits;
- allowlisted local source roots;
- immutable CAS and digest verification;
- no deserialization of executable objects;
- FTS/index hits verified against authoritative CAS objects;
- read-only MCP with object-scoped APIs;
- explicit freshness checks for derivations;
- security fixtures containing injection attempts;
- no model-generated content in trust-policy fields.


## Additional boundaries

- v0.1 is local single-user software, not a multi-tenant authorization system.
- Logs and receipts must avoid secrets, full bodies and unnecessary personal data.
- Cancellation, disk exhaustion and partial-output cleanup fail closed.
- Dependency and release integrity are covered by the supply-chain policy.
- Native parser artifacts are untrusted structured data and must never be deserialized as executable objects.

## Delivered Feature 007 controls

- only PDF, DOCX and PPTX media are accepted by the rich adapter;
- all provider versions and the optional dependency are exact and lockfile-reviewed;
- model manifests require traversal-free POSIX-relative regular files with declared
  license, length and SHA-256; validation is streamed and rejects symlinks/substitution;
- socket construction is denied before provider import and common model clients are
  forced offline;
- source, page, CPU/time, address-space where portable, file-descriptor, native-output,
  projection and retrieval limits fail closed;
- parent cleanup closes IPC, terminates/kills when necessary and reaps the spawned child;
- IPC carries only strict JSON results or allowlisted body-free error categories;
- native/reference/projection/retrieval/bundle objects are digest-verified before cache
  reuse or retrieval;
- pointer resolution accepts only the retained native object, matching provider
  profile/version and bounded local RFC 6901 syntax.

## Delivered Feature 008 controls

- every accelerator hit is reverified against the content-addressed body, catalog
  scope and indexed text hash before scoring; incomplete or drifted coverage fails
  closed and is never repaired implicitly;
- selected bodies travel only inside the delimited `untrusted_data` envelope with
  `instruction_execution_allowed=false`; trust promotion from index or projection
  metadata is impossible because classification reads the reverified body trust;
- the selection receipt, catalog compilation rows, operational logs and CLI error
  envelopes carry identifiers, digests, counts and timings only — never task text,
  evidence bodies or source paths;
- resource bounds (scopes, discovery, candidates, body bytes, decisions, bundle
  units) fail closed before unbounded allocation;
- cancellation checkpoints are bounded and leave no catalog-visible partial
  compilation; pre-published immutable objects remain unreachable recovery candidates;
- replay reuses the recorded exact snapshot and rejects task, estimator, algorithm or
  integrity drift with closed mismatch codes instead of substituting newer content;
- compilation rows are insert-once with recomputed fingerprints; conflicting
  same-identity records fail closed.

These controls reduce exposure but do not prove that Python process isolation,
platform resource limits or the third-party parser are a universally secure sandbox.

## Delivered Feature 009 controls

- MCP is a local newline-delimited JSON-RPC stdio process only; it opens no HTTP or
  other network listener and advertises only the tools capability.
- The nine fixed tools accept registered document, block, evidence and receipt
  identifiers rather than filesystem paths. Path-, traversal-, URL-, shell- and
  control-shaped values are rejected before any source resolver or filesystem access.
- Body-bearing results remain inside the `openardp-evidence-v1` untrusted-data
  envelope. Neither search queries nor context tasks are promoted to instructions or
  echoed into errors, receipts or operational audit records.
- Inbound frames, the 64-frame pending dispatch queue, serialized responses,
  pagination, search results, individual bodies, compilation scopes and request
  duration have explicit fail-closed caps. Single bodies are rejected rather than
  silently truncated; queue overflow unwinds active work and closes the session.
- Unknown and near-miss identifiers share one fixed body-free `not_found` response;
  catalog, index and CAS faults reduce to stable sanitized categories without source
  paths, bodies, exception strings or tracebacks.
- Cancellation and monotonic deadlines reuse the F008 cooperative compilation boundary;
  they expose no partial catalog record and do not alter earlier immutable compilations.
- Startup opens only an existing compatible workspace. It does not initialize, migrate,
  repair, ingest, reindex or invoke a provider.

These controls bound the delivered local single-user interface. They do not provide
multi-tenant authorization or make an untrusted MCP client safe to grant local process
execution; the operator remains responsible for which client may launch the server and
which workspace path is configured out of band.

## Delivered Feature 011 controls

- Visual operations accept registered document/projection identifiers only; arbitrary
  paths, URLs, source bytes and native pointers are not public inputs.
- The optional exact PDFium/Pillow capability runs in a spawned, killable process.
  Source/raster input is transferred in bounded chunks, socket creation and proxy
  variables are denied before provider use, portable CPU/address-space/file-descriptor
  limits apply, and the parent enforces wall/output bounds and reap cleanup.
- Independent source, page-count, dimension, page/crop-pixel, decoded-byte, output,
  metadata, frame and elapsed-time caps fail closed. PNG output is single-frame RGB and
  strips metadata; intrinsic PDF rotation is recorded rather than inferred from EXIF.
- Provider-native geometry is accepted only from the exact retained profile/version;
  aspect mismatch above 1,000 PPM, ambiguity and absent cell geometry fail or carry an
  explicit table-level fallback.
- Raster/crop/descriptor objects are digest-verified before one revision-8 transaction.
  Cancellation or failure before commit exposes no partial visual row; complete
  unreachable CAS residue remains an F013 recovery candidate.
- Rights come only from a trusted policy port and default to local-only, export denied,
  `license_unverified`. No OCR/caption provider is registered by default; explicit
  results remain model-derived data with instruction execution disabled.

The worker is defense in depth, not a universal sandbox. Native decoder defects and
viewer-fidelity differences remain residual risks.
