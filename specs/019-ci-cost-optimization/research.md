# Research: CI Cost and Latency Optimization

## Decision 1: Optimize duplication, not the final platform set

**Decision**: Keep the complete test inventory on Ubuntu, macOS and Windows for every ready code-bearing pull request.
Ubuntu alone owns branch coverage plus lint, format, strict typing, repository validation and package build. macOS and
Windows run `pytest --no-cov` so socket blocking and every test remain active without redundant instrumentation.

**Evidence**: The prior workflow ran all platform-independent work three times. Local comparison on the same checkout
measured 1,381 tests at 141.64 seconds with coverage and 93.71 seconds without it, a 33.8 percent reduction in the
test phase. Historical CI also contains both Windows-only failures and a macOS-only concurrent-CAS failure, so removing
either paid platform would weaken observed defect detection.

**Rejected alternatives**:

- Linux-only CI: cheapest, but contradicts Constitution Article XI and observed platform-specific failures.
- Small smoke suites on paid platforms: lower cost, but creates an unmeasured subset that can miss file, process and
  SQLite differences.
- Coverage on every platform: no additional coverage-policy authority and material redundant time.

## Decision 2: Use explicit Draft-to-Ready promotion

**Decision**: Draft PRs receive classification and bounded preflight. Full lanes have job-level conditions and run for a
non-draft PR; the workflow subscribes to `ready_for_review`, so promotion runs the final gate without a new commit.

**Evidence**: GitHub documents that a job skipped by a job-level condition reports success, including when required,
whereas a required workflow skipped by path/branch filtering can remain pending. Core CI therefore always starts and
uses job conditions rather than workflow path filters.

**Rejected alternatives**:

- Run the full matrix on every draft synchronization: preserves quality but does not address iterative cost.
- Workflow-level `paths-ignore`: can strand required checks in Pending.
- Commit-message skip markers: user-controlled and too easy to use on merge candidates.

## Decision 3: Classify only a narrow governance allowlist

**Decision**: A standard-library classifier returns `governance` only when every non-empty repository-relative path is
an exact reviewed root document or lies below `docs/`, `specs/` or `spec-kit/feature-prompts/`. Everything else,
including workflow, policy, dependency, executable, schema, source and test changes, returns `full`.

**Rationale**: A small positive allowlist is easier to audit and fail closed than a growing list of code patterns. Mixed,
empty, unsafe and unknown inputs are full. The classifier output contains paths/reasons only, never file bodies.

**Rejected alternatives**:

- Extension-based Markdown skipping: Markdown fixtures and policy files can affect runtime or validation.
- Large negative code allowlist: new file types silently become cheap, violating fail-closed behavior.
- Third-party path-filter action: adds supply-chain surface for a small deterministic function.

## Decision 4: Separate release evidence by authorization boundary

**Decision**: Preserve the F015 three-platform evidence matrix and aggregate gate byte-for-behavior, but run it only by
manual dispatch, `v*` tag, or non-draft PR touching reviewed release-owned inputs. Ordinary PRs and all main pushes do
not regenerate release artifacts.

**Rationale**: F015 evidence is a release/reproduction control, not a general correctness suite. Core final CI already
runs every test on all platforms. The separate trigger makes an expensive release decision deliberate and inspectable.

**Rejected alternatives**:

- Delete release CI: loses independent reproduction and aggregate evidence.
- Weekly scheduled release runs: recurring cost without a release event; manual dispatch provides freshness on demand.
- Keep release jobs in every core run: accounted for roughly 1.388 USD of the dated gross daily baseline and duplicates
  setup on unrelated changes.

## Decision 5: Cache uv artifacts, never the environment

**Decision**: Enable the existing SHA-pinned `setup-uv` cache with `uv.lock` as dependency key and finish jobs with
`uv cache prune --ci`. Every install still runs `uv sync --locked`; `.venv`, test outputs and built distributions are
not cached. The downstream release aggregator deliberately does not restore a cache: it needs only the core locked
environment, and the first remote run measured a 5 minute 27 second same-key restore wait immediately after the Linux
evidence producer versus one second for its actual locked sync.

**Evidence**: uv documents built-in setup-action caching and recommends `uv cache prune --ci` to retain useful built
wheels while removing prebuilt wheels and unpacked source distributions. A missing cache remains a normal locked sync.

**Rejected alternatives**:

- Cache `.venv`: larger, path/platform sensitive and capable of hiding install reproducibility problems.
- Unlocked dependency restore: faster only by abandoning the reviewed lock contract.
- No cache: safest but repeatedly rebuilds/downloads identical immutable inputs.

## Decision 6: Protect main only after stable checks exist

**Decision**: Merge F019 after its complete remote validation, then configure classic `main` protection with strict
status checks `Preflight`, `Quality (ubuntu-latest)`, `Quality (macos-latest)` and `Quality (windows-latest)`, required
pull requests with zero human approvals, administrator enforcement, conversation resolution, and force-push/deletion
disabled.

**Rationale**: Stable contexts must exist before they are required. Zero approvals preserves solo maintenance while PR
and automated quality remain mandatory. Strict mode requires the PR to be current with `main`.

## Observed baseline and limits

The GitHub Actions inventory for 2026-08-01 contained 34 workflow runs, 158 jobs and 939 per-job rounded minutes. Using
the dated standard runner prices Linux 0.006 USD/minute, Windows 0.010 and macOS 0.062 gives a gross modeled total of
18.630 USD: Linux 277 minutes/1.662 USD, Windows 463/4.630 and macOS 199/12.338. The repository owner's invoice view was
approximately 15 USD; included usage, billing discounts or other account adjustments explain why gross modeling is not
the invoice.

The comparable-activity target is at least 55 percent modeled gross reduction. It is supported by removing release jobs
from ordinary events, avoiding the post-merge matrix duplicate, running paid-platform tests without coverage and using
Draft-to-Ready promotion. Exact realized savings depend on PR discipline, cache hit rates, GitHub rounding and future
pricing, so completion reports a range and actual post-merge runs rather than a guaranteed bill.

## Sources reviewed

- [GitHub Actions runner pricing](https://docs.github.com/en/billing/reference/actions-runner-pricing) and per-job minute
  rounding (dated 2026-08-02 review).
- [GitHub job conditions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-jobs-with-conditions)
  and skipped-job required-check semantics (dated 2026-08-02 review).
- [GitHub protected-branch REST API](https://docs.github.com/en/rest/branches/branch-protection) behavior (dated
  2026-08-02 review).
- [Astral uv GitHub Actions caching](https://docs.astral.sh/uv/guides/integration/github/) and
  `uv cache prune --ci` guidance (dated 2026-08-02 review).
