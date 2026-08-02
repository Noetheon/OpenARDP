# CI Cost, Quality and Operating Model

**Status:** F019 implementation record

**Observed baseline:** 2026-08-01

## Outcome

OpenARDP keeps the complete offline test inventory on Linux, macOS and Windows for every ready pull request that can
affect executable behavior. Savings come from removing redundant coverage, lint, typing, build, post-merge matrix and
ordinary-commit release work—not from dropping a platform, test, security control or threshold.

## Before and after topology

| Event | Before F019 | F019 |
|---|---:|---:|
| Draft PR synchronization | 7 jobs | Preflight with classification; 3 stable final checks skipped |
| Ready code/unknown PR | 7 jobs | Preflight + 3 complete platform suites |
| Ready governance-only PR | 7 jobs | Preflight with classification; 3 stable final checks skipped |
| Merge push to `main` | 7 jobs | Preflight with classification only |
| Release-owned ready PR | Included in every CI run | Separate 3-platform evidence + aggregate gate |
| Version tag/manual release | No distinct boundary | Separate complete release workflow |

Ubuntu is the single coverage and platform-independent quality owner. It runs Ruff, format checking, strict mypy, all
tests with socket denial and at least 85 percent branch coverage, repository validation and distribution build. macOS
and Windows each run the same complete test inventory with `--no-cov`; only coverage instrumentation is omitted. A local
same-checkout measurement ran 1,381 tests in 141.64 seconds with coverage and 93.71 seconds without it, reducing that
test phase by 33.8 percent.

## Dated cost evidence

[`ci-cost-baseline-2026-08-01.json`](../quality/ci-cost-baseline-2026-08-01.json) stores only aggregate observations:
34 workflow runs, 158 jobs and 939 per-job rounded billable minutes. The calculation uses the runner-price snapshot
reviewed on 2026-08-02 from the official
[GitHub runner-pricing reference](https://docs.github.com/en/billing/reference/actions-runner-pricing):

| Runner | Rounded minutes | USD/minute | Gross modeled USD |
|---|---:|---:|---:|
| Linux | 277 | 0.006 | 1.662 |
| Windows | 463 | 0.010 | 4.630 |
| macOS | 199 | 0.062 | 12.338 |
| **Total** | **939** | — | **18.630** |

The comparable-activity target is a 55–65 percent reduction, or 6.520–8.384 USD against this gross baseline. Applied
only as an illustration to the owner's approximately 15 USD observed charge, the same percentage range is about
5.25–6.75 USD. Neither figure is an invoice forecast: included usage, account adjustments, taxes, per-job rounding,
cache hits, PR draft discipline and future GitHub pricing can change realized cost.

The model assumes intermediate pushes remain draft, one final ready run, no duplicate three-platform merge run and no
release reproduction on ordinary changes. The first month of actual workflow usage should be compared with a new dated
snapshot; the baseline file must not be rewritten.

## Deterministic enforcement

[`ci-policy.json`](../quality/ci-policy.json) is the reviewed machine policy.
[`audit_ci.py`](../scripts/audit_ci.py) uses only the standard library and provides three commands:

```bash
uv run --locked python scripts/audit_ci.py classify --paths-file PATH
uv run --locked python scripts/audit_ci.py audit
uv run --locked python scripts/audit_ci.py estimate
```

The positive governance allowlist covers exact root governance documents plus `docs/`, `specs/` and
`spec-kit/feature-prompts/`. An empty, unsafe, unknown or mixed set is `full`. The classifier reads and emits names only;
it never opens changed file bodies. CI/workflow, policy, dependency, build, source, test, schema, script and release
changes are therefore full by default.

Core workflow-level path filters are intentionally absent. GitHub documents that a workflow skipped by path filtering
can leave a required check pending, while a
[job skipped by a job-level condition](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-jobs-with-conditions)
concludes successfully. Preflight and
the three explicit final job names are stable for branch protection even when the latter are legitimately skipped.

## Draft-to-Ready operation

1. Open active work as a draft and push intermediate changes there.
2. Classification and Preflight validate policy, governance, lock state and repository structure on each update.
3. Mark the PR ready only when it is a merge candidate; `ready_for_review` starts the complete applicable final gate.
4. Code/unknown PRs require `Quality (ubuntu-latest)`, `Quality (macos-latest)` and
   `Quality (windows-latest)`. Governance-only PRs conclude those explicit jobs as skipped-success.
5. If more iterations are needed, return the PR to draft before pushing them, then promote it again.

Do not use commit-message CI skip directives on merge candidates. Do not classify by extension or expand the governance
allowlist without tests showing the path cannot affect executable/release behavior.

## Cache boundary

The SHA-pinned `setup-uv` action persists only uv download/build cache entries keyed by `uv.lock`. Every job still runs
`uv sync --locked`, and Astral's documented
[`uv cache prune --ci`](https://docs.astral.sh/uv/guides/integration/github/) removes inefficient cache content at the
end. `.venv`, distributions,
coverage, evidence output and repository state are never cached. A miss or corrupt cache cannot authorize dependency
drift; locked synchronization remains authoritative.

The downstream release aggregator is intentionally the one uncached exception. The first remote F019 run measured
5 minutes 27 seconds inside cache-enabled setup immediately after the Linux evidence producer, while the aggregator's
subsequent locked synchronization took one second and all remaining work took ten seconds. Omitting restore/save for
this tiny consumer avoids same-key publication contention and remains fully reproducible through `uv sync --locked`.

## Release evidence boundary

The separate Release Evidence workflow retains the F015 Linux/macOS/Windows evidence matrix, frozen security registry,
candidate build/offline install, immutable uploads, aggregate no-waiver gate and explicit `NO-GO` assertion. It runs on
manual dispatch, `v*` tags and ready PRs changing reviewed release-owned paths. It does not run for ordinary `main`
pushes or draft PRs. This changes scheduling only; committed evidence and the release decision remain unchanged.

## Residual risks

- Savings depend on contributors using Draft-to-Ready as documented; repeated ready-state pushes deliberately rerun the
  final matrix.
- GitHub runner images, prices, cache implementation and billing policies are external and can change.
- Static marker auditing complements rather than replaces GitHub's workflow parser; the final private PR is the
  authoritative cross-platform execution proof.
- Governance-only classification deliberately spends a Linux Preflight job to guarantee a concluded required check and
  fail-closed policy evaluation.
- Release-owned path filters require review when F015 files move or a new release component is added.

## Rollback

Revert the single F019 merge through a new protected PR, restore the prior combined workflow and update required status
contexts to the restored job names. Do not force-push, delete evidence, lower coverage or disable protection. No product
migration, stored state, schema, dependency or provider operation needs reversal.
