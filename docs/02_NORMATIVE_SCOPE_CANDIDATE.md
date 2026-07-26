# Candidate public contract scope

Status: **experimental design scope for Feature 006**, not a current public schema or industry standard.

## Candidate public concepts

1. `SourceIdentity` — logical source independent of bytes and location changes where resolvable.
2. `SourceVersion` — immutable digest-bound source snapshot.
3. `NativeRepresentation` — parser-native artifact plus provider/version/config metadata.
4. `EvidenceReference` — stable reference from an evidence projection to native/source material.
5. `EvidenceProjection` — thin provider-neutral search/navigation representation.
6. `DerivationRecord` — reproducible derived artifact lifecycle and dependencies.
7. `TrustClassification` — source data, derived interpretation, trusted policy, executable instruction.
8. `ContextBundle` — bounded evidence selected for a task.
9. `SelectionReceipt` — trace of selected, rejected, omitted, stale and escalated evidence.

## Explicitly non-normative implementation details

- Python classes;
- Pydantic;
- SQLite schema;
- FTS5;
- filesystem paths;
- worker process implementation;
- Docling internal node schema;
- ranking algorithm;
- embedding model;
- MCP server implementation.

## Stability labels

Every public contract must carry one of:

- `internal`;
- `experimental`;
- `candidate`;
- `stable`.

No contract may become `stable` before:

- external users have exercised it;
- migration behavior is defined;
- conformance fixtures exist;
- at least one independent implementation or consumer has tested it.
