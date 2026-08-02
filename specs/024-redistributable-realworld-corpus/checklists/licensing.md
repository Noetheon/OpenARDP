# Requirements Quality Checklist: Corpus Provenance and Redistribution

**Purpose**: Ensure F024 requirements fully define identity, provenance, rights, network and claims boundaries

**Created**: 2026-08-02

**Audience**: Author and private-PR reviewer

## Selection and identity

- [x] CHK001 Is exactly one original publisher file required for each of the six named formats? [Completeness, Spec §FR-001–FR-003]
- [x] CHK002 Are exact path, media, digest, length and descriptive source facts mandatory per payload? [Completeness, Spec §FR-004]
- [x] CHK003 Does corpus identity cover all identity-bearing selection, source, rights and evidence facts? [Clarity, Spec §FR-008]
- [x] CHK004 Are absolute paths, timestamps and host state excluded from corpus identity? [Portability, Spec §FR-008]
- [x] CHK005 Does every byte or identity-bearing metadata change require a deliberate new version? [Governance, US5]

## Rights and provenance

- [x] CHK006 Must every asset map to exactly one source and rights record? [Completeness, Spec §FR-005]
- [x] CHK007 Are NTRS determination and third-party-material facts retained for every NASA source? [Evidence, Spec §FR-006]
- [x] CHK008 Is the CISA revision a full immutable commit with retained CC0 text? [Evidence, Spec §FR-006]
- [x] CHK009 Are trademark, agency-mark, attribution and non-endorsement limits separate from copyright facts? [Clarity, Spec §FR-007]
- [x] CHK010 Do requirements forbid describing automation or review as legal certainty? [Claims, Spec §FR-007, §FR-021]

## Reproduction and security

- [x] CHK011 Is connected fetching restricted to one explicit action and reviewed HTTPS hosts? [Security, Spec §FR-011]
- [x] CHK012 Are response, size, redirect, staging, verification and publication boundaries specified? [Coverage, Spec §FR-011–FR-012]
- [x] CHK013 Do upstream drift, outage and partial responses fail without modifying accepted data? [Failure, US3]
- [x] CHK014 Are ordinary tests, validation, imports and product operation explicitly network-free? [Security, Spec §FR-013]
- [x] CHK015 Is document content always untrusted and unable to initiate side effects? [Security, Spec §FR-014]

## Baseline and claims

- [x] CHK016 Are all six actual parser/provider paths identified without adding a new product abstraction? [Coverage, Plan §Parsing boundary]
- [x] CHK017 Are body-free observation fields and forbidden retained data explicit? [Privacy, Spec §FR-016, §FR-024]
- [x] CHK018 Is determinism measured over accepted contract identities rather than timing/provider internals? [Measurability, Spec §FR-017]
- [x] CHK019 Can an independent validator reproduce the final decision without report prose? [Independence, Spec §FR-019]
- [x] CHK020 Do named hard failures prevent a baseline-ready decision? [Fail closed, Spec §FR-020]
- [x] CHK021 Are result claims bounded from legal certainty and general document quality? [Claims, Spec §FR-021]
- [x] CHK022 Are all semantic questions, rankings and judgments reserved for F025? [Scope, Spec §FR-026]

## Review result

All 22 requirements-quality checks pass with explicit traceability. No critical or high ambiguity remains; task
generation may proceed.
