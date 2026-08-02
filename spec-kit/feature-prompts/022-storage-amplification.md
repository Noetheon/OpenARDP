# Feature 022 prompt — Storage amplification reduction

## Authoritative request

Systematically reduce the approximately 37.9-times logical text-workspace storage amplification measured by F020 while
preserving exact originals, content identities, provenance, historical evidence, verified retrieval, rebuildable search,
backup/recovery and local-first behavior.

## Frozen scope

- Retain the frozen F020 10,000- and 100,000-block workloads and their original measured result.
- Measure logical bytes, filesystem-allocated bytes, file counts and closed storage categories before and after.
- Preserve SHA-256 identities over the exact logical object bytes and leave authoritative source/native bytes unchanged.
- Permit a lossless internal encoding only for derived canonical block objects, with transparent exact reads and explicit
  corruption handling.
- Remove redundant persisted block/search metadata while keeping indexes disposable and returned evidence verified.
- Advance the workspace revision through an accepted ADR and an explicit backup-first migration; opening a workspace must
  never perform a hidden rewrite.
- Offline PDF provisioning, the real-world corpus and semantic evaluation remain sequential Features 023–025.

## Completion boundary

Complete the full Spec Kit lifecycle, tests-first implementation, migration/recovery evidence, a decision-bearing offline
storage benchmark, independent result validation, full local gates, one private pull request and green
Linux/macOS/Windows CI before starting Feature 023.
