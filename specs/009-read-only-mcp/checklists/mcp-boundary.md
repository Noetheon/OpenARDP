# MCP Boundary Requirements Checklist: Read-only MCP

**Purpose**: Formal PR-review gate for completeness, clarity, consistency and
measurability of F009 transport, least-privilege, error, privacy and failure
requirements
**Created**: 2026-07-27
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are transport, framing, pinned revision, lifecycle methods and capability set all specified? [Completeness, Spec §FR-001–FR-004]
- [x] CHK002 Is the exact tool set enumerated with a prohibition on write/ingest/delete/visual tools? [Completeness, Spec §FR-006]
- [x] CHK003 Are per-tool input bounds, pagination caps, body caps and the response cap defined? [Completeness, Spec §FR-011–FR-012; Data Model §Bounds]
- [x] CHK004 Are deadline and cancellation semantics defined for every long-running tool? [Completeness, Spec §FR-015–FR-016]
- [x] CHK005 Are CLI launch, startup fail-closed and pre-existing CLI preservation specified? [Completeness, Spec §FR-023–FR-024]
- [x] CHK006 Are audit-log content and determinism exceptions both named exactly? [Completeness, Spec §FR-019, §FR-022; Data Model §Volatile fields]

## Requirement Clarity

- [x] CHK007 Is "read-only" reduced to an explicit allowed/forbidden write list rather than left subjective? [Clarity, Spec §Clarifications; Research §Decision 5]
- [x] CHK008 Is "least privilege" reduced to identifiers-only parameters plus service-port-only access? [Clarity, Spec §FR-007–FR-008]
- [x] CHK009 Is the untrusted-data labelling mechanism named structurally rather than described vaguely? [Clarity, Spec §FR-009; Contract §Untrusted-content guarantee]
- [x] CHK010 Are all error categories, JSON-RPC mappings and fixed-message rules enumerated? [Clarity, Spec §FR-017; Contract §Taxonomy]
- [x] CHK011 Is the enumeration-resistance outcome defined as one uniform envelope? [Clarity, Spec §FR-018; Contract §Enumeration resistance]
- [x] CHK012 Is "MCP is transport only" reduced to interface-layer-only code with zero business logic? [Clarity, Spec §FR-007; Plan §Structure Decision]

## Requirement Consistency

- [x] CHK013 Do compile-persistence permission and the read-only boundary agree across spec, research and contracts? [Consistency, Spec §FR-013; Research §Decision 5; Contract §Read-only guarantee]
- [x] CHK014 Do handle-first defaults and the bounded `include_bundle` opt-in avoid contradicting the response cap? [Consistency, Spec §FR-012; Data Model §Tool I/O]
- [x] CHK015 Do the pinned revision, stdio framing and local single-user boundary align with all non-goals? [Consistency, Spec §FR-001–FR-003, §Non-Goals]
- [x] CHK016 Do identifier-only parameters remain consistent with the CLI's path-capable status verb? [Consistency, Spec §FR-008; Research §Decision 4]
- [x] CHK017 Do determinism requirements and the named volatile fields avoid contradiction? [Consistency, Spec §FR-022; Data Model §Volatile fields]

## Acceptance Criteria Quality

- [x] CHK018 Can byte-stability be measured across an explicit repeat count with named exceptions? [Measurability, Spec §SC-002]
- [x] CHK019 Can envelope coverage be tested as zero bare-body occurrences? [Measurability, Spec §SC-004]
- [x] CHK020 Can confused-deputy resistance be measured as zero filesystem access across the probe matrix? [Measurability, Spec §SC-005]
- [x] CHK021 Can taxonomy conformance be measured as zero undocumented codes under fault injection? [Measurability, Spec §SC-006]
- [x] CHK022 Can cancellation/deadline safety be measured as zero partial compilations? [Measurability, Spec §SC-007]
- [x] CHK023 Are compatibility and cross-platform outcomes objectively bounded? [Measurability, Spec §SC-009–SC-012]

## Scenario and Edge-Case Coverage

- [x] CHK024 Are handshake, navigation and envelope flows covered independently? [Coverage, US1]
- [x] CHK025 Are search, compile, bundle opt-in and verified receipt flows covered? [Coverage, US2]
- [x] CHK026 Are malformed framing, oversize, batch, unknown method/tool, path-bearing and enumerated identifiers covered? [Coverage, US3; Edge Cases]
- [x] CHK027 Are injection-shaped queries and tasks covered with structural data-only outcomes? [Coverage, US3/AC3]
- [x] CHK028 Are cancellation at every compile phase and deadline expiry at checkpoints covered? [Coverage, US3/AC4; Edge Cases]
- [x] CHK029 Are startup failure, EOF, second initialize, pre-init calls and concurrent-CLI cases covered? [Coverage, US4; Edge Cases]

## Security, Privacy and Operational Requirements

- [x] CHK030 Is document content consistently classified as data with no path, URL, command or tool authority? [Security, Spec §FR-009, §FR-013]
- [x] CHK031 Are network listener, remote transport and multi-user access excluded unambiguously? [Security, Spec §FR-001, §FR-020]
- [x] CHK032 Are log and error denylists explicit for query text, task text, bodies, paths and tracebacks? [Privacy, Spec §FR-017, §FR-019]
- [x] CHK033 Are resource dimensions and accepted ranges documented for lines, responses, deadlines and every tool? [Operational, Spec §FR-011–FR-012, §FR-015; Research §Limits]
- [x] CHK034 Are no-startup-migration, no-repair and locked-workspace fail-closed behaviors specified? [Recovery, Spec §FR-020, §FR-024]

## Dependencies, Assumptions and Traceability

- [x] CHK035 Are F008 service reuse, F011 visual exclusion, F012 watcher exclusion and F013 retention boundaries explicit? [Dependency, Spec §Non-Goals, §Assumptions]
- [x] CHK036 Are application, MCP-interface, protocol, error-taxonomy and workspace version impacts separated? [Compatibility, Spec §Compatibility; Data Model §Version dimensions]
- [x] CHK037 Is the docs/05 planning-sketch conflict resolved at the originating artifact rather than silently? [Traceability, Research §Conflict resolution]
- [x] CHK038 Does every contract addition carry fixtures, compatibility and review evidence without touching frozen schemas? [Traceability, Spec §FR-025; Contract §Compatibility]
- [x] CHK039 Are all four user stories independently testable and mapped to measurable outcomes? [Traceability, Spec §User Scenarios; §Success Criteria]
- [x] CHK040 Are SDK adoption, HTTP transport, replay tool and visual tool explicitly deferred with owners? [Boundary, Spec §Non-Goals, §Assumptions]

## Notes

- All 40 requirement-quality checks pass before task generation.
- The checklist evaluates requirements writing, not implementation behavior.
