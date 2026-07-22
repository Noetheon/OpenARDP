# Migration from the previous OpenARDP blueprint

## Can the previous ZIP still be used?

Yes. It contains a coherent architecture, schemas, tests, work packages and a Codex prompt. It is not technically invalid.

## Why the revised package is preferred

The revised package adds:

- a pinned GitHub Spec Kit integration;
- an OpenARDP constitution;
- native Codex Spec Kit bootstrap;
- bounded feature mapping for every work package;
- ready-to-use feature specification inputs;
- analyze and convergence gates;
- scripts for macOS/Linux and Windows;
- a safer first-session procedure;
- an explicit source-of-truth hierarchy to prevent documentation drift.

## Existing repository migration

If development has not started, replace the old extracted folder with this package.

If development has already started:

1. create a branch;
2. copy `spec-kit/`, `scripts/bootstrap-speckit.*`, `scripts/apply-speckit-overlay.py`, `docs/12_*`, `docs/13_*` and
   `docs/14_*` into the repository;
3. merge the updated `AGENTS.md`, `README.md`, execution plan and master prompt carefully;
4. commit the migration;
5. run the bootstrap script;
6. create a feature specification for the current bounded state rather than pretending completed code is unimplemented;
7. run analyze/converge to identify drift.

Do not delete accepted ADRs, schemas, tests or existing implementation merely to match a newly generated task list.
