# Research: Strategic Realignment and Contract Boundary

## Decision 1 — Keep existing canonical filenames authoritative

**Decision**: `README.md`, `.specify/memory/constitution.md`, `spec-kit/CONSTITUTION_SOURCE.md`, `spec-kit/FEATURE_MAP.md`, and `spec-kit/OPERATING_PROCEDURE.md` remain the active entry points. Version-suffixed v3.1 files are retained as labelled adoption sources and must point back to the canonical files.

**Rationale**: Replacing established paths would break contributor expectations and allow two plausible authorities. Curated adoption preserves stable navigation while retaining blueprint provenance.

**Alternatives considered**:

- Make the v3-suffixed files authoritative: rejected because existing tooling and governance point to the current names.
- Omit the v3 source files: rejected because the reviewed migration explicitly includes them and they provide auditable source provenance.
- Keep both without status labels: rejected because it leaves an authority conflict.

## Decision 2 — Integrate the complete overlay through repository-specific mappings

**Decision**: Add every non-platform overlay artifact to its intended area, mapping `adrs/` into `docs/adr/` and retaining the optional Codex prompt with a clear subordination notice. Do not commit the external blueprint directory, its manifest, validator, duplicated overlay source, or `.DS_Store`.

**Rationale**: This meets the reviewed migration scope without treating the external package as repository source or introducing duplicated packages.

**Alternatives considered**:

- Copy the external package wholesale: rejected because it duplicates files and includes platform metadata.
- Exclude the Codex prompt: viable, but rejected because checked-in workflow guidance makes the multi-feature execution model reproducible; it remains non-authoritative.
- Copy candidate ADR filenames unchanged: rejected because the live repository uses numbered ADRs under `docs/adr/`.

## Decision 3 — Adopt four decisions as ADRs 0007–0010

**Decision**: Renumber and reconcile the four candidate decisions as:

1. `0007-implementation-first.md`
2. `0008-preserve-provider-native-representations.md`
3. `0009-indexes-are-non-authoritative.md`
4. `0010-contracts-before-adapters.md`

Mark them Accepted by Feature 005A. Annotate ADR 0001 as partly superseded by ADR 0008. Change proposed ADR 0005 to Deferred pending Feature 014 rather than treating custom packaging as decided.

**Rationale**: These decisions govern the new roadmap and must exist before implementation. Explicit partial supersession preserves history. ADR 0005 was never accepted and lacks the comparative evidence now required.

**Alternatives considered**:

- Leave candidates in a separate `adrs/` directory: rejected because it creates a second ADR system.
- Mark candidates Proposed: rejected because then the adopted roadmap would depend on undecided boundaries.
- Delete or rewrite ADR 0001/0005: rejected because governance requires historical traceability.

## Decision 4 — Amend the constitution to 2.0.0

**Decision**: Produce Constitution 2.0.0 with a Sync Impact Report. Preserve every binding rule from 1.0.0 while adding implementation-first positioning, reuse-before-reinvention, thin evidence projection, disposable accelerator verification, fair baselines, complete feature isolation, cross-platform build/release gates, and stabilization evidence.

**Rationale**: The provider-neutral representation boundary and standards posture are materially redefined, so semantic-version governance requires a major increment. Removing the existing detailed clauses would be a regression.

**Alternatives considered**:

- Replace the constitution with the concise v3 source: rejected because it would silently drop tested security and engineering obligations.
- Minor version bump: rejected because the product and representation boundary are governance-significant.
- Leave the constitution unchanged and rely on ADRs: rejected because the blueprint explicitly changes project-wide non-negotiables.

## Decision 5 — Preserve historical specs; replace obsolete future prompts

**Decision**: Keep `specs/001-*` through `specs/005-*` unchanged except for separate status/index evidence where necessary. Replace old unimplemented prompts 006–014 with the v3.1 prompt sequence 005A–017 after the canonical feature map is updated.

**Rationale**: Specifications record completed feature history; prompts are forward execution instructions. Keeping both old and new future prompt sequences would be contradictory.

**Alternatives considered**:

- Renumber historical specs: rejected because it destroys traceability to merged work.
- Retain obsolete prompts with warning banners: rejected because contributors could still execute the wrong dependency order.

## Decision 6 — Add repository-contract tests for governance invariants

**Decision**: Extend offline repository tests before integration to verify the constitution version and key clauses, authoritative roadmap sequence, prompt set, ADR status/supersession, experimental contract labels, valid example JSON, and absence of prohibited standards claims in active entry points.

**Rationale**: Documentation-only migrations can regress silently. Deterministic tests make the most consequential boundaries reviewable on every supported platform.

**Alternatives considered**:

- Manual review only: rejected because roadmap and claim drift are predictable regression classes.
- Add a new documentation framework or link checker dependency: rejected because F005A needs no dependency and external link availability would violate offline determinism.

## Decision 7 — Prove runtime neutrality by path and content checks

**Decision**: Before commit, require no diff in `src/`, `schemas/`, `pyproject.toml`, or `uv.lock`; run the complete locked quality gate, build, `git diff --check`, JSON parsing, relative-link validation, and prohibited-claim searches.

**Rationale**: Passing runtime tests alone does not prove a documentation feature avoided lockfile or schema drift.

**Alternatives considered**:

- Rely only on the test suite: rejected because tests need not cover byte-level repository scope.
- Add snapshots of all runtime files to the repository: rejected as redundant and maintenance-heavy; Git path-scoped diff is sufficient.

## Decision 8 — Treat current contracts as experimental design guidance

**Decision**: Add the contract and conformance materials exactly as design guidance, with explicit non-normative/experimental labels. The receipt example is illustrative and is not a public schema in F005A.

**Rationale**: Feature 006 owns the first provider-neutral contract semantics. Stabilizing or validating a contract shape in F005A would violate feature isolation and contracts-before-adapters sequencing.

**Alternatives considered**:

- Publish the example as a schema now: rejected because it bypasses Feature 006 specification and compatibility design.
- Omit the example: rejected because it usefully communicates the planned audit boundary when correctly labelled.
