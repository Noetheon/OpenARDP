# Implementation Notes: Export and Interchange Experiment

## Authoritative input

- Prompt: `spec-kit/feature-prompts/014-export-interchange-experiment.md`
- SHA-256: `a04a8f8c74e6b15073fbbe41e0fbed4e9fb5081eb78919b702899dc47bad98bd`
- Branch: `codex/f014-export-interchange-experiment`

## Acceptance criteria restatement

1. Compare RO-Crate, OCFL, BagIt and a minimal custom archive against one evidence
   matrix; accept “no custom format”.
2. Export exact selected portable records, trust, derivations and permitted assets with
   complete versions and integrity, never secrets or absolute paths.
3. Verify hostile packages completely under explicit count/size/path/relationship bounds
   before publishing one fresh snapshot; reject traversal, collisions and digest
   conflicts without partial visibility.
4. Preserve or reject only declared JSON extensions, accept exact installed versions
   and never elevate imported content, references or license assertions to authority.
5. Commit deterministic synthetic positive/negative vectors and an offline validator
   with the same Linux/macOS/Windows outcomes.

## Scope correction from planning

The canonical product requirement calls F014 an experiment, and F013 already owns
workspace backup/recovery. Import therefore publishes a fresh, separately inspectable,
read-only package snapshot. It does not merge into the live catalog/CAS. This keeps
workspace revision 10 unchanged and avoids claiming an unimplemented cross-resource
transaction.

## Implemented decisions

- BagIt 1.0 plus experimental OpenARDP profile `0.1.0`; ordinary deterministic stored
  ZIP transport and no custom suffix.
- Closed canonical public interchange record/schema `0.1.0` with independent identity,
  versions, trust, dispositions, relationships and extension policy.
- Explicit local source mapping exists only in the trusted CLI request and is never
  serialized into package metadata or results.
- Preflight reads no member into an authoritative destination, follows no links and
  performs no network/provider/plugin operation.
- Three valid and thirty-eight invalid deterministic package vectors plus drift check.

## Validation evidence

- 2026-08-01: initial focused domain, port, adapter, service, CLI, security, schema
  and conformance suites passed before the repository-wide run.
- 2026-08-01: the first complete pytest run passed 1,248 tests and identified only
  five intentional F013 governance freezes. Those guards were advanced additively to
  include the F014 module surface, active feature, accepted ADR and frozen new schema.
- 2026-08-01: initial Spec Kit convergence checked 64 requirements/acceptance
  scenarios, plan decisions and all constitution articles. It appended T067-T072 for
  three-scope repeatability, complete hostile-vector coverage, interruption cleanup,
  conflicting concurrency, target-bound import authority and onboarding consistency.
- 2026-08-01: T067-T072 passed focused tests. The corpus now contains three valid and
  thirty-eight invalid packages (42 generated files including the manifest); runtime
  verifier, independent validator and import preflight agree on every classification.
- 2026-08-01: follow-up Spec Kit analysis mapped all 32 functional requirements, 10
  success criteria and 22 acceptance scenarios to 72 tasks with no critical, high or
  medium contradiction. Follow-up convergence found zero remaining gaps.
- 2026-08-01: final local gates passed: Ruff check; Ruff format check over 198 files;
  strict mypy over 68 source files; 1,263 offline tests; 85.80% total branch coverage
  against the 85% floor; all 13 generated schemas current; all 42 interchange vector
  files current; independent minimal-vector validation; repository validation; clean
  `git diff --check`; source distribution and wheel build; and the complete pre-commit
  suite.
- 2026-08-01: PR run `30694826490` passed macOS and Ubuntu. Windows passed 1,259
  tests with 85.18% coverage but exposed a single platform-specific vector-manifest
  drift: `Path.write_text` translated the requested LF terminator to CRLF. T073 writes
  deterministic UTF-8 bytes and asserts LF-only manifest content; no runtime package,
  verification or import behavior was implicated.

Exact final commands:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv build
uv run python scripts/generate_schemas.py --check
uv run python scripts/generate_interchange_vectors.py --check
uv run python scripts/validate_interchange_package.py \
  conformance/interchange/v0.1.0/valid/minimal.zip --json
uv run python scripts/validate_repository.py
uv run pre-commit run --all-files
git diff --check
```

## Tradeoffs and remaining risks

- The strict uncompressed ZIP profile is narrower than general BagIt and optimizes
  deterministic/safe evidence over transport size.
- Read-only filesystem permissions are defense in depth, not immutable storage against
  a privileged local operator.
- No signature/authenticity/legal-license verification or live-workspace merge exists.
- Local filesystem rename/durability is tested on CI filesystems; remote/shared mounts
  are unsupported.
- The transient import plan hashes the absolute destination plus parent device/inode so
  paths never enter output or persisted package data. It detects authority replacement
  within the supported local-filesystem model, not privileged mount-namespace changes.
