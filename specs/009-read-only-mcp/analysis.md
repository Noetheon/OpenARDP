# Spec Kit Analysis: Read-only MCP

**Date**: 2026-07-31

**Artifacts reviewed**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/mcp-read-only-tools.md`, `contracts/mcp-error-envelope.md`,
`checklists/requirements.md`, `checklists/mcp-boundary.md`, `tasks.md`, constitution
2.0.0, `AGENTS.md`, `spec-kit/FEATURE_MAP.md`, `docs/05_CONTEXT_COMPILER_AND_MCP.md`,
ADR 0004.

**Scope counts**: 27 functional requirements, 12 success criteria, 4 independently
testable user stories, 75 tasks after final convergence task T075.

## Pass 1 — findings and origin-level resolution

| ID | Severity | Finding | Resolution at origin |
|---|---|---|---|
| F009-A1 | HIGH | FR-015 claimed deadline enforcement "at framing level". While the session loop is blocked reading stdin, no deadline can fire; the claim was unimplementable as written and contradicted Research Decision 8's cooperative model. | FR-015 and Research Decision 8 corrected at the originating artifacts: the deadline is checked before dispatch and threaded into the compiler's bounded checkpoints; the non-interruption of a blocked stdin read is stated explicitly. |
| F009-A2 | HIGH | Single-body cap semantics were unspecified: data-model and contract named a 256 KiB body cap without saying whether an oversized verified body is truncated or fails. Silent truncation would falsify evidence and violate constitution Articles I and VI. | `data-model.md` (Tool I/O notes) and `contracts/mcp-read-only-tools.md` (Bounds) now specify fail-closed behavior: bodies are never truncated; truncation applies only to body-free lists, explicitly and deterministically. |
| F009-A3 | MEDIUM | Line-cap wording drift: FR-002 said "default 64 KiB" while data-model and research said "fixed". Inconsistent configurability claims invite divergent implementations. | FR-002 unified to "bounded at 64 KiB (fixed)". |
| F009-A4 | LOW | `docs/05` planning sketch lists `get_visual_evidence` and an HTTP transport option that this feature deliberately does not deliver. | Resolved at the highest-level originating artifact per constitution precedence: the active spec's Clarifications and Non-Goals govern; `research.md` records the conflict explicitly; task T064 aligns `docs/05` at convergence. No code-level patch. |

No CRITICAL finding. The two HIGH findings were corrected in `spec.md`,
`research.md`, `data-model.md` and `contracts/mcp-read-only-tools.md` before task
execution; tasks already reflected the corrected semantics, so no task rewrite was
required.

## Pass 2 — consistency, constitution and coverage

### Cross-artifact consistency

- Tool set is identical (nine names, same order) across spec FR-006, data-model,
  tool contract and tasks T027–T042. PASS
- Error taxonomy categories, JSON-RPC mappings and fixed-message rule are identical
  across FR-017, data-model and error contract. PASS
- Limits table agrees across research, data-model, tool contract and spec
  FR-002/FR-011/FR-012/FR-015. PASS
- Read-only write list (compile's additive derived publication only) agrees across
  spec Clarifications/FR-013, Research Decision 5 and the tool contract. PASS
- Volatile-field exceptions agree across FR-022 and data-model. PASS
- Frozen-artifact list (11 schemas, 3 vector files, F006 corpus) agrees across spec
  FR-025/SC-009, implementation-notes hashes and tasks T004/T066. PASS

### Constitution check

Plan §Constitution Check passes all twelve articles with no exception and no ADR
requirement. Article V.6 (read-only MCP without arbitrary filesystem reach) and ADR
0004 are directly implemented; Article XI dependency and lockfile stability is
asserted by FR-021 and task T003.

### Coverage check

- Every FR maps to at least one task: FR-001–FR-005 → T007–T019/T056–T058;
  FR-006–FR-010 → T020–T031/T039–T042/T045–T046; FR-011–FR-012 → T022/T035/T041/T050/T052;
  FR-013–FR-014 → T034/T036/T040/T042; FR-015–FR-016 → T017/T038/T043/T048;
  FR-017–FR-019 → T010/T015/T031/T045/T049/T051/T054; FR-020–FR-021 → T003/T020/T053/T057;
  FR-022 → T025/T044/T069; FR-023–FR-024 → T056–T062; FR-025 → T004/T066;
  FR-026 → all test-first tasks plus T068; FR-027 → T063–T065. PASS
- Every SC maps to validation: SC-001/SC-011 → T058/T069; SC-002 → T025/T069;
  SC-003 → T007/T050/T069; SC-004 → T022–T023/T033/T049; SC-005 → T024/T055;
  SC-006 → T045/T055; SC-007 → T038/T048/T055; SC-008 → T049/T055;
  SC-009 → T004/T066; SC-010 → T068; SC-012 → T057/T062. PASS
- Every user story has an independent test and a phase checkpoint. PASS

## Result

Pass 2 reported **zero unresolved critical or high findings** and complete
requirement coverage before implementation.

## Final pass — implemented runtime and convergence

| ID | Severity | Finding | Resolution at origin |
|---|---|---|---|
| F009-A5 | HIGH | The first synchronous `serve` loop correctly threaded a cancellation flag into F008, but could not read a real `notifications/cancelled` frame while compilation occupied the same loop. This contradicted FR-016's mid-compilation acceptance case. | FR-016, Research Decision 8, the plan and data model now require a bounded reader that observes cancellation concurrently while application dispatch stays sequential. T075 added a thread-safe active-request registry and staged real-stream test. |
| F009-A6 | HIGH | Adding a reader thread without bounding pending normal frames would permit attacker-controlled memory growth during a long compile. | FR-002, the data model, research limits and tool contract now fix a 64-frame pending cap. Overflow cancels active work and closes with a sanitized protocol error; a saturation test proves bounded unwind. |
| F009-A7 | MEDIUM | Pre-cancelling unknown IDs could leave a flag that poisoned a later request reusing that ID, conflicting with the documented unknown-request no-op. | The registry now tracks active/queued IDs under a lock; unknown and completed IDs are ignored and completion removes all state. Unit and session tests pin the behavior. |

The final pass rechecked all 27 FRs and 12 success criteria against the 75 tasks,
implementation, 144 focused MCP tests, 843-test repository gate, contracts and
operations guidance. It reports **zero unresolved critical or high findings**, no
unrequested capability, no dependency/schema/migration drift and complete coverage.
