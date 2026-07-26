# Experimental contract candidates

**Status:** Experimental contract program. Feature 006 roots are implemented public
schemas; later candidates and the example receipt remain design guidance.

Feature 006 delivers `NativeRepresentation`, `EvidenceReference`, `EvidenceProjection`,
and `TrustClassification` as independently versioned experimental roots under
[`schemas/`](../schemas/README.md). Candidate objects not delivered by F006 are
`SourceIdentity`, `SourceVersion`, `DerivationRecord`, `ContextBundle` and
`SelectionReceipt`. The included
[`example-selection-receipt.json`](example-selection-receipt.json) is illustrative only
and is not a public schema.

Every implemented schema requires `$schema`, `$id`, an independent `contract_version`, a stability label, canonical
identity rules, a strict extension/unknown-field policy, supported-version behavior, valid/invalid fixtures and migration
notes. Provider-neutral contracts may contain opaque provider-profile pointers but not Docling classes, Python types,
SQLite rows or local filesystem paths.

Contract, application, workspace, provider-profile and export-profile versions evolve independently. Feature 016 must
test the resulting provider-neutral boundary with an independent parser or consumer before stabilization is considered.
