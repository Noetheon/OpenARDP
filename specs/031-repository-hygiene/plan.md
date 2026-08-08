# Implementation Plan: Repository Hygiene and Bounded Refactoring

**Branch**: `codex/f031-repository-hygiene` | **Date**: 2026-08-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/031-repository-hygiene/spec.md`

## Summary

Restore an unambiguous repository state, add a deterministic read-only sync-artifact audit, and reduce three measured
function-level hotspots without changing observable behavior. The implementation first characterizes CLI grammar/output,
Markdown parsing and local-watch scanning; then it extracts cohesive helpers, tightens the existing maintainability
allowlist, updates governance, and proves all ten gates locally and in the existing three-platform CI.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Python standard library for the hygiene audit; existing argparse and Pydantic v2 runtime only

**Storage**: Existing SQLite and content-addressed filesystem are unchanged; Git/worktree files are inspected read-only

**Testing**: pytest with branch coverage, Ruff lint/format, strict mypy, existing repository/build/drift validators

**Target Platform**: Linux, macOS and Windows; local-first CLI/library repository

**Project Type**: Python package with CLI, MCP and maintainer validation scripts

**Performance Goals**: Hygiene audit completes in linear time over Git-reported candidates, hashes only candidates and
canonical counterparts, and adds less than one second on the clean reference checkout

**Constraints**: Offline, body-free diagnostics, no automatic cleanup, no new runtime dependency, no public or persisted
contract change, no reduction in test/typing/security gates

**Scale/Scope**: 107 production modules, approximately 46,342 source lines, 1,650 functions, 151 verified worktree
conflict copies, four verified inactive Git-index copies, three selected function hotspots

**Contract/Version Impact**: None for application, workspace, contract, provider-profile and export-profile versions;
maintainer validation is additively stricter

**Trust/Operational Impact**: Conflict-copy filenames and contents are untrusted local filesystem data. Validation uses
Git's tracked/untracked facts, refuses unsafe paths and symlinks, emits relative paths and hashes only, never mutates,
and has no network or subprocess authority beyond the bounded Git inventory needed at the composition boundary. The
one-time reviewed cleanup is separate from the validator and is followed by Git integrity checks.

## Baseline and Selected Scope

The clean baseline at `658e3ae60fced4131fb807dfdeb6e02dfeabb489` passes the current maintainability audit. It contains
five module exceptions and 21 function exceptions. The selected original functions are:

| Hotspot | Baseline span | Baseline Ruff complexity | Planned result |
|---|---:|---:|---|
| `interfaces/cli.py:_parser` | 270 lines | orchestration branch fan-out | thin delegating composition with bounded command-group builders |
| `interfaces/cli.py:_success` | 166 | command rendering branch fan-out | thin JSON/human dispatcher with bounded renderer groups |
| `adapters/text_parser.py:TextParserAdapter._parse_markdown` | 173 | C901 27 | thin state-machine entry with cohesive block consumers |
| `adapters/local_watch.py:LocalWatchScanner.scan` | 118 | C901 20 | bounded traversal helpers with unchanged fail-closed result |

The combined measured baseline for these four functions is 727 lines. Success requires at least a 40 percent reduction in
their combined executable spans and removal of all four function exceptions. CLI module size remains acknowledged legacy
debt unless the extractions safely bring it below 1,000 lines; its allowance can only decrease, never increase.

## Constitution Check

### Pre-research gate

- **Articles I-II**: PASS — no source document or derived artifact contract changes; cleanup targets only proven local
  conflict copies and inactive Git metadata copies.
- **Articles III-IV**: PASS — standard-library validation, no provider or representation changes, no new abstraction
  beyond one concrete repository audit and cohesive private helpers.
- **Articles V-VII**: PASS — file content remains untrusted, diagnostics are body-free, paths are bounded, product
  context behavior is unchanged.
- **Articles VIII-IX**: PASS — tests precede extraction, thresholds and baseline evidence are explicit, and unfavorable
  results block the 10/10 claim.
- **Articles X-XII**: PASS — one bounded F031 branch, complete lifecycle, no ADR-triggering decision and all compatibility
  axes unchanged.

### Post-design gate

PASS. The design introduces no runtime port, schema, migration, provider, external dependency or new authority. The audit
is maintainer-only and read-only; automatic cleanup remains a non-goal. All behaviors map to synthetic tests and existing
cross-platform gates.

## Project Structure

### Documentation (this feature)

```text
specs/031-repository-hygiene/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── implementation-notes.md
├── analysis.md
├── contracts/
│   └── repository-hygiene-audit.md
└── checklists/
    ├── requirements.md
    └── maintainability.md
```

### Source and tests

```text
quality/
└── maintainability-policy.json
scripts/
├── audit_repository_hygiene.py       # read-only deterministic maintainer audit
└── validate_repository.py            # composes hygiene with existing gates
src/openardp/
├── adapters/
│   ├── local_watch.py                # bounded scanner orchestration/helpers
│   └── text_parser.py                # bounded Markdown state helpers
└── interfaces/
    ├── cli.py                        # stable composition/dispatch surface
    ├── cli_arguments.py              # cohesive command-group parser builders
    └── cli_output.py                 # cohesive body-free output renderers
tests/
├── integration/
│   ├── test_cli.py
│   └── test_local_watch.py
└── unit/
    ├── test_repository_hygiene.py
    └── test_text_parser.py
```

**Structure Decision**: Keep the modular local monolith and existing inward dependency direction. CLI-only helpers remain
under `interfaces`; parser and scanner helpers remain private to their adapters. The maintainer audit remains under
`scripts` so it cannot become runtime authority or package API.

## Delivery Phases

1. Capture exact baseline metrics and conflict-copy classifications in implementation evidence.
2. Add failing synthetic hygiene-audit tests and implement the read-only audit plus repository-validator integration.
3. Revalidate and remove only the exact pre-approved local duplicate inventory; verify canonical hashes and Git health.
4. Add/confirm characterization coverage, extract CLI grammar and output helpers, then remove both CLI function exceptions.
5. Characterize and decompose Markdown parsing; remove its function exception.
6. Characterize and decompose local-watch traversal; remove its function exception.
7. Update policy ceilings, inventory, roadmap, changelog and operational guidance; run convergence and all local gates.
8. Push once after local convergence, run one required ready-for-review matrix, merge normally and prune the feature branch.

## Complexity Tracking

No constitutional violations or temporary exceptions are introduced. Existing exceptions are treated as debt and may
only shrink. SQLite catalog, migration and other unselected hotspots remain explicitly out of scope.
