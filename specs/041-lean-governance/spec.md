# F041 — Lean governance: usefulness first

**Status:** Implemented; validation results in [implementation notes](implementation-notes.md)
**Created:** 2026-09-24
**Constitution:** amended 3.0.0 → [4.0.0](../../.specify/memory/constitution.md)
**Supersedes in part:** the mandatory Spec Kit lifecycle of [F032](../032-documentation-governance/spec.md) and the
[F038 pilot](../038-local-document-pilot-readiness/spec.md) as a precondition for further product work

## Task served

The maintainer, and the agents working for them, need to spend their time on changes a person or agent can use,
rather than on process artifacts. A project audit found:

- most recent features produced planning and evaluation records, not usable capability;
- high-assurance work required the full lifecycle (specify through converge) regardless of benefit;
- further development was paused until a 30-task, three-arm human pilot finished, which had not started.

Meanwhile basic user paths such as MCP connection and multi-core PDF parsing were broken.

Improvement is observed when more changes reach users and fewer records are written per change, while the quality
gates stay as strict as before.

## Acceptance criteria

1. The constitution (and its byte-identical mirror) is version 4.0.0 with a Sync Impact Report.
   - Article XI requires a concise `spec.md` and `implementation-notes.md` for behavior, contract, schema, identity,
     migration, trust, provider and dependency changes, and treats Spec Kit stages as optional tools.
   - Article XII limits mandatory ADRs to irreversible or architectural decisions.
   - Article XIII (Usefulness First) requires each feature to name the task it improves and treats real use, recorded
     in a lightweight usage log, as the primary evidence.
   - Article XIV (Agent Efficiency) requires compact, located, verifiable agent output.
2. `AGENTS.md`, `CONTRIBUTING.md`, the feature map and the specs README describe the same lean rules and link the usage
   log.
3. `pilots/usage-log/` provides a one-line-per-task template that needs no study design. The F038 protocol and
   templates remain available and are marked as no longer a development gate.
4. The quality gates, the three-platform CI, the release NO-GO and the evidence-integrity principles (Articles I–X) are
   unchanged.

## Decisions

- Keep the strict technical gates. Drop only the mandatory process stages.
- Real use comes first. The formal pilot protocol stays available for a future, deliberate comparison but blocks
  nothing.
- No ADR is needed: this changes the development process, not the product architecture. The constitution's own
  amendment rules apply instead.
