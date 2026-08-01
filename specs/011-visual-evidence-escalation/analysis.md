# Specification Analysis: Visual Evidence Escalation

## Pre-implementation analysis

The required read-only Spec Kit analysis covered `spec.md`, `plan.md`, `tasks.md` and
Constitution 2.0.0 after task generation.

Initial metrics were 30 functional requirements, 10 buildable success criteria, four
user stories and 86 tasks with 100 percent requirement/task coverage, no unmapped task,
no duplication and no constitution violation.

Five findings were remediated at their highest originating artifacts before runtime
implementation:

| ID | Initial severity | Resolution |
|---|---|---|
| I1 | HIGH | Removed the unsupported claim that F010 automatically stales object-only interpretation dependencies; current use rechecks the exact parent visual scope. |
| U1 | HIGH | Added a fixed 1,000-PPM rotation-adjusted provider/renderer aspect admission rule and `page_geometry_mismatch`. |
| A1 | MEDIUM | Removed the unnecessary one-unit crop clamp; all geometry is strictly in bounds or rejected. |
| C1 | MEDIUM | Standardized ContextBundle handle and `artifact_id` on the descriptor CAS object, which names the crop. |
| C2 | MEDIUM | Replaced an impossible whole-manifest freeze with an allowlisted visual-extra dependency diff while freezing every prior contract/profile. |

The second read-only pass found zero unresolved critical, high, medium or low findings,
100 percent FR/SC coverage, no placeholder and no extension hook. Implementation was
unblocked only after that pass.

## Final convergence analysis

The post-implementation read-only pass reloaded the active feature through
`check-prerequisites.sh --require-tasks --include-tasks` and compared the complete
specification, plan, 86 tasks and all twelve constitutional articles. No extension
hooks were configured.

| Metric | Result |
|---|---:|
| Functional requirements | 30 |
| Buildable success criteria | 10 |
| User stories | 4 |
| Tasks | 86 |
| Requirement/task coverage | 100% |
| Unmapped tasks | 0 |
| Unresolved ambiguity/duplication | 0 |
| Constitution conflicts | 0 |
| Critical/high/medium/low findings | 0 / 0 / 0 / 0 |

The implementation-specific review initially translated the cross-platform byte claim
into one shared fixed SHA-256 vector. Remote CI then demonstrated that equally versioned
native PDFium wheels can produce different raster bytes on macOS and Linux. The highest
source was corrected: renderer and encoder recipes now bind exact wheel RECORD-content
fingerprints, each platform proves twenty-process repeatability, and distinct native
wheels cannot collide in the same cache identity.
The delivered source/rotation/display geometry is consistent across specification,
ADR, model, renderer, descriptor and tests. A convergence security review then found
that the initial multiprocessing result channel implicitly used Pickle. It was replaced
before final convergence with a bounded, duplicate-key-rejecting JSON metadata frame
plus raw PNG bytes in both directions; no object deserialization crosses the untrusted
child-to-parent boundary. The follow-up assessment has zero remaining findings, so no
convergence task is required.
