# Implementation Notes: Repository Baseline

**Feature**: `001-repository-baseline`

**Started**: 2026-07-22

**Status**: Converged

## Acceptance criteria reconciliation

This matrix restates the active work-package contract, as required by `AGENTS.md`, and ties each outcome to observed or
inspectable evidence. Local contract checks and externally observed runner evidence remain distinguished explicitly.

| ID | Acceptance criterion | Evidence | Status |
|---|---|---|---|
| FR-001 | Python is limited to the 3.12 series and uv is the environment manager. | `.python-version`, project metadata, contract test | Pass |
| FR-002 | A committed lock covers the package and mandatory development tools. | `uv.lock`; 31-package lock check | Pass |
| FR-003 | Locked sync rejects missing/stale lock state and does not mutate a current lock. | Repeated sync plus both disposable negative probes | Pass |
| FR-004 | Version and five architecture namespaces import. | Package tests and wheel smoke import | Pass |
| FR-005 | No later document-product behavior is present. | Forbidden-module and entry-point tests | Pass |
| FR-006 | Lint, format, strict typing and tests are authoritative failing gates. | Four successful gates plus negative probes | Pass |
| FR-007 | Pytest enforces no network, branch coverage and at least 85 percent. | Required-plugin/config tests; 100 percent observed coverage; socket probe | Pass |
| FR-008 | Public baseline contracts are typed, documented and tested. | Ruff docstring rules, strict mypy and package tests | Pass |
| FR-009 | Commit-time hooks run all mandatory gate families from the lock. | Local-hook parity tests, config validation, all-files execution | Pass |
| FR-010 | CI declares Linux/macOS/Windows, Python 3.12 and the local gate set. | Workflow contract tests | Pass |
| FR-011 | CI is read-only, does not persist credentials and uses immutable actions. | Workflow tests and release-tag SHA verification | Pass |
| FR-012 | Tests/docs use redistributable fixtures and no network. | Synthetic temporary fixtures; offline/no-sync suite | Pass |
| FR-013 | Local Markdown paths/headings are validated safely and offline. | 18 focused positive/negative validator tests plus whole-repository run | Pass |
| FR-014 | License, Python, uv and quality commands agree across artifacts. | Governance validator and repository contract tests | Pass |
| FR-015 | Entry, license, contribution, security, validation and changelog docs are coherent. | Required-file and discoverability tests | Pass |
| FR-016 | Ignore rules cover environments, caches, coverage, OS state and secrets. | `.gitignore` contract test | Pass |
| FR-017 | Decisions, commands, results, trade-offs and risks are recorded here. | This implementation record | Pass |
| FR-018 | Baseline adds no runtime dependency, provider or future abstraction. | Empty runtime dependency set and source-boundary tests | Pass |
| SC-001 | A clean checkout is reproducible on Linux, macOS and Windows. | GitHub Actions run `29926478593`: Ubuntu, macOS and Windows jobs passed every workflow step | Pass |
| SC-002 | A repeated locked sync/gate run creates no unintended tracked change. | Repeated sync and staged-diff comparison | Pass locally |
| SC-003 | Representative lint/format/type/test/coverage/network faults are rejected. | Seven disposable probes | Pass |
| SC-004 | CI has zero write permission, persisted credentials and mutable actions. | Static workflow and immutable-reference tests | Pass |
| SC-005 | Offline docs validation has zero unresolved local-target defects. | Whole-repository validator returned zero diagnostics | Pass |
| SC-006 | A first-time maintainer can find the full setup/validation sequence. | README, START_HERE and contributor-guide tests | Pass |
| SC-007 | Installed source/commands expose zero work-package 1–13 behavior. | Wheel/source and entry-point inspection | Pass |
| SC-008 | Spec, plan, tasks, code and evidence have no critical/high inconsistency. | Analyze and final convergence both returned zero actionable findings | Pass |

## Decisions implemented

1. **Infrastructure-only boundary**: only package version metadata, `py.typed` and the five architecture namespace packages
   remain. Premature hashing, chunking, domain-model and CLI behavior was deleted so later features can specify those
   contracts deliberately.
2. **One exact locked toolchain**: runtime dependencies are empty. Build and development tools resolve through `uv.lock`;
   setup, local hooks and CI all use that same environment.
3. **Locked rather than frozen synchronization**: `--locked` is used anywhere stale metadata must fail because frozen mode
   intentionally skips lock-freshness checking.
4. **Measured environment correction**: conventional `.venv` directories created by both uv 0.11.16 and 0.11.31 below
   the macOS 26.5.2 `Documents` path acquired hidden flags asynchronously, causing Python 3.12.13 to skip editable-package
   and coverage `.pth` hooks. The exactly pinned uv 0.11.31 toolchain enables only `centralized-project-envs`; the derived
   environment lives in uv's disposable cache while `.venv` is only an optional discovery symlink. This host later
   recreates an empty `.venv` directory, so uv reports a non-fatal link warning and uses the deterministic cache path
   directly. The canonical commands and visible underlying hooks remain functional through repeated sync and gate runs.
