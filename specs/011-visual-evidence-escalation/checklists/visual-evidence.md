# Requirements Quality Checklist: Visual Evidence Escalation

**Purpose**: Challenge requirement completeness, clarity, consistency and traceability
before task decomposition. This checklist tests the written requirements, not the code.
**Created**: 2026-08-01
**Feature**: [spec.md](../spec.md)
**Depth**: Release-blocking

## Scope and authority

- [x] CHK001 Is the accepted visual target limited to exact registered F006/F007 facts rather than paths, URLs or raw pointers? [Completeness, Spec FR-001–FR-002]
- [x] CHK002 Is original-source authority distinguished from derived page/crop and interpreted OCR/caption data? [Clarity, Spec Clarifications]
- [x] CHK003 Is the thin descriptor boundary explicit enough to prohibit a second complete layout model? [Clarity, Spec FR-003]
- [x] CHK004 Are PDF concrete support and honest DOCX/PPTX unavailability stated consistently? [Consistency, Spec FR-009–FR-010, Assumptions]
- [x] CHK005 Are F012, F013 and F014 responsibilities excluded without omitting required F011 handoff facts? [Scope, Spec Non-Goals]

## Identity and provenance

- [x] CHK006 Does every semantic identity input have a named place in the descriptor/preimage? [Completeness, Spec FR-003–FR-004]
- [x] CHK007 Are direct object identity and descriptor identity distinguished? [Clarity, Data Model §8]
- [x] CHK008 Are timestamp/extension inclusion rules explicit enough for retry and vector expectations? [Clarity, Data Model §8]
- [x] CHK009 Do changed source, target, renderer, scale, encoder/config and output-affecting limits have defined cache-identity effects? [Coverage, Spec FR-015]
- [x] CHK010 Is provenance sufficient to reverify source/native/reference/projection/raster/crop scope without provider imports? [Measurability, Spec FR-001, FR-003, FR-016]

## Geometry and table evidence

- [x] CHK011 Are coordinate systems, page numbering, integer rounding and half-open pixel bounds unambiguous? [Clarity, Spec FR-005–FR-006]
- [x] CHK012 Are clamping and inferred geometry repair prohibited, with parser/renderer aspect mismatch governed by a fixed 1,000-PPM fail-closed rule? [Clarity, Clarification §crop boundaries]
- [x] CHK013 Are rotation, orientation, scale and raster dimensions all auditable and mutually constrained? [Completeness, Spec FR-006]
- [x] CHK014 Does `cell_exact` require explicit geometry and does fallback retain row/column/span/table identity? [Safety, Spec FR-007]
- [x] CHK015 Is text/model-based cell geometry inference expressly prohibited? [Safety, Clarifications and Contract §Table granularity]
- [x] CHK016 Are missing/multiple/inconsistent native provenance cases covered by fail-closed or explicit fallback behavior? [Edge coverage, Spec Edge Cases]

## Rendering, isolation and resources

- [x] CHK017 Is the optional dependency boundary consistent with the local-first core guarantee? [Consistency, Spec FR-009]
- [x] CHK018 Are concrete deterministic PDF/PNG profile choices sufficient to reproduce output without claiming universal viewer fidelity? [Clarity, Research Decision 3]
- [x] CHK019 Are encoded, decoded, dimension, pixel, output, metadata, frame, time, memory and file caps independently specified? [Completeness, Spec FR-011]
- [x] CHK020 Are timeout, cancellation, crash, encryption, malformed input, bomb detection and provider absence mapped to closed outcomes? [Coverage, Spec FR-012]
- [x] CHK021 Is worker cleanup described without overstating process isolation as a strong sandbox? [Accuracy, Research Decision 6]
- [x] CHK022 Can cached raster decoding receive the same image-bomb protections as first rendering? [Consistency, Research Decision 4]
- [x] CHK023 Are network denial and provider import ordering explicit for the optional worker? [Security, Research Decision 6]

## Atomicity, cache and recovery

