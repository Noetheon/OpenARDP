# Specification Analysis: Alternate Parser Conformance Spike

**Date**: 2026-08-01
**Scope**: Post-implementation Spec Kit analysis and convergence preparation

## Result

No critical, high, medium or low cross-artifact inconsistency remains. The implementation
matches the bounded F016 specification without changing the F006 public contract, any
workspace revision, application version, runtime adapter or dependency.

## Coverage summary

| Inventory | Count | Covered | Result |
|---|---:|---:|---|
| Functional requirements | 26 | 26 | 100% |
| Measurable outcomes | 10 | 10 | 100% |
| User stories | 3 | 3 | 100% |
| Task entries | 42 | 42 | Complete after publication evidence |
| Requirement checklist items | 16 | 16 | Pass |
| Conformance checklist items | 24 | 24 | Pass |

## Requirement-to-evidence review

- **Independent consumption (FR-001–FR-008)**: the digest-pinned executable runs with
  `-I -S`, proves project/third-party imports unavailable, confines regular-file reads and
  independently evaluates all 7 valid, 8 invalid, 1 record-set and 6 vector cases.
- **Alternate production (FR-009–FR-018)**: fixed TXT/CSV inputs produce retained native
  JSON plus all required thin anchors under `stdlib-text-csv` / `deterministic-grid`; three
  runs are byte-identical and reference models accept every record/artifact binding.
- **Decision and claims (FR-019–FR-025)**: manifest, executable, source, observation and
  decision identities are explicit; missing/failed/duplicate/tampered evidence fails closed;
  friction/non-claims remain machine-readable and contract stability stays experimental.
- **Completion (FR-026)**: local and remote gate evidence is recorded in
  `implementation-notes.md`; publication remains the final task until PR/main workflows pass.

## Constitution alignment

- Originals remain unchanged; native and projected outputs are reproducible derivatives.
- The projection stays thin while complete provider-native outputs remain retained.
- All content is data-only with no tool, network, trust or path authority.
- Identities use explicit SHA-256/RFC 8785 envelopes; unsupported numeric values fail closed.
- The decision reports unfavorable evidence and limitations without overstating the claim.
- One bounded feature branch/PR follows F015 convergence and precedes F017.

## Provider-neutrality finding

The evidence supports the narrow thin-contract statement for this measured alternate
implementation. It does not support universal parser neutrality or cross-provider semantic
equivalence. No Docling leakage was observed in contract fields or alternate output. Three
friction classes remain documented: semantic invariants beyond JSON Schema, replicated
purpose-specific identity allowlists and provider-profile meaning for geometry/pointers.
None requires a contract change in F016.

## Remaining risk and publication boundary

The independent implementation shares Python as a language, uses synthetic sources and has
no external adopter. These are explicit limitations rather than hidden failures. A future
external or another-language implementation may add stronger evidence, but is not required
to complete this scoped spike. No convergence remediation task is indicated.
