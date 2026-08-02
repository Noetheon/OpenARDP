# Feature 023 prompt — Offline PDF model bundle

## Authoritative request

Reproducibly provision the complete local model boundary required by OpenARDP's reviewed Docling PDF profile, prove that
PDF ingestion remains offline after provisioning and publish decision-bearing size, latency, memory and correctness
evidence.

## Frozen scope

- Preserve the exact Docling `2.114.0` CPU profile delivered by F007: layout and accurate table structure enabled; OCR,
  remote services, external plugins and every optional enrichment disabled.
- Resolve mutable upstream model references to immutable revisions, retain per-file SHA-256 and byte lengths, and record
  reviewed redistribution licenses and provenance.
- Provision only the files required by that profile into an independently verifiable, path-independent bundle. The
  repository does not commit model weights and ordinary OpenARDP installation remains network-free.
- Make connected provisioning an explicit maintainer/operator action with fail-closed staging and atomic publication;
  validation and PDF conversion must work without network access or a pre-populated provider cache.
- Freeze an offline benchmark that measures bundle/archive size, validation, cold/warm conversion, CPU time, peak memory,
  output determinism and source/evidence correctness while retaining unfavorable results.
- The redistributable real-world corpus and semantic question/source evaluation remain sequential Features 024 and 025.

## Completion boundary

Complete the full Spec Kit lifecycle, tests-first implementation, actual bundle provisioning, disconnected PDF execution,
independent benchmark validation, full local gates, one private pull request and green Linux/macOS/Windows CI before
starting Feature 024.
