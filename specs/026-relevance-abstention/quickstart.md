# Quickstart: F026 Minimum Relevance and Explicit Abstention

## Prerequisites

```bash
uv sync --locked --all-extras
```

Unit and integration validation requires no network or external model. The unchanged real-corpus slice additionally
requires the exact F023 PDF bundle documented by F025.

## 1. Validate requirements and repository governance

```bash
.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
uv run python scripts/validate_repository.py
```

Expected: F026 is active and all governed artifacts are present.

## 2. Run focused behavior and security tests

```bash
uv run pytest tests/domain/test_context_relevance.py tests/unit/test_context_relevance.py \
  tests/integration/test_context_relevance.py tests/security/test_context_relevance_boundaries.py
```

Expected: integer boundaries, strong matches, genuine abstention, failure distinctions and replay pass offline.

## 3. Validate the unchanged F025 comparison slice

```bash
uv run python scripts/validate_semantic_e2e_benchmark.py --repository-root . --inputs-only
uv run python scripts/run_relevance_benchmark.py \
  --pdf-bundle /Users/Shared/openardp-pdf-bundle-2.114.0-v1-measured \
  --output /Users/Shared/openardp-f026-result
uv run python scripts/validate_relevance_benchmark.py \
  --result /Users/Shared/openardp-f026-result
uv run pytest tests/integration/test_context_relevance_reference.py
```

Expected: Q17/Q18 abstain, prior successful Q02/Q03/Q06/Q13/Q14/Q19 remain fully supported and all citations resolve.

## 4. Run complete quality gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run python scripts/validate_repository.py
uv build
uv run pre-commit run --all-files
```

Expected: every command succeeds, branch coverage remains at least 85%, and no tracked file changes during validation.
