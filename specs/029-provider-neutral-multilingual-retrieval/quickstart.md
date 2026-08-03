# Quickstart: Provider-Neutral Multilingual Retrieval

Provision and verify the external model bundle explicitly:

```bash
uv run --extra semantic python scripts/provision_embedding_bundle.py \
  --source-lock model-bundles/multilingual-e5-small-v1/source-lock.json \
  --destination /Users/Shared/openardp-multilingual-e5-small-v1
uv run python scripts/verify_embedding_bundle.py \
  --source-lock model-bundles/multilingual-e5-small-v1/source-lock.json \
  --bundle /Users/Shared/openardp-multilingual-e5-small-v1
```

Run and independently validate the frozen comparison:

```bash
uv run --all-extras python scripts/run_provider_retrieval_benchmark.py \
  --protocol-version 0.3.0 \
  --pdf-bundle /Users/Shared/openardp-pdf-bundle-2.114.0-v1 \
  --e5-bundle /Users/Shared/openardp-multilingual-e5-small-v1 \
  --output /tmp/openardp-f029
python3 -I -S scripts/validate_provider_retrieval_benchmark.py \
  --protocol-version 0.3.0 --result /tmp/openardp-f029
```

Run repository gates:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```