5. **Offline enforcement**: pytest-socket blocks sockets for the complete suite. A typed standard-library validator checks
   local Markdown and governance contracts without fetching external links.
6. **Least-privilege automation**: CI uses a three-OS matrix, read-only content permission, no credential persistence, no
   cache, locked sync and full-SHA action pins with release comments.
7. **Governance without readiness inflation**: Apache-2.0, contribution, security and changelog artifacts are coherent,
   while public-release clearance and unimplemented product/security capabilities remain explicit future work.

## Command evidence

All exit states are from 2026-07-22 on the local macOS environment. The final all-files evidence is populated only after
the intended feature change is staged.

| Command | Observed result |
|---|---|
| `bash scripts/bootstrap-speckit.sh` | Pass; `specify-cli==0.13.3`, Codex integration and constitution overlay verified |
| `uv --version` | Pass; `uv 0.11.31` |
| `uv lock --check` | Pass; 31 packages resolved without lock mutation |
| `uv sync --all-extras --locked` (twice after clearing the centralized environment) | Pass; 31 packages resolved, second run checked 30 installed packages without mutation |
| `uv run python -c "import openardp; print(openardp.__version__)"` | Pass; printed `0.0.1` after each synchronization |
| `uv run ruff check .` | Pass |
| `uv run ruff format --check .` | Pass |
| `uv run mypy src` | Pass; six source files checked |
| `uv run pytest` | Pass; 41 tests, 100 percent branch coverage, 85 percent threshold enforced |
| `uv run pre-commit validate-config` | Pass |
| `uv run pre-commit run --all-files` | Pass; all four local hooks passed across the staged repository |
| `uv build` | Pass; wheel and source distribution built |
| `uv run --offline --no-sync pytest` | Pass; 41 tests, 100 percent branch coverage, no synchronization or network |
| `uv run python scripts/validate_repository.py` | Pass; zero diagnostics |
| `git ls-remote` for both reviewed action tags | Pass; both configured 40-character revisions matched their annotated release tags |
| `git diff --cached --check` | Pass; zero whitespace errors |
| Spec Kit convergence | Pass; 26 requirements/criteria, 18 acceptance cases, nine plan decisions, ten constitutional articles and 34 tasks checked with zero findings |
| `gh run watch 29926478593 --exit-status` | Pass; Ubuntu in 15 seconds, macOS in 18 seconds and Windows in 41 seconds |

The built wheel contained `openardp/__init__.py`, all five namespace packages and `py.typed`; its isolated Python 3.12
import reported version `0.0.1` and exposed no console entry point.

## Negative evidence

Each probe was intentionally isolated and its non-zero result was expected:

| Probe | Expected and observed result |
|---|---|
| Remove `uv.lock`, then run locked synchronization | Exit 2; missing lockfile rejected |
| Add an unmatched temporary dependency, then run locked synchronization | Exit 1; stale lockfile rejected |
| Send an unused import to Ruff | Exit 1; lint defect identified |
| Send unformatted source to Ruff format check | Exit 1; formatting defect identified |
| Check an incompatible annotated assignment with strict mypy | Exit 1; assignment error identified |
| Run an intentional failing pytest | Exit 1; failure reported |
| Require 100 percent coverage while executing only the validator probe | Exit 2; 66 percent measured coverage rejected |
| Construct a socket under the configured pytest runner | Socket operation blocked; negative contract test passed |

The initial test-first baseline contracts also produced 13 expected failures against the premature blueprint scaffold.
After the package-boundary implementation, only the deliberately missing license/changelog contract remained; adding the
governance artifacts brought that slice to green before later stories proceeded.

## Trade-offs and remaining risks

- The repository is private at `Noetheon/OpenARDP`, and the first full three-platform workflow run passed. GitHub limits
  repository security advisories and private vulnerability reporting to public repositories; `SECURITY.md` therefore
  keeps a no-details fallback for the private phase and requires enabling the structured channel before public release.
- Exact uv and full-SHA action pins trade automatic updates for reviewable reproducibility. They require deliberate,
  tested maintenance when upgraded.
- The centralized project-environment capability is a uv preview bounded by the exact tool pin. On this workspace, the
  file provider also prevents the optional `.venv` discovery link and causes non-fatal uv warnings; CLI resolution and
  every gate use the external cache environment successfully, but some editors may need their interpreter selected from
  the path reported by `uv run python -c "import sys; print(sys.prefix)"`.
- The offline Markdown validator intentionally skips external URL reachability. Remote content availability and semantic
  correctness are outside this deterministic unit-test contract.
- Local pre-commit hooks run the complete test suite and may become slower as the product grows. Splitting fast and full
  gates requires measured evidence in a later feature.
- Ownership, employer-IP, public naming and trademark clearance remain prerequisites for public release.
- Passing this baseline proves repository engineering controls only. It does not prove document parsing, provenance,
  storage, security isolation, retrieval quality or production readiness; those belong to later work packages.
