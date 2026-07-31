# Validation status

This file separates locally observed evidence from externally observed automation. Feature-specific acceptance evidence
is recorded in the [feature 001 notes](specs/001-repository-baseline/implementation-notes.md),
[feature 002 notes](specs/002-domain-models-schemas/implementation-notes.md) and
[feature 003 notes](specs/003-cas-sqlite-catalog/implementation-notes.md) and
[feature 004 notes](specs/004-text-ingestion-slice/implementation-notes.md) and
[feature 005 notes](specs/005-lexical-search/implementation-notes.md) and
[feature 005A notes](specs/005A-strategic-realignment/implementation-notes.md) and
[feature 006 notes](specs/006-evidence-contract-foundation/implementation-notes.md) and
[feature 007 notes](specs/007-docling-native-adapter/implementation-notes.md),
[feature 008 notes](specs/008-context-compiler-receipts/implementation-notes.md) and
[feature 009 notes](specs/009-read-only-mcp/implementation-notes.md) and
[feature 010 notes](specs/010-reconciliation-derivation-dag/implementation-notes.md).

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

## Feature 005A local evidence

Feature `005A-strategic-realignment` changes documentation, governance, decision records, feature prompts, repository
validation and experimental examples only. The path-scoped diff against the merged F005 base is empty for `src/`,
`schemas/`, `pyproject.toml` and `uv.lock`.

The local locked gate passes 415 offline tests with 86.45 percent branch-aware coverage. Ruff, formatting, strict mypy on
native and Windows targets, staged pre-commit hooks, the repository validator, source/wheel builds, an isolated offline
wheel import, JSON validation, relative links, migration accounting and the Feature 005A quickstart all pass.

Constitution 2.0.0 is byte-identical to its canonical source. Repository-contract tests enforce the exact 005A–017 prompt
sequence, ADR supersession/deferral, experimental contract maturity, claim discipline, overlay completeness and exclusion
of the external blueprint package.

## Feature 005A external verification completed

