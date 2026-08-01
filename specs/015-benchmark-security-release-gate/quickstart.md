# Quickstart: Benchmark, Security and v0.1 Release Gate

## 1. Validate the frozen corpus and focused implementation

```bash
uv sync --all-extras --locked
uv run python scripts/generate_release_corpus.py --check
uv run pytest --no-cov \
  tests/domain/test_release.py \
  tests/contract/test_release_schema.py \
  tests/integration/test_release_benchmarks.py \
  tests/security/test_release_boundaries.py \
  tests/test_release_evidence_drift.py
```

All fixtures are synthetic/redistributable and unit/integration tests block network access.

## 2. Generate one local platform bundle

```bash
uv run openardp release-evidence \
  --corpus benchmarks/release/v0.1.0 \
  --output /tmp/openardp-release-evidence \
  --source-root . \
  --json
```

Use `--reference-timing` only on the documented idle reference environment. Shared CI bundles
remain valid semantic/security/install evidence but cannot satisfy the timing gate.

## 3. Evaluate without forcing a favorable result

```bash
uv run openardp release-gate \
  --policy benchmarks/release/v0.1.0/gate-policy.json \
  --evidence /tmp/openardp-linux-evidence \
  --evidence /tmp/openardp-macos-evidence \
  --evidence /tmp/openardp-windows-evidence \
  --output /tmp/openardp-release-decision \
  --decision-at 2026-08-01T00:00:00Z \
  --json

uv run openardp release-report \
  --decision /tmp/openardp-release-decision/decision.json \
  --output /tmp/openardp-release-decision \
  --check --json
```

`NO-GO` is a valid evaluated decision, not a command failure. Missing platforms, baselines,
security controls, current dependency review or operational value must produce `NO-GO`.

## 4. Validate committed release evidence

```bash
uv run python scripts/generate_release_evidence.py --check
uv run python scripts/validate_release_evidence.py release/evidence/v0.1.0
uv run openardp release-report \
  --decision release/evidence/v0.1.0/decision.json \
  --output release/evidence/v0.1.0 --check --json
```

The human report and claim map are generated projections of the machine decision. Do not edit
them manually.

## 5. Full quality gate

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv build
uv run python scripts/generate_schemas.py --check
uv run python scripts/generate_release_corpus.py --check
uv run python scripts/generate_release_evidence.py --check
uv run python scripts/validate_release_evidence.py release/evidence/v0.1.0
uv run python scripts/validate_repository.py
```

Linux, macOS and Windows PR CI and post-merge `main` CI must agree before Feature 016 begins.
