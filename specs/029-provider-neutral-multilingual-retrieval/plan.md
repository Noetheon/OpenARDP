# Implementation Plan: Provider-Neutral Multilingual Retrieval

**Branch**: `codex/f029-provider-neutral-multilingual-retrieval` | **Date**: 2026-08-03

## Summary

Add an optional bounded semantic candidate source over exact current text/CSV/rich evidence. A provider-neutral port
returns fixed-point similarity observations; the first real adapter runs a pinned multilingual E5 model in a persistent
spawned, socket-denied offline worker with an exact in-memory passage cache. F027 allocation and exact evidence resolution
remain authoritative. Compare F027 and F029 direct treatments over all unchanged F025 questions in two fresh workspaces.

## Technical Context

- Python 3.12, Pydantic v2, `uv` locked.
- Core remains Pydantic/RFC8785 only. Optional `semantic` extra pins Transformers/Torch/Safetensors.
- No catalog/public-schema migration. Embeddings are worker-memory-only derived accelerators.
- Model: `intfloat/multilingual-e5-small`, exact revision, 384 dimensions, 512-token maximum, MIT license.
- Runtime: local assets only, no remote code, socket denied, spawn worker, bounded IPC/time/text/batch/cache.
- Benchmark: unchanged F024/F025 identities and evaluator, F023 PDF bundle, F028 CSV path, two fresh workspaces.

## Architecture

1. `domain/semantic_retrieval.py`: provider recipe, score/policy/limits and fixed-point invariants.
2. `ports/semantic_retrieval.py`: narrow provider protocol and sanitized failure taxonomy.
3. `adapters/embedding_bundle.py`: exact source-lock/installation verification.
4. `adapters/e5_semantic.py`: isolated offline E5 provider with model/passage cache.
5. `adapters/semantic_candidates.py`: exact snapshot enumeration, CAS verification, provider scoring and eligibility.
6. `interfaces/context_composition.py`: explicit opt-in semantic compiler; lexical default unchanged.
7. benchmark/validator: paired all-question comparison and frozen body-free result.

## Constitution Check

| Principle | Response | Gate |
|---|---|---|
| Originals authoritative | Provider sees verified disposable text projections; selection returns exact existing evidence. | PASS |
| Optional model-specific caches | Vectors remain provider/profile-namespaced worker memory and are never authoritative. | PASS |
| Provider-neutral core | Narrow port plus fake and real adapter; default compiler has no provider. | PASS |
| Local-first | Bundle is explicitly provisioned; binding runtime is offline/socket-denied. | PASS |
| Data not instruction | Prefix/config are trusted code; document/query text is bounded inert input. | PASS |
| Determinism | Exact recipes, integer scores, total ordering and two-run semantic projection. | PASS |
| Progressive disclosure | Existing context budget, source quota, receipts and exact get remain unchanged. | PASS |
| Fair evidence | F025 questions/oracles stay frozen; lexical baseline and failures are retained. | PASS |
| Feature isolation | No generation, vector DB, cloud provider, schema migration or later feature. | PASS |

## Implementation Phases

1. Freeze spec, ADR, model source lock, comparison policy and security/claim boundaries.
2. Add model-free domain/port/adapter contract tests and exact candidate-source tests first.
3. Implement bundle verification, provider protocol and semantic candidate composition.
4. Implement optional spawned E5 adapter and explicit provision/verify commands.
5. Add paired producer/stdlib validator, run exact model/corpus twice and commit the result without bodies.
6. Converge docs, quality/build/CI, commit, publish and merge independently.

## Rollback

Remove the semantic extra, opt-in composition, provider/bundle adapters and F029 benchmark. Existing workspaces and lexical
receipts need no migration; no persisted vector or provider-specific evidence remains to reclaim.
