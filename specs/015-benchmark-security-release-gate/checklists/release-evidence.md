# Benchmark, Security and Release Requirements Checklist: v0.1 Release Gate

**Purpose**: Formal PR-review gate for completeness, clarity, consistency and
measurability of F015 benchmark fairness, hostile-input safety, supply-chain,
reproduction and binding release-decision requirements.
**Created**: 2026-08-01
**Feature**: [spec.md](../spec.md)

**Note**: These items test the requirements as written, not implementation behavior.

## Requirement completeness

- [x] CHK001 Are all five required baselines defined as separate treatments over identical source, query/task and judgment inputs? [Completeness, Spec §FR-001–FR-003]
- [x] CHK002 Are cold, warm, source-update, parser-invocation, storage, retrieval, context and replay evidence all required? [Completeness, Spec §FR-004]
- [x] CHK003 Are raw observations, rejected samples, aggregates, uncertainty, limitations and unavailable baselines all retained? [Completeness, Spec §FR-005–FR-007]
- [x] CHK004 Are relevance, rank, anchor, evidence-coverage, stale rejection and replay judgments all specified? [Completeness, Spec §FR-009–FR-012]
- [x] CHK005 Are prompt injection, malformed parser, stale/reconciliation, privacy, failure/recovery and authority-expansion controls all represented? [Completeness, Spec §FR-013–FR-018]
- [x] CHK006 Are dependency graph, per-component SBOM licenses, vulnerabilities, separate review dispositions, artifact checksums and artifact-content inspection all required? [Completeness, Spec §FR-019–FR-022]
- [x] CHK007 Are fresh install, prior upgrade, backup/restore, rollback and all supported platforms covered? [Completeness, Spec §FR-023–FR-026]
- [x] CHK008 Are machine decision, human report, support matrix, claim map, documentation and rollback instructions all specified? [Completeness, Spec §FR-027–FR-035]

## Requirement clarity

- [x] CHK009 Is each baseline's precise reuse/parsing/retrieval boundary defined without overclaiming provider-native search behavior? [Clarity, Research §Decision 2]
- [x] CHK010 Are timing clock, units, warm-up, minimum sample count, invalid-sample policy, statistic, interval and rounding rules exact? [Clarity, Spec §FR-001, FR-006, FR-011; Research §Decision 4]
- [x] CHK011 Is “distinct operational value” decomposed into parser avoidance, interval separation, correctness, bounded evidence and native-retrieval parity? [Clarity, Plan §After design; Research §Decision 5]
- [x] CHK012 Is a reference timing environment distinguished from shared CI and cross-host timing comparison? [Clarity, Plan §Technical Context; Research §Decision 11]
- [x] CHK013 Is model-based answer quality explicitly optional/unavailable rather than conflated with mechanical correctness? [Clarity, Spec §FR-010; Research §Decision 6]
- [x] CHK014 Is an integrity-valid SBOM distinguished from license compatibility, vulnerability absence and legal review? [Clarity, Spec §FR-019–FR-022; Research §Decisions 9–10]
- [x] CHK015 Is a valid `NO-GO` distinguished from malformed evidence and command execution failure? [Clarity, Spec §FR-027–FR-030; Contracts §maintainer-commands]
- [x] CHK016 Is external publication explicitly excluded from a local `GO` decision? [Clarity, Spec §Non-Goals and Assumptions]

## Requirement consistency

- [x] CHK017 Do benchmark reproducibility requirements agree with the rule that wall-clock observations vary and remain environment-scoped? [Consistency, Spec §FR-005–FR-007, FR-032]
- [x] CHK018 Do complete-baseline requirements agree that any unavailable required treatment yields `NO-GO` rather than exclusion? [Consistency, Spec §FR-002–FR-003, FR-028]
- [x] CHK019 Do optional evaluator rules agree with the mandatory correctness suite and avoid making a missing cloud/model service a hidden pass? [Consistency, Spec §FR-009–FR-010]
- [x] CHK020 Do three-platform requirements separate semantic agreement from unsupported cross-platform latency ranking? [Consistency, Spec §FR-026; Research §Decision 11]
- [x] CHK021 Do supply-chain requirements preserve offline-by-default runtime behavior while allowing time-scoped explicit maintainer evidence? [Consistency, Spec §FR-019–FR-020, FR-033]
- [x] CHK022 Do candidate-version rules distinguish prior `0.0.1`, candidate `0.1.0rc1` and prohibited final `0.1.0`, while leaving public release status unchanged on `NO-GO`? [Consistency, Spec §Compatibility Impact]
- [x] CHK023 Do report/README requirements consistently make `decision.json` authoritative and prohibit claims beyond allowed evidence? [Consistency, Spec §FR-029–FR-032; Research §Decision 14]

