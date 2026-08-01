# Research: Repository Hygiene and Maintainability

## Decision: Use deterministic AST span metrics as a non-regression guard

**Rationale**: Python's standard-library AST provides cross-platform module and function spans without importing or
executing product code. Span is understandable in review and deterministic across supported platforms. The guard can
allow measured legacy debt while rejecting growth and stale exceptions.

**Alternatives considered**:

- Add a complexity-analysis dependency: rejected because F018 does not justify new supply-chain surface and tool
  versions can change scoring semantics.
- Enable every Ruff complexity rule immediately: rejected because the audit found 184 current findings, including
  protocol signatures and validated domain invariants; mass suppression or broad rewrites would reduce signal.
- Record only an informational report: rejected because it would not prevent regression.

## Decision: Refactor three orchestration hotspots with existing black-box coverage

**Rationale**: Baseline inspection measured `evaluate_release` at 327 lines, CLI `_execute` at 248 lines and
`reconcile_watch_scan` at 291 lines. They span service, interface and adapter layers, have mature integration suites and
can be decomposed without changing contracts. They provide higher risk reduction than formatting already-clean code.

**Alternatives considered**:

- Split the complete SQLite catalog into mixins: rejected for this feature because the class has cross-cutting
  transactional helpers and protocol conformance; a mechanical inheritance split would increase hidden coupling.
- Rewrite command routing with a framework: rejected because it adds dependency and abstraction cost.
- Refactor only the newest Graph modules: rejected because their focused code is already small and over 90 percent
  covered; repository-level measurements identify higher-risk locations.

## Decision: Separate focused tests from repository-wide coverage

**Rationale**: The F017 quickstart's 29 focused tests passed but the command exited non-zero because global pytest
configuration applied coverage to the entire package and measured 21.93 percent. Focused commands therefore use
`--no-cov`; the authoritative full command remains unchanged and enforces at least 85 percent branch coverage with
network disabled.

**Alternatives considered**:

- Lower or omit the global threshold: rejected by Constitution Article VIII.
- Describe non-zero focused runs as expected: rejected because that makes quick validation misleading.
- Duplicate package-wide tests in every quickstart: rejected because it removes the value of a focused check.

## Decision: Preserve ignored virtual environments during cleanup

**Rationale**: The clean checkout contains only ignored caches, coverage/build output and the required centralized
virtual environment. No generated artifact is tracked. Cache deletion after validation is safe, but deleting `.venv`
would destroy reproducible tooling without improving repository history.

**Alternatives considered**:

- Run an indiscriminate ignored-file clean: rejected because it would remove `.venv`.
- Track generated reports or caches: rejected because they are disposable local state.

## Baseline evidence

- Production source: 81 modules, 39,392 lines, 1,401 functions and 557 classes.
- Largest module: `src/openardp/adapters/sqlite_catalog.py`, 6,761 lines.
- Initial optional complexity sweep: 184 findings; it is diagnostic, not an enabled gate.
- Authoritative configured gates at baseline: Ruff PASS, format PASS for 240 files, strict mypy PASS for 81 files,
  lockfile check PASS and repository validation PASS.
- Tracked generated/cache artifacts: zero.
