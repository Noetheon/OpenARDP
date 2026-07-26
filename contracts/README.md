# Experimental contract candidates

**Status:** Experimental design guidance only; this is not a public schema or stability commitment.

Feature 006 owns the first minimal provider-neutral contract foundation. Candidate objects are `SourceIdentity`,
`SourceVersion`, `NativeRepresentation`, `EvidenceReference`, `EvidenceProjection`, `DerivationRecord`,
`TrustClassification`, `ContextBundle` and `SelectionReceipt`. The included
[`example-selection-receipt.json`](example-selection-receipt.json) is illustrative only.

Every implemented schema requires `$schema`, `$id`, an independent `contract_version`, a stability label, canonical
identity rules, a strict extension/unknown-field policy, supported-version behavior, valid/invalid fixtures and migration
notes. Provider-neutral contracts may contain opaque provider-profile pointers but not Docling classes, Python types,
SQLite rows or local filesystem paths.

Contract, application, workspace, provider-profile and export-profile versions evolve independently. Feature 016 must
test the resulting provider-neutral boundary with an independent parser or consumer before stabilization is considered.