## Acceptance criteria quality

- [x] CHK024 Can complete five-baseline coverage and every unavailable reason be counted objectively? [Measurability, Spec §SC-001]
- [x] CHK025 Can every reported aggregate and 95% interval be recomputed exactly from raw observations? [Measurability, Spec §SC-002]
- [x] CHK026 Are corpus families, context budgets and required metric families numerically bounded? [Measurability, Spec §SC-003]
- [x] CHK027 Are correctness, security, privacy, install, recovery, dependency and drift outcomes expressed as exact pass/block conditions? [Measurability, Spec §SC-004–SC-010]
- [x] CHK028 Can report/decision/claim-map agreement be checked over 100% of statuses, metrics, limitations and claims? [Measurability, Spec §SC-011]
- [x] CHK029 Is the `GO` condition conjunctive and the missing/stale/failing/threshold-crossing behavior objectively `NO-GO`? [Measurability, Spec §SC-012]

## Scenario and edge-case coverage

- [x] CHK030 Are successful, unfavorable, unavailable, insufficient-sample and threshold-crossing benchmark outcomes all specified? [Coverage, User Stories 1–2; Edge Cases]
- [x] CHK031 Are parser hang/crash/late output/network attempt/child cleanup and malformed/oversized output scenarios covered? [Coverage, Spec §FR-015; Edge Cases]
- [x] CHK032 Are all sentinel locations and the designated-payload exception specified without allowing canaries in reports/logs/policy? [Coverage, Spec §FR-017; Research §Decision 8]
- [x] CHK033 Are interruption, capacity refusal, concurrent duplicate work, migration failure and recovery/rollback flows defined? [Coverage, Spec §FR-018; Edge Cases]
- [x] CHK034 Are SBOM omissions, platform markers, missing licenses, stale scanner data and unresolved finding dispositions covered? [Coverage, Spec §FR-019–FR-022; Edge Cases]
- [x] CHK035 Are candidate-generated prior fixtures, unsupported prior revisions and partial platform reproduction explicitly rejected? [Coverage, Spec §FR-024–FR-026; Edge Cases]
- [x] CHK036 Are report tampering, source/lock/corpus drift, duplicate sample identity and invalid numeric values covered? [Coverage, Spec §FR-005, FR-011, FR-032; Edge Cases]

## Dependencies and assumptions

- [x] CHK037 Is the no-new-runtime-dependency decision supported by existing standard-library/Pydantic capabilities and pinned `uv` SBOM export? [Dependency, Plan §Technical Context; Research §Decision 9]
- [x] CHK038 Is the CycloneDX preview-status risk addressed through exact tool pinning, normalization, schema validation and drift checks? [Dependency, Research §Decision 9]
- [x] CHK039 Are features 001–014 treated as the candidate under measurement rather than silently redesigned within F015? [Assumption, Spec §Assumptions; Plan §Summary]
- [x] CHK040 Are synthetic-corpus, supported-platform, offline-provider, statistical-generalization and scanner-coverage limitations explicit? [Assumption, Spec §Assumptions; Research §Known limitations]
- [x] CHK041 Is the ownership boundary between F015 release evidence, F016 alternate-parser conformance and F017 Graph design explicit? [Scope, Spec §Non-Goals]
- [x] CHK042 Are future threshold, policy or evidence-version changes required to produce new identities rather than mutate prior decisions? [Lifecycle, Data Model §State transitions]

## Notes

- Review completed during planning at formal release-gate depth for maintainers and PR reviewers.
- No unresolved requirement-quality gap remained. Implementation evidence belongs in tasks,
  tests and convergence notes rather than this checklist.
