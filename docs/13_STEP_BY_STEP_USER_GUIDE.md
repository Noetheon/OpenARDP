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

## 3. Select and classify one bounded change

Use [`spec-kit/FEATURE_MAP.md`](../spec-kit/FEATURE_MAP.md) for roadmap work and classify the change as routine, standard
or high assurance using the constitution. Routine changes do not create feature directories. Standard changes retain a
specification and implementation notes. High-assurance changes use the full lifecycle below.

## 4. Complete high-assurance planning when required

```text
$speckit-specify
$speckit-clarify
$speckit-plan
$speckit-checklist
$speckit-tasks
$speckit-analyze
```

Correct contradictions in the highest-level originating artifact. Do not start high-assurance implementation while a
critical/high finding remains. The full lifecycle is optional for standard changes and unnecessary for routine changes.

## 5. Implement test-first

For high-assurance work, use `$speckit-implement` for the active phase. For every tier, add failing deterministic offline
tests before changed behavior or contracts where practical. Preserve original source bytes, provider-native artifacts,
evidence provenance, local-first defaults and provider boundaries.

## 6. Validate and converge

Run the applicable locked gate, repository validator and build. High-assurance work then runs `$speckit-converge`; append
missing tasks and implement them until no critical/high finding remains. Compact temporary planning artifacts only after
their durable content and references have been migrated.

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
services) delivers a local stdio server with nine fixed identifier-scoped tools. Start
it only against an existing compatible workspace:

```bash
uv run --locked openardp mcp --store .openardp
```

Configure an MCP client to launch that command and pass the absolute workspace path as
the `--store` argument. The client then performs `initialize` with protocol revision
`2025-06-18`, sends `notifications/initialized`, and discovers the fixed surface with
`tools/list`. The server has no network listener and client tool arguments cannot
contain source paths or URLs.

The default inbound-frame, pending-frame, response and deadline bounds are 64 KiB, 64,
1 MiB and 30 seconds. `--response-cap-bytes` accepts 65,536 through 4,194,304 and `--deadline-ms`
accepts 1,000 through 120,000. Body-bearing results are explicitly marked untrusted;
errors and audit records omit bodies, queries, tasks and paths. Features 010–013 add
reconciliation/derivation lifecycle, visual escalation, local watching/jobs and explicit
retention/recovery.

Feature 014 adds an experimental BagIt profile. Build an export request containing the
closed portable package record plus a local `asset_sources` mapping, then run:

```bash
uv run openardp package-export --request REQUEST.json --destination PACKAGE.zip --json
uv run openardp package-verify --package PACKAGE.zip --json
uv run openardp package-import --package PACKAGE.zip \
  --destination FRESH_SNAPSHOT --json
uv run python scripts/generate_interchange_vectors.py --check
```

Only explicitly permitted synthetic or redistributable assets should be included. The
snapshot is not a live workspace, integrity is not authenticity/license verification,
and no package command fetches references or accepts document-driven execution.

Feature 015 adds the local release-evidence workflow:

```bash
uv run python scripts/generate_release_corpus.py --check
uv run python scripts/run_release_security_controls.py \
  --controls benchmarks/release/v0.1.0/security-controls.json \
  --junit /tmp/openardp-security-junit.xml
uv build
uv venv /tmp/openardp-release-venv --python 3.12
uv pip install --python /tmp/openardp-release-venv --offline \
  dist/openardp-0.1.0rc1-py3-none-any.whl
uv run python scripts/generate_ci_suite_results.py \
  --output /tmp/openardp-suite-results.json \
  --junit /tmp/openardp-security-junit.xml \
  --artifacts dist --install-environment /tmp/openardp-release-venv
uv run openardp release-evidence \
  --corpus benchmarks/release/v0.1.0 --source-root . \
  --suite-results /tmp/openardp-suite-results.json --reference-timing \
  --output /tmp/openardp-platform-evidence --json
uv run openardp release-gate \
  --policy benchmarks/release/v0.1.0/gate-policy.json \
  --evidence /tmp/openardp-platform-evidence \
  --output /tmp/openardp-decision \
  --decision-at 2026-08-01T00:00:00Z --json
uv run openardp release-report \
  --decision /tmp/openardp-decision/decision.json \
  --output /tmp/openardp-decision --json
```

Use a non-symlinked output parent. Mark `--reference-timing` on exactly one qualified
environment; ordinary platform jobs omit it. One local bundle still produces `NO-GO`
because the binding policy requires all three platforms, and current supply-chain/value
checks also fail. That result is successful evaluation, not permission to publish. Validate committed
evidence with `scripts/validate_release_evidence.py`; do not edit generated reports,
claim maps, checksums or blockers. Features 016 and 017 are the remaining design spikes.
Do not reuse the pre-v3.1 numbering.
