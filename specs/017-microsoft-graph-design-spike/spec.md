# Feature Specification: Microsoft Graph Design Spike

**Feature Branch**: `codex/f017-microsoft-graph-design-spike`

**Created**: 2026-08-01

**Status**: Draft

**Input**: Authoritative Feature 017 prompt
`spec-kit/feature-prompts/017-microsoft-graph-design-spike.md`, plus the request to
complete the roadmap sequentially with a durable, best-practice implementation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reconcile Tenant-Scoped Drive Changes (Priority: P1)

As an enterprise-connector architect, I can execute a bounded mocked Drive delta cycle so
that item updates, deletions and permission references converge atomically without exposing
provider cursors or crossing tenant, site or drive boundaries.

**Why this priority**: Delta reconciliation is the authoritative recovery path; notifications
are only hints and cannot make a connector correct by themselves.

**Independent Test**: Feed deterministic multi-page mocked deltas containing duplicate item
occurrences, moves, tombstones and a final delta token, then verify last-occurrence-wins state
and cursor publication happen in one atomic commit.

**Acceptance Scenarios**:

1. **Given** a scoped starting cursor and multiple pages, **When** reconciliation completes,
   **Then** exactly one final opaque cursor handle and the reduced item/tombstone state commit.
2. **Given** the same item multiple times, **When** pages are reduced, **Then** the last
   occurrence wins while the stable item identity is independent of path or name.
3. **Given** a 410 reset, malformed page, cycle, scope mismatch or injected commit failure,
   **When** reconciliation runs, **Then** no partial changes or replacement cursor become visible.

---

### User Story 2 - Enforce Least-Privilege Operational Boundaries (Priority: P1)

As a security reviewer, I can inspect and test notification, permission, retry and secret
boundaries so that the design never treats webhook delivery as authority and never leaks raw
tokens, client state, paths, bodies or cross-tenant identifiers into core state or logs.

**Why this priority**: A technically functional connector is unacceptable if broad Graph
permissions, webhook spoofing or shared caches can disclose another tenant's data.

**Independent Test**: Exercise valid and invalid notification digests, tenant-confused cursor
handles, missing permission snapshots, 429 Retry-After behavior and bounded fallback backoff
without credentials, network access or wall-clock sleeping.

**Acceptance Scenarios**:

1. **Given** a matching unexpired subscription binding, **When** a notification is validated,
   **Then** it schedules reconciliation only; it never mutates document state directly.
2. **Given** invalid authenticity, scope or expiry evidence, **When** notification validation
   runs, **Then** it fails closed using a body-free category and schedules nothing.
3. **Given** throttling, **When** Retry-After is within policy, **Then** it is honored exactly;
   otherwise deterministic bounded backoff or a retry-later result is used without partial commit.

---

### User Story 3 - Issue a Conservative Enterprise Decision (Priority: P1)

As a project maintainer, I receive a threat model, data-protection assessment, permission
matrix and explicit decision so that mock-contract feasibility is separated from production
readiness and unresolved governance blockers remain visible.

**Why this priority**: The spike must prevent a successful mock from being misreported as
authorization to deploy a real tenant-wide connector.

**Independent Test**: Review every decision criterion against exact tests and official
Microsoft documentation, then verify that production remains NO-GO while the bounded mock
architecture can be GO.

**Acceptance Scenarios**:

1. **Given** passing deterministic mock evidence, **When** the decision is evaluated, **Then**
   only mock-contract feasibility is GO and no production claim is made.
2. **Given** unresolved tenancy, authorization, webhook, consent, data-protection or release
   blockers, **When** production readiness is assessed, **Then** the decision is NO-GO without
   waiver or optimistic inference.
3. **Given** official platform facts that conflict with an assumed least-privilege design,
   **When** research is documented, **Then** the conflict is recorded as a blocker rather than
   silently widening permissions.

### Edge Cases

