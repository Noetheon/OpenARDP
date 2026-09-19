# F038 Validation

Use the existing locked all-extras environment. Run focused CLI tests with `uv run --locked pytest --no-cov`, then the exact guide smoke in a fresh synthetic workspace with original-file hashes checked before/after. Run required Ruff, format, mypy, full pytest/coverage, repository/maintainability/CI audits and `uv build`.

Review protocol/templates without fabricating data: every decision gate must map to fields; all initial statuses must remain pending. Check zero diffs in `benchmarks`, `corpora`, `schemas`, `uv.lock` and `pyproject.toml`. Real tasks and measured benefit remain pending until supplied and independently reviewed.
