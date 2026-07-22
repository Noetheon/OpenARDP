# Phase 0 Research: Repository Baseline

## Decision 1 — Bound feature 001 to infrastructure only

**Decision**: Keep only package metadata and documented architecture namespaces. Remove `src/openardp/core.py`,
`src/openardp/domain/models.py`, `src/openardp/interfaces/cli.py` and their behavior tests.

**Rationale**: The active feature explicitly excludes document-product behavior. Hashing, canonical serialization,
chunking, domain manifest/block models and a hash CLI belong to work packages 1 and 3. Leaving them in place would bypass
their own specification, compatibility and security analysis.

**Alternatives considered**:

- Retain the scaffold as examples: rejected because installed public behavior can become an accidental contract.
- Hide the modules from tests: rejected because unvalidated code is worse than deferred code.

## Decision 2 — Use locked validation, not frozen synchronization

**Decision**: Use `uv sync --all-extras --locked` for setup/CI drift checks and require uv 0.11.31 in project
configuration.

**Rationale**: Current uv documentation distinguishes the modes: `--locked` checks that `uv.lock` matches project
metadata, while `--frozen` uses the lock without checking freshness. Feature acceptance requires stale lock state to fail.
Exact tool pinning makes this behavior reviewable and repeatable. uv 0.11.31 is the version used for the final lock and
supports the narrowly enabled `centralized-project-envs` preview feature.

The centralized environment is a measured portability correction for this workspace. A conventional `.venv` below the
macOS 26.5.2 `Documents` path was asynchronously marked hidden together with its `.pth` files; Python 3.12.13 then skipped
the editable-package and coverage hooks. The failure reproduced with uv 0.11.16 and 0.11.31, so a tool upgrade alone was
not misrepresented as the fix. With uv's project environment stored in its disposable cache and `.venv` used only as an
optional discovery symlink, the real `.pth` files remain outside that file-provider boundary. Clean sync, repeated sync,
package import and all 41 tests then pass using the unchanged canonical commands. An explicit visible environment via
`UV_PROJECT_ENVIRONMENT` was rejected because it would require undocumented per-shell state, and a macOS-only `chflags`
repair was rejected because it was non-portable and was later undone by the host file provider.

**Alternatives considered**:

- `--frozen` for drift validation: rejected because it does not detect stale dependency metadata.
- Unpinned uv: rejected because lock and project semantics can change across tool releases.
- Exported `requirements.txt`: rejected because it duplicates `uv.lock` and creates another source of truth.

## Decision 3 — Keep runtime dependencies empty

**Decision**: Remove Pydantic, Typer, platformdirs and future Docling/MCP/watcher extras from feature 001. Keep build and
development tooling only.

**Rationale**: No baseline runtime behavior needs these packages. Future features will select, constrain and test them at
the point of actual use, which reduces supply-chain and installation surface now.

**Alternatives considered**:

- Preserve future dependencies as placeholders: rejected because placeholders still download code and create maintenance
  obligations without delivering value.

## Decision 4 — Share one locked toolchain between local, pre-commit and CI

**Decision**: Define Ruff, mypy, pytest, pytest-cov, pytest-socket, jsonschema and pre-commit in the default development
group. Configure pre-commit as local hooks that invoke the locked project commands.

**Rationale**: A single resolution prevents a pre-commit environment from silently using different tool versions than
CI. The standard `dev` group remains installed for the mandatory `uv run ...` commands.

**Alternatives considered**:

- Remote pre-commit hook repositories: rejected for this feature because each adds its own revisions and environments.
- Only CI checks: rejected because contributors need the same feedback before review.

## Decision 5 — Enforce no-network unit tests at the runner boundary

**Decision**: Add pytest-socket and make `--disable-socket` part of pytest's mandatory configuration; test that a socket
constructor is rejected.

**Rationale**: A policy sentence alone cannot prevent accidental network calls. A runner-level guard is deterministic,
portable and independent of application implementation.

**Alternatives considered**:

- Rely on developer discipline: rejected because it is not enforceable.
- Monkeypatch selected HTTP clients: rejected because it misses other libraries and raw sockets.

## Decision 6 — Validate repository contracts offline

**Decision**: Add a standard-library validator plus typed pytest checks for package/version metadata, required policy files,
JSON Schema validity, local Markdown paths and anchors, architectural boundaries, absent future product surfaces, CI
permissions/action pins and pre-commit coverage.

**Rationale**: These are observable feature contracts. Keeping the validator exercised by pytest means the mandated local
and CI test command cannot omit documentation/governance validation. External links are never fetched. The validator
rejects path escape, external symlinks, absolute local paths, Windows backslashes, `file:`/`sandbox:` targets and
case-mismatched paths even on case-insensitive hosts.

**Alternatives considered**:

- A separate documentation tool not included in pytest: rejected because the required gate could silently skip it.
- Online link checking: rejected because unit tests must be offline and remote availability is nondeterministic.

## Decision 7 — Harden GitHub Actions with immutable revisions

**Decision**: Pin `actions/checkout` to `3d3c42e5aac5ba805825da76410c181273ba90b1` (`v7.0.1`) and
`astral-sh/setup-uv` to `c771a70e6277c0a99b617c7a806ffedaca235ff9` (`v9.0.0`), with release comments. Disable
credential persistence and action caching, set read-only content permissions and use locked synchronization.

**Rationale**: Full revisions prevent mutable-tag substitution, annotations preserve reviewability, and non-persistent
checkout credentials reduce the authority available to later steps. Disabling cache removes mutable cross-run state from
the first baseline; caching can be reconsidered only after a measured benefit.

**Alternatives considered**:

- Major-version tags: rejected because they are mutable.
- Installing uv with an unpinned shell download: rejected because it expands the supply-chain surface.
- Enabling cache immediately: rejected because feature 001 has no benchmark evidence that it is needed.

## Decision 8 — Make governance usable now without overstating release readiness

**Decision**: Add the full Apache-2.0 license, a changelog, executable contributor setup/gate instructions and a
private-first security-reporting process. Update validation evidence after running the feature gates.

**Rationale**: Project metadata already declares Apache-2.0 and the blueprint recommends it. The repository can be
internally coherent while continuing to state that ownership, employer-IP, public name and trademark clearance precede a
public release.

**Alternatives considered**:

- Leave the license as a recommendation only: rejected because the feature explicitly requires coherent license files and
  metadata.
- Claim production readiness: rejected because parser and product security controls are future features.

## Decision 9 — Keep generated integration reviewable but exclude local agent state

**Decision**: Retain the committed `.agents/skills/*/SKILL.md` and `.specify/` integration as reviewed project inputs. Test
that no additional tracked `.agents` state appears and continue ignoring conventional secrets and local caches.

**Rationale**: The Codex skills are required build-process inputs, not user credentials. A complete `.agents/` ignore would
remove the installed Spec Kit integration from clean clones, while an allowlisted tracked shape detects accidental state.

**Alternatives considered**:

- Ignore all of `.agents/`: rejected because clean clones would lose the required workflow skills.
- Permit arbitrary tracked agent files: rejected because generated state may contain local or sensitive information.
