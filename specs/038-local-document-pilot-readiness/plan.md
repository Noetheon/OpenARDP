# Implementation Plan: Local document pilot readiness

**Branch**: `codex/f038-local-document-pilot-readiness` | **Date**: 2026-09-19 | **Spec**: [spec.md](spec.md)

## Summary and technical context

Make the existing explicit bundle output useful to a human, document one verified local workflow, and prepare a manual prospective test of its practical value. Python 3.12, existing Pydantic/CLI/SQLite/CAS; no new dependencies, providers or formats. CLI entry flags and JSON remain unchanged. Tests use pytest's default network denial and synthetic documents. Existing CI checks Linux/macOS/Windows; guide commands target a POSIX shell with Python/uv/Git.

## Design

- `src/openardp/interfaces/cli_output.py`: add a small human bundle renderer called only when the context response contains the already requested bundle. Show numbered evidence, representation/reason, exact document/version/representation and block locator or rich reference/projection IDs, untrusted body or artifact handle. Reuse `safe_text` with a small shared extension for DEL/C1 and U+061C, U+200E–U+200F, U+202A–U+202E, U+2066–U+2069; ordinary Unicode remains unchanged. never resolve paths, execute content or invent page/file details. Structured bodies use deterministic JSON text. Empty bundle is explicit.
- `tests/integration/test_cli_context.py` or a focused sibling: test opt-in text, structured, handle-only, empty, control characters, default no-body and JSON parity. Source and persisted bundle bytes must not change.
- `docs/30_LOCAL_DOCUMENT_WORKFLOW.md`: short core path and links to existing optional model provisioning/MCP commands. Test commands in a fresh synthetic workspace, including repeat ingest, exact context/source inspection and receipt replay. Do not register a host integration without an actual chosen store.
- `specs/038-local-document-pilot-readiness/contracts/pilot-protocol.md`: normative prospective human evaluation, fixed decision and stop rules. `pilots/local-document/v0.1.0/` contains empty CSV records and pending decision template plus concise run instructions. No evaluator, timing harness, new schema or app.
- `README.md`, `START_HERE.md`, canonical requirements/strategy/governance and semantic evidence documentation: prioritize one local recurring-document workflow, pause wider expansion, link actual-use protocol, and explain legacy scoring limits while preserving frozen files.

## Compatibility and trust

No public schema, CLI grammar, application/workspace/provider/export version or persisted identity impact. Opted-in content uses the existing untrusted envelope. The shared human escaper receives only the enumerated control hardening; existing escaper callers also benefit while JSON/data remain unchanged. The formatter does not generate answers or load additional objects. Actual user documents, tasks and judgments remain outside Git; bundled examples/smoke are synthetic and cannot count as study evidence. F015 release NO-GO remains authoritative.

## Constitution check

PASS before research and after design: originals authoritative, disposable state unchanged, provider-neutral/local-first core, thin evidence preserved, no source execution, strong baselines and explicit claim limits. High-assurance lifecycle applies because evaluation methodology determines investment claims. One bounded concern is a workflow ready for a fair pilot, not a new platform capability. Predecessor F037 is merged. No ADR exception.

## Execution and gates

Analyze requirements/plan/tasks/protocol before implementation. Then CLI tests/fix/guide and manual pilot templates may run in parallel in disjoint files. Root aligns canonical docs and runs the synthetic smoke. Independent convergence precedes lifecycle compaction with committed history. Required Ruff, format, strict mypy, full pytest/coverage, governance, maintainability, packaging and three-platform CI must pass before merge. Real pilot registration awaits the user's folder/tasks and reviewer; no positive verdict is part of this feature's acceptance.

## Complexity tracking

No new runtime abstraction or justified exception. Manual CSV records deliberately avoid a new benchmark subsystem.