- A provider item ID is reused in a different tenant, site or drive.
- An item is renamed or moved while its provider ID remains stable.
- A page omits `cTag`, contains only an `eTag`, or exposes multiple revisions of one item.
- A deleted item lacks path, parent or revision metadata.
- The same item appears repeatedly across pages, including update-after-delete or delete-after-update.
- A final cursor repeats an already visited cursor or belongs to another scope.
- Graph returns 429 with a valid Retry-After, no Retry-After, or a delay beyond local policy.
- Graph returns 410 Gone after earlier pages have been accumulated.
- A notification is duplicated, delayed, forged, expired or reports a lifecycle event.
- Permission data is incomplete for the caller even though item metadata is available.
- Selected permissions cannot support complete inherited-permission reconstruction.
- Raw provider URLs, delta tokens, subscription secrets, names or content reach a core model.
- A global digest/cache reveals equality or timing across tenants.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST remain mock-only and MUST perform zero OAuth, HTTP, Graph SDK,
  credential, certificate, webhook-listener or production-tenant operations.
- **FR-002**: The design MUST define a composite tenant/site/drive scope and bind every item,
  cursor, permission snapshot, subscription and persisted state record to that exact scope.
- **FR-003**: Provider item IDs MUST be case-sensitive stable identity inputs; names and paths
  MUST NOT participate in persisted item identity.
- **FR-004**: Raw provider IDs, delta links, next links and client-state secrets MUST remain
  inside the adapter/secret boundary; core contracts receive only scope-bound SHA-256 handles.
- **FR-005**: `eTag`, `cTag` and version values MUST be represented as optional remote revision
  hints, never as original-content identity or proof that bytes were fetched.
- **FR-006**: Every upsert MUST carry a complete permission-snapshot reference for the exact
  item/scope; incomplete or mismatched snapshots MUST fail closed.
- **FR-007**: Deletes MUST become explicit tenant-scoped tombstones and MUST NOT require absent
  path, revision or permission data.
- **FR-008**: The delta contract MUST represent exactly one continuation or final cursor per page.
- **FR-009**: Reconciliation MUST traverse bounded pages and changes, reject cursor cycles and
  reduce repeated items by last occurrence across the entire ordered delta response.
- **FR-010**: State changes and the final delta cursor MUST commit atomically after all pages
  validate; any prior error MUST leave state and cursor unchanged.
- **FR-011**: A 410/reset condition MUST produce an explicit reset-required result with no
  partial commit; production rescan authorization remains outside this spike.
- **FR-012**: 429 handling MUST honor valid Retry-After values, otherwise use deterministic
  capped exponential backoff, enforce retry/page/change limits and return retry-later when policy
  cannot wait safely.
- **FR-013**: Notifications MUST be treated only as reconciliation wakeups, never as an
  authoritative or complete change log.
- **FR-014**: Notification validation MUST use constant-time digest comparison for subscription
  and client-state bindings, enforce expiry and produce only body-free decisions.
- **FR-015**: Notification validation MUST perform zero catalog mutation, content fetch or
  delta advancement.
- **FR-016**: Mock adapters MUST keep provider cursors private, prevent scope-confused handle
  use, provide deterministic scenarios and perform zero network access.
- **FR-017**: The in-memory state adapter MUST model an atomic persistence port, optimistic
  expected-cursor checks, explicit tombstones and injected pre-publication failure.
- **FR-018**: No contract or diagnostic MUST contain document bodies, item names, paths, URLs,
  raw provider identifiers, raw cursors, access tokens or client-state secrets.
- **FR-019**: No global cross-tenant content deduplication, shared cache key or observable
  equality shortcut MAY be introduced by this feature.
- **FR-020**: The feature MUST define permission options and identify the minimum candidate for
  a future pilot without silently widening to tenant-wide application permission.
- **FR-021**: The permission matrix MUST distinguish Entra consent, resource assignment and
  runtime token requirements, and MUST record Graph's limitations for effective permissions.
- **FR-022**: The threat model MUST cover spoofing, token/cursor disclosure, permission drift,
  replay, deletion loss, throttling denial, SSRF/egress, tenant confusion and side channels.
- **FR-023**: The data-protection assessment MUST inventory metadata/content categories,
  purposes, minimization, retention, residency, subprocessors, data-subject handling,
  incident response and unresolved controller decisions.
- **FR-024**: The decision MUST independently classify mock feasibility and production readiness;
  mock GO MUST NOT override a production NO-GO.
