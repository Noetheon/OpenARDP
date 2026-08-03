# Implementation Notes: Minimum Relevance and Explicit Abstention

**Feature**: `026-relevance-abstention`

**Branch**: `codex/f026-relevance-abstention`

**Date**: 2026-08-03

## Restated acceptance criteria

1. Reject incidental lexical overlap using one bounded, deterministic, integer-only policy over verified bodies.
2. Return explicit zero-evidence abstention only for valid empty/all-below-floor outcomes.
3. Preserve integrity, trust, freshness, cancellation, limits, provenance and citation resolution unchanged.
4. Bind every decision-significant policy field into a distinct replay-safe algorithm identity.
5. Preserve all six frozen F025 direct successes and make Q17/Q18 abstain without changing F025 inputs.
6. Publish body-free, independently validated, two-fresh-workspace evidence.

## Implementation

`context_relevance.py` defines canonical signals, the immutable policy and body-free observations. The adapter decorator
rereads every candidate through verified CAS, validates block/projection shape and attaches observations without
filtering. The compiler applies relevance after freshness/trust/sensitivity/deduplication and before budget admission,
records `insufficient_relevance`, recalculates fixed-point bundle accounting for notices and emits
`no_relevant_evidence` only for genuine relevance outcomes.

The CLI composes the new profile by default. Replay first loads the body-free receipt identity and deliberately selects
the legacy compiler only for a recorded legacy algorithm, preserving historical reproducibility.

## Binding result

The unchanged F025 corpus, question-set and protocol identities were verified before execution. Two fresh offline
workspaces produced identical semantic projections. The independent validator returns `RELEVANCE_ABSTENTION_READY` for
result `sha256:ff3f9d25763073cabcc8a5a8e7fb95714aa4d521df3189b76db5e3e32cbb91c3`.

- Q02/Q03/Q06/Q13/Q14/Q19 retain complete support and citation integrity.
- Q17/Q18 select zero evidence and carry bundle/receipt abstention codes.
- Selected counts become 7, 64, 16, 10, 11, 0, 0 and 10 in focused question order.
- The tool-observed two-workspace run completed in approximately 103 seconds, below the 300-second gate.

## Tradeoffs and remaining risk

The filter is deliberately exact and provider-free. It cannot solve paraphrase or German/English mismatch, and Q03
still saturates the 64-candidate cap. CAS re-verification is linear and favors integrity over maximum throughput. F027,
F028 and F029 remain separate work packages so this favorable focused result cannot hide their still-open product gaps.

## Validation evidence

Focused domain, contract, adapter, compiler, CLI, security, benchmark and unchanged F025 drift tests pass. The binding
clean staged-tree run completed with:

- Ruff lint and format across 332 files;
- strict mypy across 95 source files on native macOS and the Windows platform model;
- independent F025 input, F026 result and repository/maintainability validation;
- 1,610 passing tests, three explicit opt-in skips and 85.25% branch-aware coverage in 262.04 seconds;
- successful sdist and wheel builds;
- every pre-commit hook, including a second complete no-network pytest/coverage run;
- clean `git diff --check` and no validation-created tracked changes.

The initial clean gate correctly rejected growth beyond the frozen F018 CLI/compiler limits. Relevance algorithm,
notice and composition helpers were decomposed into bounded modules; the same policy and full suite then passed without
raising or weakening any maintainability exception.
