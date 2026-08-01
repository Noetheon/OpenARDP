# Retention and Recovery Requirements Checklist

**Purpose**: Reviewer-level quality gate for destructive authority, recovery,
migration and capacity requirements before tasks are generated
**Created**: 2026-08-01
**Feature**: [spec.md](../spec.md)

## Requirement completeness

- [x] CHK001 Are all catalog reference families delivered through F012 explicitly
  included in the conservative live-root boundary? [Completeness, Spec §FR-001]
- [x] CHK002 Are candidate, protected, quarantined, disposable and inconsistent states
  defined as disjoint classifications with reasons and totals? [Completeness, Spec
  §FR-002–FR-004]
- [x] CHK003 Are dry-run, quarantine, restore, irreversible commit and generic recovery
  specified as distinct authorities and lifecycle phases? [Completeness, Spec
  §FR-009–FR-020]
- [x] CHK004 Are both catalog and immutable-object requirements complete for backup,
  fresh restore and A→B→A recovery? [Completeness, Spec §FR-022–FR-028]
- [x] CHK005 Are diagnostics, capacity reserve and complete lexical-index replacement
  all covered without treating low space as deletion authority? [Completeness, Spec
  §FR-031–FR-035]

## Requirement clarity and consistency

- [x] CHK006 Are the minimum candidate age, default grace and hard irreversible floor
  numerically defined, including which values operators may extend? [Clarity, Spec
  §FR-008 and §FR-017]
- [x] CHK007 Is semantic plan identity distinguished clearly from observation/reporting
  time while still changing for every semantic candidate/input change? [Clarity, Spec
  §FR-009–FR-010]
- [x] CHK008 Is the requirement that filesystem presence never authorizes deletion
  consistent with forward recovery of an already acknowledged durable commit intent?
  [Consistency, Spec §FR-016 and §FR-018–FR-020]
- [x] CHK009 Is backup consistently framed as an internal recovery artifact rather than
  the portable interchange scope owned by F014? [Consistency, Spec §Non-Goals]
- [x] CHK010 Is validate-only open consistent across newer, gapped, checksum-drifted,
  malformed and prior supported revisions? [Consistency, Spec §FR-027–FR-030]

## Acceptance-criteria quality

- [x] CHK011 Do the success criteria quantify determinism, concurrency and false-
  reclamation prevention rather than using qualitative safety language alone?
  [Measurability, Spec §SC-001–SC-006]
- [x] CHK012 Does backup/restore acceptance require exact manifest, hash, length,
  catalog-fact and B-exclusion evidence? [Measurability, Spec §SC-007–SC-008]
- [x] CHK013 Are migration fault boundaries and concurrent migration convergence
  objectively measurable? [Measurability, Spec §SC-009]
- [x] CHK014 Are non-mutation and capacity boundaries measurable at nanosecond timestamp
  and exact-byte thresholds? [Measurability, Spec §SC-010–SC-011]
- [x] CHK015 Is complete index equivalence defined through authoritative coverage,
  ordered results and unchanged evidence identities? [Measurability, Spec §SC-012]

## Exception, recovery and edge coverage

- [x] CHK016 Are stale plans, new references, holds, changed bytes and concurrent
  conflicting requests all defined to fail closed before unauthorized mutation?
  [Coverage, Spec §US2 and §Edge Cases]
- [x] CHK017 Are source-only, destination-only, duplicate, neither-location, corrupt and
  interrupted transition scenarios all required to remain recoverable or explicitly
  inconsistent? [Coverage, Spec §FR-013–FR-016 and §Edge Cases]
- [x] CHK018 Are backup/restore requirements complete for overlap, links/junctions,
  hardlinks, extras, traversal, limits, insufficient space and publication crashes?
  [Coverage, Spec §FR-022–FR-026 and §Edge Cases]
- [x] CHK019 Are migration failures before and after every statement required to expose
  only exact prior or exact complete revision state? [Recovery, Spec §FR-027–FR-029]
- [x] CHK020 Are backward wall-clock movement and the exact grace/candidate boundary
  covered without shortening protection? [Edge Case, Spec §Edge Cases and §SC-006]

## Security, privacy and operational boundaries

- [x] CHK021 Are remote/shared filesystem non-goals and recognizable path/device/link
  rejection requirements stated without claiming universal mount detection?
  [Assumption, Spec §Non-Goals and §Assumptions]
- [x] CHK022 Are audit, log and structured-output exclusions explicit for bodies,
  paths, filenames, queries, tokens, raw SQL and untrusted exceptions? [Security, Spec
  §FR-037–FR-038]
- [x] CHK023 Is it explicit that MCP, document content, startup, timers, watchers and
  low-space paths cannot grant or invoke irreversible authority? [Security, Spec
  §FR-020 and §FR-040]
- [x] CHK024 Are logical removal and secure erasure clearly distinguished? [Clarity,
  Spec §FR-021]
- [x] CHK025 Are Linux, macOS and Windows offline quality evidence and synthetic fixture
  requirements explicit? [Operational, Spec §FR-041 and §SC-014]

## Notes

- Review iteration 1 passed all 25 checks after the plan made persistent intent,
  backup topology, local-filesystem limits and fresh restore explicit.
- No unresolved ambiguity remains that changes requirements or checklist scope.
