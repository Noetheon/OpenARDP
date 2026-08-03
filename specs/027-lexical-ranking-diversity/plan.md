# Implementation Plan: Lexical Ranking, Diversity and Source Quotas

**Branch**: `codex/f027-lexical-ranking-diversity` | **Date**: 2026-08-03

## Summary

Introduce a pure immutable allocation policy and a deterministic allocator after F026 classification. Decompose the
existing compiler classification logic into a focused service rather than expanding the compiler hotspot. The allocator
ranks, exact-body deduplicates, groups by document, applies a hard 16-item quota and fair round-robin interleaving. The
CLI uses the combined profile while legacy/F026 identities remain replayable. A paired F026/F027 runner evaluates both
compilers over each of two newly ingested frozen F025 workspaces.

## Technical Context

- Python 3.12, Pydantic v2, existing SQLite/CAS; no new dependency or network use.
- Pure integer comparisons, canonical SHA-256 policy identity and stable lexical/source tie-breakers.
- Existing context bundle/receipt schemas and namespaced body-free extensions remain sufficient.
- Maximum 512 candidates and 16 selected items per document scope.
- Full Ruff, formatting, strict mypy, pytest coverage, build, pre-commit and repository validation.

## Architecture

```text
verified candidates -> freshness/trust/F026 relevance -> deterministic rank
                                                        |
                                               exact-body dedupe
                                                        |
                                               per-document queues
                                                        |
                                         quota + fair round-robin
                                                        |
                                               existing budgeter
```

Pure policy and allocation types live in `domain/context_ranking.py`; orchestration and compatibility wrappers live in
`services/context_ranking.py` and `services/context_compiler.py`. Composition belongs in `interfaces/` and evaluation in
`scripts/`. Dependencies continue pointing inward.

## Constitution Check

All gates pass by design: originals remain authoritative, ranking is disposable, provider-free, deterministic and
measured; document content cannot initiate tools; no schema/storage/cloud/identity exception or ADR is required. F027 is
bounded and excludes F028/F029.

## Phases

1. Freeze requirements, paired comparison and anti-overfitting boundary.
2. Add policy, rank, dedupe, quota, replay and security tests first.
3. Extract classification helpers and implement the smallest coherent allocator.
4. Compose F027 by default while preserving explicit legacy and F026 replay.
5. Run paired benchmark twice, validate reference evidence, document limitations and converge.

## Risks and Controls

- **Overfitting**: runtime receives task/candidates/policies only; evaluation oracle stays in scripts.
- **Lost provenance**: exact duplicates retain the highest-ranked candidate and record every rejection.
- **False diversity**: no reserved slots or relevance override.
- **Replay drift**: combined identity includes both canonical policies and old identities remain byte-identical.
- **Hotspot growth**: move existing classification into a focused module and keep compatibility exports.
