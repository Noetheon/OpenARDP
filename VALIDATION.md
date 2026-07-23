# Validation status

This file separates locally observed evidence from externally observed automation. Feature-specific acceptance evidence
is recorded in the [feature 001 notes](specs/001-repository-baseline/implementation-notes.md),
[feature 002 notes](specs/002-domain-models-schemas/implementation-notes.md) and
[feature 003 notes](specs/003-cas-sqlite-catalog/implementation-notes.md) and
[feature 004 notes](specs/004-text-ingestion-slice/implementation-notes.md) and
[feature 005 notes](specs/005-lexical-search/implementation-notes.md).

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

## Feature 003 external verification completed

[Pull request #3](https://github.com/Noetheon/OpenARDP/pull/3) merged F003 as commit
[`65ff681984b844cc647b9c4221f435606be72a25`](https://github.com/Noetheon/OpenARDP/commit/65ff681984b844cc647b9c4221f435606be72a25).
The final PR-head workflow [29938693336](https://github.com/Noetheon/OpenARDP/actions/runs/29938693336) and the
post-merge `main` workflow [29938831432](https://github.com/Noetheon/OpenARDP/actions/runs/29938831432) both completed
successfully on Ubuntu, macOS and Windows. They repeated the locked environment setup, Ruff, formatting, strict mypy,
the 284-test network-blocked suite, distribution builds and tracked-file drift verification.

This closes F003's local filesystem CAS, transactional SQLite catalog, durable job/recovery and read-only reachability
boundary. It does not validate parsers, complete document representations, retrieval or automatic deletion; those
remain later bounded work packages.

## Feature 004 local evidence

Feature `004-text-ingestion-slice` implements the bounded local TXT/Markdown workflow without adding search, chunking,
embedding, rich formats or MCP. The locally observed complete gate on macOS/Python 3.12 passed 389 offline tests with
87.20 percent branch-aware coverage against the enforced 85 percent threshold. Ruff, formatting and strict mypy
(native and Windows platform) also passed across the complete repository.

Focused evidence covers incremental strict UTF-8 and Markdown normalization, spawned-worker timeout/crash cleanup and
socket denial, atomic workspace markers, no-follow regular source snapshots, source-race detection, checksummed catalog
revision 3, fenced representation retries, six atomic READY rollback points, sequential and concurrent verified cache
hits, A → B → A head selection, full CAS/semantic integrity checks, progressive outline reads, source removal and all six
human/JSON CLI commands through the installed entry point. Spec Kit convergence also closed an empty-blockquote edge case
with a bounded warning. Original source bytes, size, modification time and mode remained unchanged on the tested paths;
access time is intentionally not claimed.

The first pull request matrix stopped macOS on a real F003 CAS publication race. Publication is now no-clobber on both
platforms (POSIX hard link plus staging unlink, Windows `os.rename`) with a bounded settling re-check for the transient
internal second link; eighty loaded repetitions of the store suite passed on the final tree. The feature 004 notes carry
the mechanism and evidence details.

Cross-platform PR-head, merge and post-merge evidence is recorded in the closure section below and in the feature 004
notes.

## Feature 004 external verification completed

[Pull request #4](https://github.com/Noetheon/OpenARDP/pull/4) merged F004 as commit
[`e30b293f51fb57e250351dd39f35763af820449e`](https://github.com/Noetheon/OpenARDP/commit/e30b293f51fb57e250351dd39f35763af820449e).
The final PR-head workflow [29961130435](https://github.com/Noetheon/OpenARDP/actions/runs/29961130435) and the
post-merge `main` workflow [29961311398](https://github.com/Noetheon/OpenARDP/actions/runs/29961311398) both completed
successfully on Ubuntu, macOS and Windows. They repeated the locked environment setup, Ruff, formatting, strict mypy,
the 389-test network-blocked suite, distribution builds and tracked-file drift verification.

The superseded PR-head run [29960461367](https://github.com/Noetheon/OpenARDP/actions/runs/29960461367) remains
intentionally visible: it exposed that Windows `DirEntry.stat` caches directory data without a file index, so the
staged-twin scan now requests complete identities explicitly, and both later Windows jobs passed. This closes the
cross-platform execution and final Spec Kit convergence boundary for feature 004.

## Feature 005 local evidence

Feature `005-lexical-search` adds exact source-backed lexical retrieval through a checksummed catalog revision 4
(contentless-delete FTS5 plus a STRICT mapping table) without adding embeddings, fuzzy matching, watchers, MCP, HTTP
or any new runtime dependency. The locally observed complete gate on macOS/Python 3.12 passed 407 offline tests with
86.45 percent branch-aware coverage against the enforced 85 percent threshold. Ruff, formatting and strict mypy
(native and Windows platform), pre-commit, the offline repository validator and the distribution builds plus isolated
wheel import also passed.

Focused evidence covers the bounded term/phrase grammar with operator lookalikes as literal text, atomic READY+index
commits with fault-injection rollback, fail-closed structural coverage (`SearchIndexIncomplete`), serve-time hash
guards (`SearchIndexDrifted`), verified CAS snippets with bounded escaped rendering, deterministic bm25 ordering with
a total tie-break, the explicit idempotent `reindex` backfill with byte-identical evidence, all filters including the
stable page/slide contract, and both CLI verbs in human and JSON modes through the installed entry point. The complete
Spec Kit lifecycle converged with zero findings; the feature 005 notes carry the full evidence table and the five
quickstart scenarios.

## Feature 005 external verification completed

[Pull request #5](https://github.com/Noetheon/OpenARDP/pull/5) merged F005 as commit
[`26947ad2ebdf4a2c90a2726838b870aa3fb564a8`](https://github.com/Noetheon/OpenARDP/commit/26947ad2ebdf4a2c90a2726838b870aa3fb564a8).
The final PR-head workflow [30050801259](https://github.com/Noetheon/OpenARDP/actions/runs/30050801259) and the
post-merge `main` workflow [30050939386](https://github.com/Noetheon/OpenARDP/actions/runs/30050939386) both completed
successfully on Ubuntu, macOS and Windows. They repeated the locked environment setup, Ruff, formatting, strict mypy,
the 407-test network-blocked suite, distribution builds and tracked-file drift verification. This closes the
cross-platform execution and final Spec Kit convergence boundary for feature 005.

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
local engineering gates is evidence that the product is production-ready; search, rich-format ingestion, broader security
hardening, enterprise connectors and release operations remain later work packages.
