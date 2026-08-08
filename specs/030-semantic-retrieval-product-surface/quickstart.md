# Quickstart: Semantic Retrieval Product Surface

Compile with the lexical default:

```bash
uv run openardp context "question" --document DOCUMENT_ID --budget 262144 --store .openardp --json
```

Compile explicitly with the verified offline semantic profile:

```bash
uv run --extra semantic openardp context "question" --document DOCUMENT_ID --budget 262144 \
  --retrieval-profile semantic \
  --semantic-bundle /Users/Shared/openardp-multilingual-e5-small-v1 \
  --semantic-source-lock model-bundles/multilingual-e5-small-v1/source-lock.json \
  --store .openardp --json
```

Start an MCP session with the capability locally authorized:

```bash
uv run --extra semantic openardp mcp --store .openardp \
  --semantic-bundle /Users/Shared/openardp-multilingual-e5-small-v1 \
  --semantic-source-lock model-bundles/multilingual-e5-small-v1/source-lock.json
```

Run and validate the frozen operational measurement:

```bash
uv run --all-extras python scripts/run_semantic_surface_benchmark.py \
  --pdf-bundle /Users/Shared/openardp-pdf-bundle-2.114.0-v1 \
  --e5-bundle /Users/Shared/openardp-multilingual-e5-small-v1 \
  --output /tmp/openardp-f030
python3 -I -S scripts/validate_semantic_surface_benchmark.py --result /tmp/openardp-f030
```

Validate every retained F029 control result without loading product/model code:

```bash
python3 -I -S scripts/validate_provider_retrieval_benchmark.py --protocol-version 0.1.0 \
  --result benchmarks/provider-retrieval/v0.1.0/results/reference-macos-arm64
python3 -I -S scripts/validate_provider_retrieval_benchmark.py --protocol-version 0.2.0 \
  --result benchmarks/provider-retrieval/v0.2.0/results/reference-macos-arm64
python3 -I -S scripts/validate_provider_retrieval_benchmark.py --protocol-version 0.3.0 \
  --result benchmarks/provider-retrieval/v0.3.0/results/reference-macos-arm64
```

Run repository gates:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run python scripts/audit_maintainability.py .
uv run python scripts/validate_repository.py .
uv run pre-commit validate-config
uv run pre-commit run --all-files
uv build
uv run python scripts/generate_dependency_review.py --check
uv run python scripts/generate_release_sbom.py --check
uv run python scripts/generate_release_evidence.py --check
```
