# Experimental contract candidates

**Status:** Experimental contract program. Feature 006 roots and the Feature 008
`ContextBundle 0.2.0` / `SelectionReceipt 0.1.0` roots are implemented public
schemas; later candidates remain design guidance.

Feature 006 delivers `NativeRepresentation`, `EvidenceReference`, `EvidenceProjection`,
and `TrustClassification` as independently versioned experimental roots under
[`schemas/`](../schemas/README.md). Feature 008 delivers `ContextBundle 0.2.0` and the
body-free `SelectionReceipt 0.1.0` as public roots; their authoritative contracts are
[`specs/008-context-compiler-receipts/contracts/`](../specs/008-context-compiler-receipts/contracts/).
Candidate objects not yet delivered are `SourceIdentity`, `SourceVersion` and
`DerivationRecord`. The included
[`example-selection-receipt.json`](example-selection-receipt.json) is illustrative only
and is not a public schema; it does not describe the delivered F008 receipt shape.

Every implemented schema requires `$schema`, `$id`, an independent `contract_version`, a stability label, canonical
identity rules, a strict extension/unknown-field policy, supported-version behavior, valid/invalid fixtures and migration
notes. Provider-neutral contracts may contain opaque provider-profile pointers but not Docling classes, Python types,
SQLite rows or local filesystem paths.

Contract, application, workspace, provider-profile and export-profile versions evolve independently. Feature 016 must
test the resulting provider-neutral boundary with an independent parser or consumer before stabilization is considered.
