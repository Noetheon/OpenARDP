# Validation status

This file separates locally observed evidence from externally observed automation. Feature-specific acceptance evidence
is recorded in the [feature 001 notes](specs/001-repository-baseline/implementation-notes.md) and
[feature 002 notes](specs/002-domain-models-schemas/implementation-notes.md).

## Blueprint relocation and Spec Kit bootstrap

The extracted blueprint was first preserved in commit `6596eb6`. Its visible and hidden files were then compared
byte-for-byte with their repository-root destinations before the accidental nested directory was removed in commit
`56155e9`.

The pinned bootstrap subsequently completed on this machine:

- `specify-cli==0.13.3` installed successfully;
- `specify init --here --force --integration codex` generated the local execution layer;
- the generated constitution was byte-identical to `spec-kit/CONSTITUTION_SOURCE.md`;
- `specify integration status` reported the Codex integration as healthy;
- the reviewed bootstrap state was committed as `acf8aea`.

The earlier artifact-generation note about an HTTP 503 is historical and no longer describes this repository state.

## Feature 001 local evidence

Observed on macOS 26.5.2, Apple Silicon, with Python 3.12.13 and uv 0.11.31:

- locked synchronization completed and a second locked synchronization changed no project or lock file;
- the package and all five architectural namespaces imported;
- wheel and source distributions built, the wheel contained `py.typed`, and an isolated wheel import returned `0.0.1`;
- Ruff lint, Ruff formatting verification and strict mypy completed successfully;
- 41 tests passed with 100 percent branch coverage against an enforced 85 percent minimum;
- pytest-socket rejected socket construction and the suite passed offline with synchronization disabled;
- the offline repository validator reported zero Markdown or governance diagnostics;
- all local pre-commit hooks passed against every staged file.

The exact final commands, exit states and negative probes are listed in the feature implementation notes rather than
duplicated here.

Final Spec Kit convergence checked 26 requirements and success criteria, 18 user-story acceptance cases, nine plan
decisions, ten constitutional articles and all 34 completed tasks. It found zero missing, partial, contradictory or
unrequested implementation gaps, so no convergence tasks were appended.

## Feature 002 local evidence

Feature `002-domain-models-schemas` adds only pure domain validation and deterministic identity behavior. Its acceptance
evidence covers five root models, five Draft 2020-12 schemas, five synthetic golden records, an independent
canonicalization-vector file, strict raw-JSON rejection and 20 fresh-process determinism executions. The executable
contracts remain free of filesystem, database, parser, retrieval, provider and interface I/O.

The final local repository gate passed 186 tests with 100 percent statement and branch coverage; two consecutive schema
checks, Ruff, formatting, strict mypy, the offline locked suite, build and staged pre-commit checks also passed. Exact
schema hashes and Spec Kit evidence are maintained in the feature implementation notes. External Linux/macOS/Windows
evidence must still be green before this section is treated as closed.

## Feature 002 external verification completed

[Pull request #2](https://github.com/Noetheon/OpenARDP/pull/2) merged F002 as commit
[`81c1d3315c9082a4902c8ec898bfab118d530a3e`](https://github.com/Noetheon/OpenARDP/commit/81c1d3315c9082a4902c8ec898bfab118d530a3e).
The final PR-head workflow [29932307711](https://github.com/Noetheon/OpenARDP/actions/runs/29932307711) and the
post-merge `main` workflow [29932448176](https://github.com/Noetheon/OpenARDP/actions/runs/29932448176) both completed
successfully on Ubuntu, macOS and Windows. Each job performed locked synchronization, lint, formatting, strict mypy,
the 186-test network-blocked suite, distribution builds and tracked-file drift verification.

The earlier PR run [29931948083](https://github.com/Noetheon/OpenARDP/actions/runs/29931948083) remains intentionally
visible: it exposed Windows CRLF checkout and implicit CP1252 decoding assumptions. The repository now enforces LF for
reviewed text contracts and explicit UTF-8 for the Unicode vector, and both later Windows jobs passed. This closes the
cross-platform execution and final Spec Kit convergence boundary for feature 002.

## Corrective environment verification

On the current macOS/Python combination, a conventional `.venv` below `Documents` was asynchronously marked hidden
together with its `.pth` files; Python skipped those files, breaking the editable-package import and coverage hooks. The
failure reproduced with uv 0.11.16 and 0.11.31, which ruled out a version-only explanation.

The exact uv 0.11.31 pin now bounds the single enabled `centralized-project-envs` preview contract. uv stores the derived
environment in its disposable cache and attempts to keep `.venv` as the standard discovery symlink. This workspace's file
provider later recreates an empty `.venv` directory, so uv emits a non-fatal link warning and resolves its deterministic
cached environment directly. A cleared environment, repeated locked synchronization, all mandatory commands and package
import preserved visible underlying `.pth` files and passed. This is a measured correction for the observed workspace,
not a general claim about macOS, Python or uv.

## Negative-gate evidence

Disposable probes confirmed that the baseline rejects:

- missing and stale lock state;
- representative lint and formatting defects;
- an incompatible assignment under strict mypy;
- an intentional failing test;
- coverage below the configured threshold;
- socket access during the unit suite.

All disposable probe files were outside the repository or removed after the check.

## External verification completed

The repository is hosted privately at [Noetheon/OpenARDP](https://github.com/Noetheon/OpenARDP). GitHub Actions run
[`29926478593`](https://github.com/Noetheon/OpenARDP/actions/runs/29926478593) executed against commit
`4126188aa2289803e6e464f8d262bc4558381ab3` and completed successfully on all declared runners:

- Ubuntu: every locked-sync, quality, test, build and no-diff step passed in 15 seconds;
- macOS: every step passed in 18 seconds;
- Windows: every step passed in 41 seconds.

This closes the cross-platform execution boundary for feature 001. The local `main`, `origin/main` and workflow head SHA
were verified as identical before the evidence update.

GitHub documents repository security advisories and private vulnerability reporting for public repositories. Because
OpenARDP remains private, `SECURITY.md` provides a metadata-only fallback that never asks a reporter to disclose exploit
details publicly. The structured GitHub channel must be enabled when the repository becomes public.

## Remaining release-governance checks

PowerShell bootstrap parser execution was not repeated locally because `pwsh` is not installed. The Windows feature-001
workflow passed, but it does not invoke the preserved bootstrap script; feature 001 does not modify that script's behavior.

Ownership, employer-IP, public-name and trademark clearance also remain release-governance requirements. None of the
local engineering gates is evidence that the product is production-ready; document ingestion and every product security
boundary belong to later work packages.
