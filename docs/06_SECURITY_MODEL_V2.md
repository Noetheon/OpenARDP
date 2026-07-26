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

These controls reduce exposure but do not prove that Python process isolation,
platform resource limits or the third-party parser are a universally secure sandbox.
