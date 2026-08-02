# Maintainer Contract: Offline PDF Bundle

## Explicit connected provisioning

```text
uv run --locked --extra docling python scripts/provision_pdf_bundle.py \
  --source-lock model-bundles/pdf-docling-2.114.0-v1/source-lock.json \
  --destination ABSENT_INSTALL_ROOT
```

- This is the only connected operation in F023 and requires an absent destination.
- It accepts only the committed host/repository/revision/path allowlist and never tokens on the command line.
- Success prints one body-free canonical JSON envelope with source-lock ID, bundle ID, file/byte counts and measured
  duration; identities/counts are reproducible while duration is observational.
- Failure is nonzero with a stable category; no raw network/provider exception or absolute path is returned.
- Ordinary import, validation, package creation, installation and PDF conversion never call provisioning.

## Offline installation verification

```text
uv run --locked python scripts/verify_pdf_bundle.py \
  --source-lock model-bundles/pdf-docling-2.114.0-v1/source-lock.json --bundle INSTALL_ROOT
```

Verification validates fixed control files, exact license text digests and the closed runtime tree. Missing/extra files,
links, devices, path/case/normalization collisions, size/digest drift or source-lock/manifest mismatch fail before provider
import. Success returns the existing model bundle ID plus counts; it does not mutate the installation.

## Deterministic package and safe install

```text
uv run --locked python scripts/package_pdf_bundle.py \
  --source-lock model-bundles/pdf-docling-2.114.0-v1/source-lock.json \
  --bundle INSTALL_ROOT --output ABSENT_PACKAGE.zip
uv run --locked python scripts/install_pdf_bundle.py \
  --source-lock model-bundles/pdf-docling-2.114.0-v1/source-lock.json \
  --package PACKAGE.zip --destination ABSENT_INSTALL_ROOT
```

Package creation first verifies the installation, writes a sibling temporary file and replaces only an absent output.
Safe install reads bounded central-directory metadata, rejects the complete hostile-member set, streams into a disjoint
staging tree, verifies every extracted byte and atomically publishes only a complete installation.

## Parser use

```text
openardp ingest SOURCE.pdf --store WORKSPACE \
  --docling-model-root INSTALL_ROOT/assets \
  --docling-model-manifest INSTALL_ROOT/manifest.json
```

The parser verifies the exact closed `assets/` tree before provider import. It ignores global caches as authority and
retains the existing CPU/one-thread/offline/disabled-enrichment profile and worker limits.

## Benchmark contract

```text
uv run --locked --extra docling python scripts/run_pdf_bundle_benchmark.py \
  --bundle INSTALL_ROOT --package PACKAGE.zip \
  --provision-duration-ns DURATION_FROM_PROVISION_RESULT --output FRESH_RESULT
uv run --locked python scripts/validate_pdf_bundle_benchmark.py --result FRESH_RESULT
```

Producer output is exactly `decision.json`, `observations.json`, `report.md`, `run-manifest.json` and `summary.json`.
Absolute paths, source/model bodies, task text, usernames, hostnames, credentials, cache contents and raw exceptions are
prohibited. The validator rejects extra/missing files, noncanonical JSON, identity or arithmetic drift, missing observation
groups, report mismatch, network attempts, nondeterminism and any unjustified ready decision.
