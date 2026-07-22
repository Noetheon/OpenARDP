# OpenARDP Spec Kit operating procedure

## Before every feature

1. Pull the latest default branch and confirm a clean working tree.
2. Read the feature prompt and the previous feature's convergence report.
3. Verify `specify version` matches `spec-kit/PINNED_VERSION.txt`.
4. Run `specify integration status` and resolve errors.
5. Start Codex from the repository root.

## Specification gate

Use the feature prompt with `$speckit-specify`. The specification must:

- focus on user-visible or operator-visible behavior rather than implementation details;
- contain prioritized independently testable stories;
- include Given/When/Then acceptance scenarios;
- include negative and security scenarios;
- define measurable success criteria;
- list explicit non-goals and dependencies.

Then run `$speckit-clarify` until no material ambiguity remains.

## Planning gate

Use `$speckit-plan` and require it to cite relevant project docs and ADRs. The plan must identify:

- exact architecture boundaries;
- data model and contracts;
- migration or compatibility impact;
- security/privacy impact;
- performance and resource constraints;
- test strategy;
- rejected alternatives.

Run `$speckit-checklist`, then `$speckit-tasks`. Tasks must include exact file paths, dependencies and tests.

## Consistency gate

Run `$speckit-analyze`. Critical or high issues block implementation. Fix the source artifact and regenerate downstream
artifacts rather than patching only `tasks.md`.

## Implementation gate

Run `$speckit-implement` for one phase or bounded task group at a time. Require:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

No network access is allowed in unit tests.

## Convergence and review gate

Run `$speckit-converge`. If it appends tasks, implement and converge again. Before merge:

- inspect the diff;
- verify source immutability and trust-boundary tests;
- update docs/ADRs/schemas as needed;
- record exact checks and results;
- keep the pull request limited to the active feature.
