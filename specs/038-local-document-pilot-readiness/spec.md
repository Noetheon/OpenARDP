# Feature Specification: Local document pilot readiness

**Feature Branch**: `codex/f038-local-document-pilot-readiness`
**Created**: 2026-09-19
**Status**: Specified
**Governance Tier**: high-assurance (prospective evaluation methodology and investment decision)
**Input**: Implement the accepted project audit recommendations within a narrow useful document workflow.
**Predecessor**: F037 merged as PR #48, commit `4504cbd469db7b7c30f06f0655a2e39da8e02322`; all required CI checks passed.

## User scenarios

### US1 — Read and verify selected evidence (P1)

A local user imports a few documents, asks for context, reads the selected passages and checks their exact source/version.

Acceptance:
1. `context --include-bundle` prints the selected content or artifact handle and exact available provenance in human output; default body-free output and JSON remain unchanged except the narrowly defined human terminal-control hardening below.
2. Block locators and rich projection/reference IDs remain distinct. No filename/page/anchor is invented. Untrusted contents and labels are identified as evidence, not instructions or generated answers. The shared human escaper additionally escapes DEL, C1 controls and explicit Unicode bidi controls (U+061C, U+200E–U+200F, U+202A–U+202E, U+2066–U+2069), preserving ordinary Unicode and German umlauts.
3. Empty selections explain that no evidence was selected. Structured content and handle-only items remain inspectable.
4. A short working guide takes a new user from a locked core install through ingest, repeat reuse, list, context, original/source checking and receipt replay; a synthetic local smoke run verifies the commands without claiming actual user value.

### US2 — Decide whether further work is justified (P1)

The user wants a bounded decision based on real recurring tasks rather than more platform features.

Acceptance:
1. A prospective manual protocol and empty private-run templates register 30 distinct real tasks as ten matched triplets before any trial. Each triplet assigns one task to current work, a simple persistent native-parser cache with search, and OpenARDP. Task and execution assignment are frozen and order-balanced.
2. Setup/import attention, active task work, source checking, repairs/rescue and maintenance count; machine waiting is separately visible. Failed attempts remain present. No automatic substring/keyword match certifies semantic support.
3. Human judgments start pending and require a concrete supporting passage, correct source/version, correctness and sufficient completeness (or justified scoped abstention). Record reviewer independence and blind review; self-review alone cannot establish the stronger confirmed pilot verdict.
4. Limited continued development requires all preregistered gates: all 30 tasks completed and reviewed, at least 30% less total active operational time than BOTH baselines, at least 9/10 assigned-arm successes and no worse quality, zero false source/version final claims, faster than the simple cache in at least 7/10 groups, and voluntary reuse for two further real tasks on separate days.
5. Cap additional work at 20 hours and ten working days. Missing real tasks, reviews, effort accounting or repeat-use evidence cannot yield GO; at the cap, pause expansion. Personal usefulness and external adoption remain separate; broader open-source investment requires at least two independent repeat users in addition to the personal evidence.
6. Current canonical strategy/README prioritizes this one workflow and pauses expansion. Existing benchmark artifacts/evaluators remain immutable; new documentation discloses legacy substring/support and fixed source-fitness limits. The release NO-GO is unchanged.

## Requirements

- **FR-001**: Render the already requested bundle with content/handles and exact available provenance only under `--include-bundle`; preserve default body omission, JSON, selection and receipt semantics. Existing human outputs using the shared escaper also receive the explicitly bounded control hardening.
- **FR-002**: Preserve untrusted-content boundaries and escape C0, DEL, C1 and the enumerated bidi controls across text, structured bodies and provenance. Ordinary Unicode remains readable. No source-driven actions or fabricated source details.
- **FR-003**: Provide and smoke-test the short local workflow, including exact replay parameters and optional existing MCP/PDF/semantic setup references with honest limits.
- **FR-004**: Freeze a prospective three-arm matched-task protocol, setup/repair-inclusive timing and human semantic support adjudication; keep historical results/evaluators intact.
- **FR-005**: Provide empty task, attempt, overhead and review records plus a pending decision template; store actual private tasks/results outside Git, distinguish smoke data from user evidence and preserve all failures.
- **FR-006**: Define unambiguous limited-GO/pause gates, 20-hour/ten-workday stop rule, reviewer/learning limitations and separate personal/adoption criteria before trial.
- **FR-007**: Align canonical focus/claims with the bounded validation phase; no new provider, model, cloud, GUI, connector, HTTP service, export, runtime benchmark framework or release authorization.
- **FR-008**: Add focused renderer regression tests first; pass existing locked quality/governance/build and three-platform CI, independent analysis/convergence, and verify final delivery.

## Success criteria

- **SC-001**: Explicit human bundle output displays source-verifiable text/structured/handle evidence; default and JSON behavior are characterized unchanged; the enumerated terminal/bidi controls are escaped while ordinary Unicode remains readable.
- **SC-002**: A fresh synthetic workspace completes the documented ingest/context/source/replay loop with originals unchanged and explicit selected evidence. This proves workflow execution only.
- **SC-003**: An independent reviewer can determine every prospective gate from the protocol and templates; all initial records and verdict remain pending and no real trial is claimed.
- **SC-004**: Existing benchmark/schema/dependency bytes remain unchanged and all required code and governance gates pass.

## Edge cases and compatibility

Zero evidence, structured JSON bodies, handle-only evidence, malicious control characters, multiline content and rich sources without inline page locators; incomplete/failed trials, absent independent reviewer, setup-dominated timings, zero baseline time, changed versions, unsupported questions, learning/order effects and missing recurrence evidence.

No CLI flag/JSON schema, identity, persisted model, provider recipe or selection-policy change. Shared human rendering changes only by escaping the enumerated control characters in addition to C0. The protocol governs a new prospective manual pilot only. ADR 0019 remains unchanged; no architectural exception is needed. F038 completes at pilot readiness, not at a positive user-value verdict. Actual task execution remains dependent on the user's folder and real tasks.

## Clarification record

Scope and implementation choices follow the accepted audit and user authorization. One coherent work package makes the existing workflow usable and ready for honest measurement; its mixed scope uses the higher assurance tier. No blocking implementation ambiguity remains. The already pending user question about folder and recurring tasks is required before registering a real trial, not before this readiness change.
