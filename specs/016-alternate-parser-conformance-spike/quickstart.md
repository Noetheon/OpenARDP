# Quickstart: Alternate Parser Conformance Spike

## Prerequisites

- Python 3.12
- Locked project environment from `uv sync --all-extras --locked`
- No network access is required or permitted by the tests

## Focused validation

From the repository root:

```bash
uv run --locked python scripts/validate_alternate_conformance.py --check
uv run --locked pytest \
  tests/contract/test_alternate_conformance.py \
  tests/security/test_alternate_conformance_boundaries.py
```

Expected result: the independent process runs with isolated/no-site flags, accepts/rejects
the complete F006 corpus as declared, reproduces all golden identities, produces deterministic
TXT/CSV evidence, passes reference validation and matches the committed decision report.

## Isolation probe

```bash
uv run --locked python -I -S scripts/alternate_evidence_process.py --self-check
```

Expected result: a canonical success envelope reports that project and third-party imports
are unavailable. This proves a bounded process boundary, not a universal sandbox.

## Full repository validation

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run python scripts/validate_repository.py
uv build
```

Review `conformance/alternate-parser/v0.1.0/expected/decision.json` and
`specs/016-alternate-parser-conformance-spike/implementation-notes.md` before making any
provider-neutrality claim.
