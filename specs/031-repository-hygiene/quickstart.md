# Quickstart: F031 Repository Hygiene

## 1. Synchronize the locked environment

```bash
uv sync --all-extras --locked
```

## 2. Run focused acceptance checks

```bash
uv run pytest tests/unit/test_repository_hygiene.py
uv run pytest tests/unit/test_text_parser.py tests/integration/test_local_watch.py
uv run pytest tests/integration/test_cli.py tests/integration/test_cli_mcp.py
```

## 3. Run deterministic policy audits

```bash
uv run python scripts/audit_repository_hygiene.py --root .
uv run python scripts/audit_maintainability.py --root . --policy quality/maintainability-policy.json
uv run python scripts/validate_repository.py
```

## 4. Run all local gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv build
uv run pre-commit run --all-files
```

## Expected outcome

The implementation notes may report 10/10 only when SC-001 through SC-010 all have captured passing evidence. A clean
audit never modifies the repository. Future duplicate findings must be reviewed; do not delete them from a glob alone.

## Rollback

Code and policy changes can be reverted as one F031 commit. The one-time local duplicate cleanup is not reconstructed by
rollback because it removes only verified redundant or superseded conflict copies; canonical tracked content remains in
Git. If any pre-clean candidate classification changes, stop and preserve that candidate outside automated cleanup.
