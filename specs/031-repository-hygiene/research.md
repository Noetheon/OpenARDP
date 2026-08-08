# Research: Repository Hygiene and Bounded Refactoring

## Decision 1 — Detect sync artifacts; never auto-delete them

**Decision**: Add a read-only standard-library audit. It obtains the tracked/untracked inventory from Git, recognizes a
narrow numbered-conflict-copy pattern, checks canonical existence and type, and compares SHA-256 when safe. Git metadata
inspection is limited to explicitly recognized `index N` and loose-ref conflict copies within the resolved Git directory.

**Rationale**: Detection is safe to run in CI and locally. Deletion requires contextual proof and cannot be generalized
without risking legitimate files.

**Alternatives rejected**:

- Glob-and-delete: cannot distinguish user work from sync debris.
- Add patterns to `.gitignore`: hides corruption and does not protect `.git` metadata.
- Third-party repository cleaner: adds supply-chain cost for a small deterministic problem.

## Decision 2 — Use Git facts before filesystem naming heuristics

**Decision**: A worktree candidate must be untracked, match the narrow filename pattern and have a canonical tracked
counterpart before it can be classified identical or divergent. Tracked names are never disposable findings.

**Rationale**: Filenames such as `chapter 2.md` can be legitimate. Git ownership is the stable distinction between an
intended repository file and an untracked sync copy.

**Alternatives rejected**:

- Flag every numbered filename: false positives against legitimate data.
- Compare modification times: timestamps are weak evidence and drift across sync/copy operations.

## Decision 3 — Preserve the one-time inventory as evidence, not product logic

**Decision**: Record counts and hashes in implementation notes, execute one exact reviewed cleanup, then rely on the
generic audit for recurrence. Do not bake the 151 paths into production validation.

**Rationale**: Repository state is time-specific; a static deletion manifest would become dangerous and stale.

## Decision 4 — Extract cohesive CLI groups behind the existing private seams

**Decision**: Move parser construction into `interfaces/cli_arguments.py` and human rendering into
`interfaces/cli_output.py`, using small command-group helpers. `cli._parser` and `cli._success` remain callable aliases or
thin wrappers so tests and internal callers retain behavior.

**Rationale**: This removes two exception-level functions and shortens the already oversized composition module without
altering commands, main dispatch or public packaging.

**Alternatives rejected**:

- Replace argparse or redesign commands: contract change without user value.
- Introduce a command framework/registry: one implementation does not justify the abstraction.

## Decision 5 — Decompose state machines in place

**Decision**: Keep Markdown and local-watch behavior in their existing adapter modules. Extract private state/helper
objects only where they make transitions and failure boundaries independently testable.

**Rationale**: Moving these adapters across layers would add import and ownership risk. In-place private decomposition
delivers measurable function-size and complexity reductions with the smallest compatibility surface.

**Alternatives rejected**:

- Rewrite Markdown parsing with a library: changes behavior, dependencies and evidence identity.
- Replace scanning with an OS watcher: changes the polling and cross-platform contract.

## Decision 6 — Measure improvement without metric gaming

**Decision**: Compare AST source spans and optional Ruff complexity against the frozen baseline, require all four original
exceptions to disappear, prohibit new/grown exceptions, and retain full behavioral gates.

**Rationale**: Line count alone can be gamed by moving complexity. Combined exception, complexity and equivalence gates
make the claim meaningful.

## Decision 7 — Treat synchronized workspace placement as residual operational risk

**Decision**: Document that active `.git` repositories should be excluded from file synchronization or moved by the user
to a non-synchronized development root. F031 does not relocate the current workspace.

**Rationale**: Relocation changes user environment and external tooling. Detection and recovery are in scope; moving the
workspace needs an explicit operational decision.

## Baseline evidence

- Base commit: `658e3ae60fced4131fb807dfdeb6e02dfeabb489`.
- Production: 107 Python modules, approximately 46,342 lines and 1,650 functions.
- Policy: five module exceptions, 21 function exceptions; current audit passes.
- Optional Ruff complexity inventory: 61 C901, 26 PLR0912 and 17 PLR0915 findings repository-wide.
- Local sync inventory: 151 untracked candidates; 146 identical and five older than canonical tracked artifacts; four
  inactive `.git/index N` copies. No candidate lacks a canonical counterpart.

## Open risks carried into implementation

- File synchronization may create new artifacts during the feature; re-audit immediately before and after cleanup.
- CLI extraction touches a broad import surface; preserve private seam names and run focused tests after each move.
- Platform-specific stat behavior can differ; reuse existing scanner tests and rely on Linux/macOS/Windows CI.
- Large SQLite and orchestration modules remain legacy debt and must not be described as resolved by F031.