- **FR-025**: Production MUST remain NO-GO until tenant-aware authorization/storage, secret and
  certificate management, live selected-scope validation, DPA/DPIA/residency decisions, public
  webhook operations, quota tests, revocation/erasure procedures and security review exist.
- **FR-026**: Official Microsoft primary documentation MUST support platform-sensitive claims,
  with access dates and explicit inference labels where conclusions combine multiple facts.
- **FR-027**: Public schemas, application version, workspace revision, export profiles and
  local-first defaults MUST remain unchanged.
- **FR-028**: Unit and integration tests MUST use synthetic inputs and run with network disabled.
- **FR-029**: The complete Spec Kit lifecycle, repository gates, build and Linux/macOS/Windows
  pull-request and post-merge workflows MUST pass before feature completion.

### Non-Goals and Compatibility Impact

- **Non-goal**: A production Microsoft Graph connector, OAuth flow, webhook endpoint, queue,
  Azure deployment, credential store, persistent enterprise catalog or live tenant test.
- **Non-goal**: Content download/parsing, global deduplication, search authorization or a claim
  that Graph permission listings are complete for every caller.
- **Compatibility impact**: Additive experimental Python contracts, mocked adapters, tests and
  design evidence only. No public interchange schema, CLI/MCP contract, workspace/application
  version, provider profile or export profile changes.

### Key Entities

- **Graph Scope**: Tenant/site/drive composite authority represented with tenant identity and
  tenant-bound digests for provider site and drive IDs.
- **Graph Item Key**: Scope plus a case-sensitive provider-item digest; never a path.
- **Remote Revision Hints**: Optional digests of `eTag`, `cTag` and version values.
- **Permission Snapshot Reference**: Complete, exact item/scope authorization evidence stored
  elsewhere; the connector contract carries no principal names or ACL body.
- **Delta Page/Change**: Ordered mocked provider response with upsert/tombstone changes and one
  next/final opaque cursor handle.
- **Subscription Binding/Notification Decision**: Secret-free core records for validating a
  wakeup without changing authoritative state.
- **Sync State/Result**: Atomically committed cursor and reduced scoped item/tombstone set plus a
  sanitized orchestration outcome.
- **Architecture Decision**: Separate mock feasibility and production readiness conclusions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Deterministic tests cover multi-page update, duplicate, move and delete scenarios;
  100% of expected final state and cursor assertions pass.
- **SC-002**: Each injected reset, cycle, scope mismatch, malformed permission reference or
  commit failure publishes zero partial state changes.
- **SC-003**: Cross-tenant/site/drive cursor and item substitutions fail in 100% of negative tests.
- **SC-004**: Every tested 429 with an allowed Retry-After sleeps exactly that duration; missing
  values use the documented capped sequence; over-policy values produce no sleep or commit.
- **SC-005**: Every invalid, expired or mismatched notification schedules zero reconciliations;
  every valid notification schedules exactly one reconciliation hint and zero state mutations.
- **SC-006**: Static and runtime test inspections find zero raw token, secret, URL, path, body or
  item-name fields in exported domain and result models.
- **SC-007**: Permission matrix, threat model and data-protection assessment cover every
  FR-020–FR-026 topic with no unresolved requirement ambiguity.
- **SC-008**: The decision reports mock architecture GO and production connector NO-GO, with
  every blocker mapped to a required follow-up and no waiver field.
- **SC-009**: Focused tests run offline from a clean checkout through one documented command.
- **SC-010**: All repository quality gates, build, pre-commit and three-platform workflows pass
  without weakening existing thresholds.

## Assumptions

- A single-process deterministic mock is sufficient to validate contracts and orchestration,
  but not platform compatibility, operational scalability or production security.
- Microsoft Graph Drive delta is the eventual-consistency reconciliation primitive; change
  notifications are latency hints and periodic reconciliation remains necessary.
- A future pilot should prefer delegated access where operationally possible, otherwise selected
  application permissions scoped to explicit resources; feasibility must be proven live later.
- Current OpenARDP v0.1 local storage and authorization are intentionally unsuitable for
  multi-tenant production and are not modified in this spike.
