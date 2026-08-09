# Implementation Notes: F032 Documentation Governance

## Acceptance criteria restatement

F032 is complete only when new work uses deterministic risk-proportionate documentation, every completed feature retains
requirements/evidence/contracts, transient historical Markdown is removed without broken links or evidence loss, the
constitution and all dependent guidance agree, and complete repository gates pass.

## Frozen baseline

- Base commit: `b55dd68e0d845af3cd81b0df211bffc83ea27934`.
- Tracked Markdown: 510 files and 3,125,104 bytes.
- Feature Markdown: 347 files and 41,392 lines across 32 completed feature directories.
- Classified transient baseline: 182 planning/task/analysis files, 61 checklist files and 32 generated feature prompts;
  275 candidate Markdown files total.
- Protected baseline: all `spec.md`, `implementation-notes.md`, contract Markdown, ADRs, canonical docs, licenses,
  machine-readable evidence and source artifacts.

## Implementation outcome

- Ratified Constitution 3.0.0 and kept its managed/source copies byte-identical.
- Classified changes as routine, standard or high assurance in contributor, agent, operating-procedure, template and
  integration guidance. Unknown or mixed changes fail upward; executable CI remains governed by its existing policy.
- Removed 275 tracked transient files: 182 plans/research/data-model/quickstart/task/analysis files, 61 checklists and 32
  generated prompts. F032's own planning artifacts were compacted after convergence and were never committed.
- Replaced the manually duplicated feature-status table with `spec-kit/FEATURE_MAP.md` as the sole registry.
- Replaced feature-specific transient-file assertions with one generic invariant covering all current and future feature
  directories, plus safe active-locator validation and focused negative tests.

## Preservation and measurements

| Measure | Before | After | Change |
|---|---:|---:|---:|
| Tracked/current Markdown files | 510 | 238 | -272 (-53.3%) |
| Markdown bytes | 3,125,104 | 1,685,591 | -1,439,513 (-46.1%) |
| Feature-record Markdown files | 347 | 106 | -241 (-69.5%) |
| Feature-record Markdown lines | 41,392 | 16,092 | -25,300 (-61.1%) |
| Historical normative contract Markdown | 39 | 39 | all retained; one link migrated |
| New F032 normative contract Markdown | 0 | 1 | added |

All 39 historical contract Markdown files remain present. Thirty-eight are byte-identical. The sole reviewed edit is in
F024's contract index, where a link to the removed quickstart now targets the durable real-world-corpus guide; no contract
statement changed. The composite ordered path/file hash therefore moved from
`b83502b75c15fa73e65c316c82125590d6f00aab21828d1158334eb6f0034b6e` to
`518c51f42210948f417512cd1feef5d43320405b43588ddf9417b0c2ce7f8c89`. All 33 feature directories retain both durable
records. The file-count difference is 272 rather than 275 because F032 adds its specification, implementation notes and
one retention contract.

## Compatibility, risk and rollback

- Product behavior, public schemas, persisted identities, dependencies, providers and workspace formats are unchanged.
- The F015 source-tree allowlist no longer names the removed F015 prompt; this changes future candidate source-tree
  identity as expected but does not alter release criteria or previously committed evidence claims.
- Git history was not rewritten. Exact removed bytes remain available with normal `git show <pre-F032-commit>:<path>`;
  therefore this improves current-tree navigation and maintenance, not historical clone size.
- Rollback is a normal revert of the F032 commit. Base commit:
  `b55dd68e0d845af3cd81b0df211bffc83ea27934`.

## Validation evidence

- Focused governance/validator/CI-policy suite: `75 passed` with `--no-cov`.
- Repository validation: passed with zero broken Markdown links or governance findings.
- `uv run --locked ruff check .`: passed.
- `uv run --locked ruff format --check .`: 381 files already formatted.
- `uv run --locked mypy src`: passed for 109 source files.
- `uv run --locked pytest`: 1,730 passed, 4 skipped in 186.76 seconds; 85.47% branch coverage.
- Release-input drift and boundary slice: 11 passed; release corpus generator reported all 10 files current.
- Maintainability, repository-hygiene and CI-policy audits: passed with zero findings.
- `uv build`: source distribution and wheel built successfully.
- `uv run --locked pre-commit run --all-files`: all hooks passed, including the complete coverage suite.
- `git diff --check`: passed.

Remote required-check results remain attached to the pull request and merge rather than causing a post-validation
documentation-only commit that would rerun the expensive matrix.
