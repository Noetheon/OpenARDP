# Feature Specification: Bounded semantic session reuse

**Feature Branch**: `codex/f037-semantic-session-reuse`
**Created**: 2026-09-19
**Status**: Specified
**Governance Tier**: high-assurance
**Input**: Implement the audited semantic session lifecycle corrections before expanding the product.

## User Scenarios & Testing

### User Story 1 - Reuse an unchanged selection in an agent session (Priority: P1)

A local agent asks several questions about the same exact documents. Preparation is reused within that session while
every delivered source remains verified and current for the requested snapshot.

**Independent Test**: Two real MCP tool requests with a deterministic prepared provider require one preparation;
changing the selected source version or estimator requires a fresh valid preparation.

**Acceptance Scenarios**:

1. Given an unchanged snapshot and estimator, two successful semantic requests reuse preparation and return the same
   evidence and receipt identities as fresh compilation of each request.
2. Given an estimator or source-version change, a new request cannot reuse an incompatible prepared handle.
3. Given cancellation, timeout, invalid provider output or another compilation failure, that request fails explicitly;
   the next request may prepare afresh without reopening the MCP session.
4. Given tampered catalog metadata or source objects after warm-up, the next request fails closed.

### User Story 2 - Switch between bounded document selections (Priority: P1)

A user changes the documents under review without restarting the semantic provider. Old disposable state must not make
a separately valid next selection fail or accumulate across the session.

**Independent Test**: Two disjoint selections that individually fill the allowed cache both succeed sequentially;
overlap is reused and old prepared handles are rejected.

**Acceptance Scenarios**:

1. A valid replacement selection retains at most its unique source objects and one active prepared corpus.
2. Multiple evidence identities for identical content produce separate ordered scores but one cached vector.
3. Conflicting text for one object identity, invalid limits or oversize selections fail before cache mutation.
4. Legacy direct scoring also replaces obsolete cache entries; it invalidates any previously prepared handle.

### Edge Cases

- Estimator A to B to A, scope A to B to A, source A to B to A, changed limits, and empty selections.
- Repeated evidence identities sharing an object; contradictory bodies for a shared object in one or later requests.
- Worker death between requests, response/selection failure after preparation, and lexical requests between semantic ones.
- A long sequence of changed evidence identities over the same objects must not grow the prepared-handle inventory.

## Requirements

- **FR-001**: One MCP session MUST retain at most one active semantic compiler, bound to the full estimator identity.
- **FR-002**: Snapshot, policy, recipe, limits and authority checks MUST still control reuse; delivered bodies MUST be
  verified against authoritative storage on every request.
- **FR-003**: Any failed semantic compilation MUST discard its compiler slot; errors MUST remain explicit and sanitized.
- **FR-004**: A new valid scoring/preparation request MUST replace obsolete passage-cache entries within existing bounds,
  retaining common exact objects and creating each missing unique object once.
- **FR-005**: Object/text conflicts and invalid count/byte limits MUST fail before cache mutation.
- **FR-006**: Prepared state MUST contain at most one corpus and its exact preparation limits; evicted handles and
  mismatched limits MUST be rejected. Direct scoring invalidates prepared state.
- **FR-007**: Existing lexical behavior, scores, selection policy, public schemas, persisted identities and historical
  benchmark evidence MUST remain unchanged. Cache-hit diagnostics may reflect actual reuse.
- **FR-008**: Offline regression tests MUST exercise actual MCP dispatch, worker request functions, invalidation and
  failure recovery without downloading models; local and applicable three-platform repository gates MUST pass.

### Non-Goals and Compatibility Impact

No new retrieval model, persisted vectors, ranking policy, larger limits, network access, user-study result or speed claim.
No public contract, application version, workspace revision, provider recipe or export version change. This corrects
disposable execution state under ADR 0019; prepared handles remain valid only while live in their owning process.

### Key Entities

- Session compiler slot: the active estimator identity and semantic compiler, disposable on replacement or failure.
- Active provider selection: exact unique object/body/vector entries and at most one ordered, limit-bound corpus handle.

## Success Criteria

- **SC-001**: Two identical successful MCP requests prepare once; incompatible requests prepare anew.
- **SC-002**: Disjoint valid selections succeed sequentially without exceeding existing cache/handle bounds.
- **SC-003**: Tampering, conflicting identities, stale handles and changed limits are rejected; a failed session request
  does not poison later valid requests.
- **SC-004**: Results and historical identities stay unchanged and all required checks pass.

## Assumptions and Clarification Record

- The stdio server dispatches one tool call at a time; this feature adds no concurrent compiler access.
- The user authorized all audited corrections. No unresolved user choice affects this bounded implementation.
- Lexical composition stays unchanged. Real tasks, onboarding and prospective evaluation belong to later packages.
- Clarify review: scope, data, failure/recovery, resource bounds, compatibility and acceptance are clear; no questions needed.
