# Implementation Plan: Semantic Retrieval Product Surface

**Branch**: `codex/f030-semantic-retrieval-product-surface` | **Date**: 2026-08-08 | **Spec**: [spec.md](spec.md)

## Summary

Productize the exact F029 hybrid semantic profile through an opt-in `context` CLI profile and an MCP
`compile_context.retrieval_profile` selector. Local process startup alone supplies and verifies bundle paths. A shared
provider-aware compiler resolver preserves lexical defaults, exact semantic replay and one persistent MCP provider
lifecycle. Add a frozen body-free operational benchmark and stdlib-only validator for cold/warm cost.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Existing Pydantic v2 core; optional locked `semantic` extra with Transformers, Torch and
SafeTensors; no new dependency

**Storage**: Existing filesystem CAS and SQLite catalog; no migration and no persisted vectors

**Testing**: pytest, pytest-cov, Ruff, strict mypy, pre-commit, independent stdlib validators

**Target Platform**: Linux, macOS and Windows; reference model timing on macOS arm64

**Project Type**: Local modular-monolith library, CLI and read-only MCP stdio server

**Performance Goals**: Measure bundle verification, cold/warm wall time, cache reuse and peak worker RSS; reference gate
requires at least 90% warm passage-cache reuse, warm no slower than cold and peak RSS at most 1.5 GiB

**Constraints**: Offline by default; explicit all-or-none bundle configuration; no client-supplied MCP paths; sanitized
errors; lexical byte-compatible default; semantic profile is exactly F029 v0.3

**Scale/Scope**: Up to existing 32 MCP document scopes and F029 semantic limits; one optional provider per process

**Contract/Version Impact**: CLI gains additive options; MCP experimental interface moves from 0.1.0 to 0.2.0 with one
optional enum input; no application/workspace/evidence/export schema or provider-profile version change

**Trust/Operational Impact**: The local operator authorizes bundle paths at process start. Model/query/document content
remains untrusted and socket-denied in the spawned worker. Cancellation and session exit close the worker; logs and
results remain body/path free.

## Constitution Check

| Principle | Design response | Gate |
|---|---|---|
| Source truth | Product surfaces select already verified CAS/catalog evidence only. | PASS |
| Disposable accelerators | Provider vectors stay in bounded worker memory and are never persisted. | PASS |
| Provider neutrality/local first | The default remains provider-free; the reviewed adapter sits behind the existing port. | PASS |
| Thin projection | No evidence, catalog or context schema gains model-native state. | PASS |
| Data not instruction | Paths are trusted startup configuration; task/evidence text cannot alter provider options. | PASS |
| Determinism | Receipts bind exact recipe/algorithm; replay rejects drift. | PASS |
| Progressive disclosure | Existing handle-first context and optional bundle envelope remain unchanged. | PASS |
| Quality/fair evidence | Fake-provider CI plus independently validated real cold/warm evidence. | PASS |
| Simplicity/isolation | Extend existing context surfaces; no second tool, service or database. | PASS |
| Contract governance | Additive MCP minor version and canonical fixture update are explicit. | PASS |

## Project Structure

### Documentation

```text
specs/030-semantic-retrieval-product-surface/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/README.md
├── checklists/
└── tasks.md
```

### Source and validation

```text
src/openardp/interfaces/
├── cli.py
├── context_composition.py
├── mcp_protocol.py
└── mcp_server.py
scripts/
├── run_semantic_surface_benchmark.py
└── validate_semantic_surface_benchmark.py
benchmarks/semantic-surface/v0.1.0/
tests/{unit,integration,security}/
```

**Structure Decision**: Keep provider construction and local authority in `interfaces/`, reuse existing domain/port and
adapter contracts unchanged, and keep benchmark production/validation in `scripts/` so maintainer tooling does not
inflate the product package.

## Implementation Phases

1. Freeze CLI/MCP/benchmark contracts and fake-provider behavior tests.
2. Add shared retrieval-profile resolution and exact replay composition.
3. Wire CLI lifecycle and errors; prove lexical compatibility.
4. Wire MCP startup capability, per-request selection and provider shutdown; update protocol fixture/version.
5. Implement and run operational producer/validator with the exact external bundle.
6. Update docs/governance, run complete gates, converge and publish one PR.

## Complexity Tracking

No constitutional exception or new architectural abstraction is required.

## Rollback

Remove the additive CLI/MCP options, provider-aware resolver and F030 benchmark. Existing lexical and semantic receipts,
workspaces and evidence need no migration or cleanup because F030 persists no new provider state.
