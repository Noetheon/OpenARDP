# Spec Kit feature map

OpenARDP is implemented as bounded Spec Kit features. Do not ask Codex to implement the entire platform in one feature.

| Order | Feature directory | Work package | Primary independently demonstrable outcome |
|---:|---|---:|---|
| 1 | `001-repository-baseline` | 0 | The repository installs and all quality gates pass. |
| 2 | `002-domain-models-schemas` | 1 | Canonical models validate and hash deterministically. |
| 3 | `003-cas-sqlite-catalog` | 2 | Objects and versions persist atomically and safely. |
| 4 | `004-text-ingestion-slice` | 3 | TXT/MD is parsed once and reused on unchanged ingest. |
| 5 | `005-lexical-search` | 4 | Exact source-backed retrieval works through SQLite FTS5. |
| 6 | `006-docling-adapter` | 5 | PDF/DOCX/PPTX are normalized through an isolated adapter. |
| 7 | `007-context-compiler` | 6 | A bounded evidence bundle is compiled for a task. |
| 8 | `008-read-only-mcp` | 7 | Codex can query prepared documents without arbitrary file access. |
| 9 | `009-local-watcher` | 8 | Saving a watched file automatically schedules one stable ingest. |
| 10 | `010-reconciliation-derivation-dag` | 9 | Unchanged blocks and derivatives survive a small edit safely. |
| 11 | `011-visual-evidence` | 10 | Exact source assets/crops and optional derived OCR/captions are available. |
| 12 | `012-portable-ardp-package` | 11 | A package can be exported, verified and safely imported. |
| 13 | `013-benchmark-security-gate` | 12 | Claims are supported by reproducible quality, cost and security evidence. |
| 14 | `014-microsoft-graph-spike` | 13 | A least-privilege connector design is validated with mocks only. |

## Required flow for each feature

```text
$speckit-specify
$speckit-clarify
$speckit-plan
$speckit-checklist
$speckit-tasks
$speckit-analyze
$speckit-implement
$speckit-converge
```

For the smallest repository-only feature, clarification may conclude that no open ambiguity remains, but the command should
still be run and recorded.

## Feature completion gate

A feature is complete only when:

1. every mandatory acceptance scenario has an automated or documented validation;
2. `speckit.analyze` has no unresolved critical issue;
3. implementation checks pass;
4. `speckit.converge` reports convergence;
5. relevant docs, ADRs and schemas are updated;
6. a commit or pull request contains only the bounded feature scope.