- [x] CHK024 Are the page-raster cache and target crop record independently identified and transactionally related? [Completeness, Research Decision 7]
- [x] CHK025 Does CAS-first publication plus one catalog commit define what readers may observe at every fault boundary? [Atomicity, Spec FR-014]
- [x] CHK026 Are exact retry convergence and same-identity conflict rules distinct? [Clarity, Spec FR-014–FR-015]
- [x] CHK027 Does the design eliminate repeat page rendering across multiple crops rather than only duplicate crops? [Value, SC-002]
- [x] CHK028 Are unreachable complete objects explicitly assigned to F013 rather than called corruption or deleted? [Recovery, Spec Non-Goals]
- [x] CHK029 Are visual page/crop/descriptor objects included in reachability and migration requirements? [Coverage, Spec FR-025]

## Context compiler behavior

- [x] CHK030 Is rendering explicitly separate from F008 compilation and F009 authority? [Boundary, Spec FR-018, FR-024]
- [x] CHK031 Does a visual item use an existing handle-capable ContextBundle shape without altering prior public bytes? [Compatibility, Spec FR-017, FR-027]
- [x] CHK032 Are current-snapshot freshness, historical exclusion and replay non-floating behavior specified? [Freshness, Spec FR-016]
- [x] CHK033 Is visual candidate cost defined without embedding image bytes in budgeted JSON? [Budget, Spec FR-019]
- [x] CHK034 Does missing visual evidence remain explicit in both bundle and receipt when no candidate qualifies? [Honesty, Spec FR-018]
- [x] CHK035 Is one canonical context recipe per target sufficient to avoid duplicate F006 evidence ids? [Ambiguity, Research Decision 8]

## OCR, captions, trust and rights

- [x] CHK036 Are OCR/caption ports explicit, optional and unregistered by default? [Clarity, Spec FR-020]
- [x] CHK037 Is every accepted interpretation bound to exact crop/provider/model/config/prompt identities and F010 lifecycle without falsely claiming object-only head invalidation? [Traceability, Spec FR-020–FR-021]
- [x] CHK038 Are model-derived trust, role-data and no-instruction constraints non-negotiable? [Security, Spec FR-021]
- [x] CHK039 Is low-confidence OCR required to retain crop evidence and barred from satisfying visual/exact verification alone? [Evidence, Spec FR-022]
- [x] CHK040 Can document, native, EXIF or model metadata relax neither orientation policy nor export rights? [Anti-escalation, Spec FR-013, FR-023]
- [x] CHK041 Is the unknown-rights default machine-enforceable for F014? [Handoff, Contract §Rights contract]

## Compatibility, validation and operations

- [x] CHK042 Are all compatibility axes classified independently and is ADR 0012 required before implementation? [Governance, Spec FR-026]
- [x] CHK043 Is the freeze boundary explicit for all eleven prior schemas, F006/F007/F008/F009 artifacts and identities? [Compatibility, Spec FR-027]
- [x] CHK044 Do fixtures cover valid page/region/cell/fallback roots and invalid identity/trust/rights/geometry/version cases? [Coverage, Contract §Conformance minimum]
- [x] CHK045 Are security tests synthetic/redistributable, network-disabled and required on all platforms? [Quality, Spec FR-029]
- [x] CHK046 Are logs/errors/rows/receipts body/path/metadata/prompt safe by default? [Privacy, Spec FR-028]
- [x] CHK047 Are upgrade, concurrent initialization, too-new rejection, rollback backup and recovery limitations all stated? [Operations, Spec FR-025, Quickstart §9]
- [x] CHK048 Do success criteria test exact geometry, byte convergence, fallback honesty, fault atomicity, context freshness, trust and compatibility without unsupported claims? [Measurability, Spec SC-001–SC-010]

## Traceability summary

- Functional requirements traced: 30/30 (100%).
- Success criteria traced: 10/10 (100%).
- User stories traced: 4/4 (100%).
- Unresolved requirement-quality findings: 0.

**Result**: PASS. Planning may proceed to task decomposition and read-only consistency
analysis.
