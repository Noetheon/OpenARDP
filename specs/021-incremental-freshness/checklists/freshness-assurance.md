# Freshness Assurance Checklist: Incremental Freshness Status

**Purpose**: Test whether the requirements define exact freshness, bounded integrity claims, concurrency behavior and
reproducible performance evidence completely enough for implementation.
**Created**: 2026-08-02
**Feature**: [spec.md](../spec.md)

**Note**: This checklist evaluates the requirements themselves, not whether the implementation already passes them.

## Claim Boundaries

- [x] CHK001 Is exact source identity defined independently of metadata-only shortcuts? [Spec FR-001]
- [x] CHK002 Is the meaning of bounded head-level coverage distinguishable from complete artifact verification? [Spec FR-004, FR-006]
- [x] CHK003 Is the default path prohibited from implying arbitrary CAS tamper detection? [Spec US2, Non-Goals]
- [x] CHK004 Is full coverage permitted only after all existing verifier checks succeed during the same request? [Spec FR-005, FR-006]
- [x] CHK005 Are unchanged, changed, missing, unregistered, unprepared and invalid states retained explicitly? [Spec FR-002]
- [x] CHK006 Is the weaker assurance of the optimized path required to remain prominent in decision evidence? [Spec SC-010]

## Complexity and Performance

- [x] CHK007 Is the sublinear claim scoped to prepared block count rather than source byte length? [Spec Assumptions]
- [x] CHK008 Are projection enumeration and block-object reads prohibited independently, not inferred only from latency? [Spec FR-003, SC-002]
- [x] CHK009 Is the decision-bearing latency threshold stated for both frozen scales and a named environment? [Spec SC-001]
- [x] CHK010 Are warm-up count, retained sample count, raw observations and quantiles specified? [Spec FR-016]
- [x] CHK011 Must default and full-integrity timing distributions remain separate? [Spec FR-015]
- [x] CHK012 Must unfavorable target misses remain visible rather than waived? [Spec US4 scenario 3]

## Correctness and Races

- [x] CHK013 Is a same-size, same-mtime source byte edit required to be detected? [Spec Edge Cases, FR-001]
- [x] CHK014 Is source replacement during inspection constrained never to yield a false `CURRENT` result? [Spec FR-007]
- [x] CHK015 Is concurrent head replacement required to avoid mixed-head evidence? [Spec FR-008]
- [x] CHK016 Are native, manifest, projection and block corruption all included in full-mode detection? [Spec FR-005, SC-004]
- [x] CHK017 Is a fast result after later block corruption forbidden from claiming complete integrity? [Spec US2]
- [x] CHK018 Is non-local source behavior fail-closed rather than inferred? [Spec US3 scenario 3]

## Interface and Security Boundaries

- [x] CHK019 Is one closed coverage vocabulary required across service, CLI and MCP? [Spec FR-010]
- [x] CHK020 Is full verification exposed only through deliberate service/CLI selection? [Spec US2, US3]
- [x] CHK021 Is MCP explicitly unable to request the expensive full-integrity mode? [Spec FR-011]
- [x] CHK022 Do requirements prohibit path authority, parsing and side effects through MCP? [Spec FR-011]
- [x] CHK023 Are status errors and evidence required to exclude bodies, paths, credentials and raw exceptions? [Spec FR-012]
- [x] CHK024 Are source and stored evidence required to remain byte-identical under both modes? [Spec FR-013, SC-008]

## Evidence and Compatibility

- [x] CHK025 Are F020 baselines retained as historical inputs rather than overwritten? [Spec FR-015, FR-019]
- [x] CHK026 Are correctness counters required alongside wall-clock timing? [Spec FR-017]
- [x] CHK027 Are observation, policy, limitation and untested-condition sections required to remain distinct? [Spec FR-018]
- [x] CHK028 Is the additive output change distinguished from unchanged persistence, identity and provider contracts? [Spec Compatibility Impact]
- [x] CHK029 Are network, cloud, dependency and parser exclusions explicit? [Spec FR-002, FR-014]
- [x] CHK030 Are repository, coverage, drift and cross-platform gates measurable completion conditions? [Spec FR-020, SC-009]

## Notes

- All requirement-quality items passed without clarification. Implementation evidence belongs in tests, benchmark
  artifacts and convergence notes rather than in this checklist.