[Pull request #6](https://github.com/Noetheon/OpenARDP/pull/6) merged F005A as commit
[`75defaba24a64ab79772683d643378305e8d776f`](https://github.com/Noetheon/OpenARDP/commit/75defaba24a64ab79772683d643378305e8d776f).
The PR-head workflow [30201594632](https://github.com/Noetheon/OpenARDP/actions/runs/30201594632) and post-merge `main`
workflow [30201693013](https://github.com/Noetheon/OpenARDP/actions/runs/30201693013) both passed on Ubuntu, macOS and
Windows. Every job performed locked synchronization, lint, formatting, strict mypy, the 415-test network-blocked suite,
distribution builds and tracked-file drift verification.

This closes the v3.1 strategic realignment and contract boundary without changing runtime behavior, public-schema
semantics, dependencies, the lockfile, persisted identities or commands.

## Feature 006 verified evidence

Feature `006-evidence-contract-foundation` adds four independently versioned
experimental roots without a rich parser, catalog migration, new dependency, network
behavior, or change to the five F002/F005 schemas. The roots cover retained native
artifacts, source-bound evidence references, thin retrieval projections, and
anti-escalation trust classifications.

The local macOS/Python 3.12 locked gate passes 476 offline tests with 86.71 percent
branch-aware coverage. Ruff, formatting, strict mypy on native and Windows targets,
deterministic generation of all nine schemas, the adapter-independent conformance
validator, repository validation, source/wheel builds, and an isolated offline wheel
import pass. The public corpus contains seven valid fixtures, eight invalid fixtures,
one coherent cross-record set, and six exact RFC 8785 canonical/digest vectors.

A path-scoped diff against F005A commit
`39e7f8313bdb433f3057c3ad5ebf1b141e1ee2c4` is empty for the five existing schemas,
their canonicalization vectors, `pyproject.toml`, and `uv.lock`. PR
[#8](https://github.com/Noetheon/OpenARDP/pull/8) merged feature commit
`2d746bea859aa399f23d3e88c55540205c8784cc` as
`0162bd839c0cd67c66201efcbfd9610ab5899d5c`. PR-head workflow
[30203968571](https://github.com/Noetheon/OpenARDP/actions/runs/30203968571) and
post-merge `main` workflow
[30204051975](https://github.com/Noetheon/OpenARDP/actions/runs/30204051975) both
passed the complete locked gate on Linux, macOS, and Windows.

## Feature 007 local evidence

Feature `007-docling-native-adapter` adds one exact optional provider dependency and
checksummed SQLite migration 5 without changing the nine public F002/F006 schemas or
their identity vectors. Locally observed macOS/Python 3.12 evidence covers actual
Docling 2.114.0 DOCX/PPTX conversions, deterministic fixtures, the PDF missing-assets
gate, bounded worker termination, network denial, complete native/F006 construction,
atomic rich persistence, ten-repeat verified cache reuse, forced convergence/divergence,
all rich object tamper classes and provider-free CLI inspection.

The closing local gate passed 566 tests at 85.36% branch coverage. Ruff, formatting,
strict native and Windows-target mypy over 38 source files, all nine generated schemas,
the F006 conformance corpus, repository validation, `git diff --check`, source/wheel
builds, and core/rich isolated-wheel probes passed. Byte comparison to the frozen base
found no change in the nine public schema JSON files, either identity-vector file, or
the F006 conformance corpus. Exact commands and packaging/quickstart evidence are in the
feature notes. Pull request [#10](https://github.com/Noetheon/OpenARDP/pull/10) merged
as `1a080d37efcc2f74307bb01a6656db09659e9138`. PR-head workflow
[30208533025](https://github.com/Noetheon/OpenARDP/actions/runs/30208533025) and
post-merge `main` workflow
[30208840651](https://github.com/Noetheon/OpenARDP/actions/runs/30208840651) both
passed the complete locked gate on Linux, macOS, and Windows.

## Feature 008 local evidence

Feature `008-context-compiler-receipts` adds the deterministic provider-free context
compiler, the public `ContextBundle 0.2.0`, the experimental `SelectionReceipt 0.1.0`
and checksummed SQLite migration 6 without changing the nine earlier public schemas
or their identity vectors. Locally observed macOS/Python 3.12 evidence covers verified
lexical discovery over text and rich evidence, byte-exact fixed-point budgeting,
20-repeat byte-identical compilation, atomic compilation persistence, five-repeat and
head-change-pinned replay, the complete hostile-path matrix (index, CAS, catalog,
limits, cancellation, publish/commit faults), body-free receipts/logs/CLI envelopes,
and the stable `context`/`context-receipt` JSON and human contracts.

The closing local gate passed 696 tests at 85.92% total coverage (85% branch gate).
Ruff, formatting, strict native and Windows-target mypy over 43 source files, all
eleven generated schemas, the F006 conformance corpus, repository validation,
`git diff --check`, source/wheel builds, and core/rich isolated-wheel probes passed —
the core wheel (seven packages, no `docling`) executed the full compile/receipt/replay
CLI workflow. Byte comparison to the F007 base found no change in the nine earlier
public schema JSON files, either identity-vector file, or the F006 conformance corpus.
Exact commands, hashes, packaging and quickstart evidence are in the feature notes.

GitHub Actions minutes were exhausted for this feature, so no remote three-platform
workflow ran; the locked local gate above replaces it and the merge is performed
locally onto `main`. The `win32` strict mypy gate and portable test design provide
the cross-platform code evidence. If remote capacity returns, the standard quality
workflow should be re-run against the merge commit and this record updated.

## Feature 009 local evidence

Feature `009-read-only-mcp` adds a dependency-free, local stdio interface over the
existing verified application services. Its experimental `MCP interface 0.1.0` fixes
protocol revision `2025-06-18`, nine identifier-scoped tools, canonical descriptors and
a versioned sanitized error taxonomy. It adds no dependency, public JSON Schema,
identity-vector revision or workspace migration.

Locally observed evidence covers exact initialize/discovery/EOF transcripts,
20-repeat navigation determinism, search and compiler parity, full receipt
verification, bounded opt-in bundle delivery, cancellation and deadline propagation,
malformed/oversize/batch recovery, uniform identifier failures, injected catalog/CAS/
index drift, every published resource cap, privacy scans and byte-for-byte non-mutating
startup failures. The server opens no listener, accepts no client source path and never
constructs ingestion, reindex or provider services. Exact final gate counts, frozen
hashes, isolated-wheel probes and external workflow references are maintained in the
feature notes.

## Feature 009 external verification completed

[Pull request #12](https://github.com/Noetheon/OpenARDP/pull/12) merged F009 as
[`ca0a20d40b8f28d986e7af77e2c0ceefcee24997`](https://github.com/Noetheon/OpenARDP/commit/ca0a20d40b8f28d986e7af77e2c0ceefcee24997).
The PR-head workflow
[30649553804](https://github.com/Noetheon/OpenARDP/actions/runs/30649553804) and
post-merge `main` workflow
[30650000034](https://github.com/Noetheon/OpenARDP/actions/runs/30650000034) both
passed the complete locked gate on Ubuntu, macOS and Windows. Every job ran Ruff,
formatting, strict mypy, all 843 network-blocked tests, distribution builds and
tracked-file drift verification. This closes F009's cross-platform publication and
final Spec Kit convergence boundary.

## Feature 010 local evidence

Feature `010-reconciliation-derivation-dag` adds no public schema, dependency, network
operation, model execution, watcher or MCP mutation. It introduces four additive
RFC 8785/SHA-256 identity domains, conservative F002 block reconciliation, checksummed
workspace revision 7 and an internal exact derivation lifecycle over unchanged F002
generation records.

The locally observed full network-blocked suite passed all 919 tests with 86.87 percent branch-aware
coverage against the 85 percent gate. Focused evidence includes a reviewed 130-decision
corpus with zero false reuse, precision 1.000 and recall 1.000; 20 fresh-process
identity checks; real populated revision-6→7 preservation; failed and concurrent
migration behavior; all-or-none run/lineage/relation and slot/node/edge/event fault
points; four-writer convergence; cycle and dependency rejection; exact transitive
invalidation; fixed-point A→B→A reactivation; and relation, record and output
reachability/integrity failure reporting.

Ruff, formatting and strict mypy over 49 source files pass. The eleven public schemas,
prior identity vectors, F006 conformance corpus, F009 MCP descriptor fixtures,
`pyproject.toml` and `uv.lock` remain unchanged. Remote PR-head and post-merge
Linux/macOS/Windows evidence is still pending and must be recorded before F010 is
described as remotely converged.

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
