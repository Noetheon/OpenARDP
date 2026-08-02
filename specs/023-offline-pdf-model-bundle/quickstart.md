# Quickstart: Validate Offline PDF Model Readiness

Run from the repository root with Python 3.12 and the locked project environment. The connected step is explicit; every
later command must work after network access is removed.

## 1. Synchronize and run fixture gates

```bash
uv sync --locked --all-extras
uv run pytest --no-cov \
  tests/contract/test_pdf_bundle_contract.py \
  tests/unit/test_docling_bundle.py \
  tests/security/test_pdf_bundle_boundaries.py \
  tests/integration/test_pdf_bundle_lifecycle.py
```

Expected: miniature synthetic bundles cover exact success, atomic failure, hostile trees/archives and deterministic
package reproduction without network access.

## 2. Provision once while connected

```bash
uv run --locked --extra docling python scripts/provision_pdf_bundle.py \
  --source-lock model-bundles/pdf-docling-2.114.0-v1/source-lock.json \
  --destination /path/to/fresh/docling-pdf-bundle
```

Expected: five exact model files plus fixed control/license material are atomically published. The JSON result contains no
absolute path or remote response body.

## 3. Package and install into a fresh offline root

```bash
uv run --locked python scripts/verify_pdf_bundle.py \
  --source-lock model-bundles/pdf-docling-2.114.0-v1/source-lock.json \
  --bundle /path/to/fresh/docling-pdf-bundle
uv run --locked python scripts/package_pdf_bundle.py \
  --source-lock model-bundles/pdf-docling-2.114.0-v1/source-lock.json \
  --bundle /path/to/fresh/docling-pdf-bundle \
  --output /path/to/fresh/docling-pdf-bundle.zip
uv run --locked python scripts/install_pdf_bundle.py \
  --source-lock model-bundles/pdf-docling-2.114.0-v1/source-lock.json \
  --package /path/to/fresh/docling-pdf-bundle.zip \
  --destination /path/to/fresh/offline-install
```

Expected: repeated package creation from identical input has the same SHA-256; fresh install has the same source-lock and
bundle IDs and needs no provider cache.

## 4. Prove real PDF conversion and measure it

Disconnect network access or run under the benchmark's socket-denied child process with provider caches redirected to
fresh empty directories:

```bash
uv run --locked --extra docling python scripts/run_pdf_bundle_benchmark.py \
  --bundle /path/to/fresh/offline-install \
  --package /path/to/fresh/docling-pdf-bundle.zip \
  --provision-duration-ns DURATION_FROM_PROVISION_RESULT \
  --output /path/to/fresh/pdf-bundle-result
uv run --locked python scripts/validate_pdf_bundle_benchmark.py \
  --result /path/to/fresh/pdf-bundle-result
```

Expected: the producer and independent validator agree on `PDF_OFFLINE_READY` or honestly retain
`PDF_OFFLINE_NOT_READY`. Read the generated report for exact size, time, memory and limitations; do not infer F024/F025
real-world or semantic quality.

## 5. Full repository gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run python scripts/validate_repository.py
uv build
uv run pre-commit run --all-files
```

Expected: all ordinary gates remain network-free and do not download heavyweight model files.
