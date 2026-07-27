# Step-by-step contributor guide

**Status:** Current-repository workflow. Initial ZIP extraction and bootstrap are historical; do not rerun them during a
normal clone.

## 1. Clone and inspect

Read `README.md`, `START_HERE.md`, `AGENTS.md`, the constitution, accepted ADRs, feature map and active feature artifacts.
Confirm the working tree and branch before changing files.

## 2. Reproduce the baseline

```bash
uv sync --all-extras --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

Record the exact base commit, tool versions and result. Do not alter the lockfile unless the active feature explicitly
owns a reviewed dependency change.

## 3. Select exactly one feature

Use the next entry in [`spec-kit/FEATURE_MAP.md`](../spec-kit/FEATURE_MAP.md) only after its predecessor converges, merges
and has green post-merge CI. Use the matching prompt in `spec-kit/feature-prompts/`.

## 4. Complete Spec Kit planning

```text
$speckit-specify
$speckit-clarify
$speckit-plan
$speckit-checklist
$speckit-tasks
$speckit-analyze
```

Correct contradictions in the highest-level originating artifact. Do not start implementation while a critical/high
finding remains.

## 5. Implement test-first

Use `$speckit-implement` for the active phase. Add failing deterministic offline tests before changed behavior or
contracts where practical. Preserve original source bytes, provider-native artifacts, evidence provenance, local-first
defaults and provider boundaries.

## 6. Validate and converge

Run the full locked gate, repository validator, build and feature quickstart. Then run `$speckit-converge`. Append missing
tasks and implement them until no critical/high finding remains.

## 7. Commit and publish one work package

Review the complete diff, preserved runtime/contract surfaces, residual risks and rollback instructions. Commit only the
feature, create one pull request, wait for Ubuntu/macOS/Windows CI, merge only when clean, and confirm post-merge `main`
CI before starting the successor.

## Current boundary

Feature 005 implements TXT/Markdown preparation and verified lexical search. Feature 005A realigns governance without
runtime change. Feature 006 defines evidence contracts; Feature 007 implements the first
bounded Docling-native adapter. Feature 008 delivers deterministic context compilation,
body-free selection receipts, atomic persistence, replay and the `context` /
`context-receipt` CLI. Feature 009 (read-only MCP wrapping of the same application
services) is the next dependency-ordered work package. Do not reuse the pre-v3.1
numbering.
