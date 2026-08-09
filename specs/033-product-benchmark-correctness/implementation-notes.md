# Implementation Notes: F033 Product Benchmark Correctness

## Acceptance criteria restatement

F033 is complete only when one F020 reference/full run can prepare PDF, DOCX and PPTX together with model authority bound
only to PDF; invalid rich inputs fail before text or scale work and before staging; every public parser-domain failure maps
to the stable body-free CLI category; and corpus, thresholds, evidence schemas, validator behavior and historical results
remain unchanged.

## Implementation outcome

- Added one preflight boundary that validates all selected rich fixture SHA-256 values and constructs three independent
  parser instances before environment capture, temporary directories or text profiles.
- Bound optional model root and manifest only to the PDF instance. DOCX and PPTX always use model-free instances.
- Passed the preflighted instances into rich execution, removing the conflicting per-fixture construction.
- Preserved the existing no-bundle behavior: PDF becomes explicitly unavailable while DOCX/PPTX continue.
- Added an explicit `ParserError` CLI catch before generic I/O/value failures. The command emits only
  `benchmark_execution_failed`, exits 6 and records only the safe exception class at debug level.
- Added regression coverage for all currently public parser subclasses, phase ordering, temporary-directory cleanup,
  non-rich profile isolation and exact format-to-model binding.

## Red-to-green evidence

The first focused run failed exactly at the new boundaries: `_preflight_rich` was absent and 13 parser subclasses that do
not also inherit `ValueError` escaped the CLI. After implementation, the focused F020 suite passed all 37 tests.

An actual preflight against the locally provisioned reviewed PDF bundle completed in 0.5 seconds and produced:

```text
docx: no model bundle
pdf: sha256:442ab96f3d56146c63e6e98dfb7452a679571b4343e9b01e2bdb02b3eb0c74b8
pptx: no model bundle
```

This validates real bundle identity and configuration separation without rerunning the unrelated 50-minute text/scale
measurement.

## Compatibility, tradeoffs and risks

- No public schema, identifier, persistence, migration, dependency, provider profile or evidence-file version changed.
- Preflight reads the three small rich fixtures twice (before expensive work and again at use time). The second digest
  check intentionally detects changes between preflight and execution.
- Reference/full startup now validates the PDF bundle before text work. This is a bounded up-front cost that prevents a
  much larger late failure and validates the bundle only once per process.
- The harness correction does not prove retrieval quality, latency improvement or downstream answer utility; those remain
  separate successor features using a holdout frozen before tuning.
- Rollback is a normal revert of the F033 commit; no data migration or evidence invalidation is required.

## Validation evidence

- Focused F020 regression suite: 37 passed with `--no-cov`.
- Real offline PDF bundle preflight: passed with the exact identity above.
- `uv run --locked ruff check .`: passed.
- `uv run --locked ruff format --check .`: 401 files already formatted.
- `uv run --locked mypy src`: passed for 129 source files.
- `uv run --locked pytest`: 1,753 passed, 4 skipped in 181.44 seconds with 85.48% branch coverage.
- `uv run --locked python scripts/validate_repository.py`: passed with zero diagnostics.
- `git diff --check`: passed.
- `uv build`: built the source distribution and wheel successfully.
- `uv run --locked pre-commit run --all-files`: Ruff, formatting, strict mypy and the complete offline pytest/coverage
  hooks passed from the final compacted tree.
