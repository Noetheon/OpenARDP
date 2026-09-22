# F039 implementation notes — pytest security maintenance

**Risk tier:** High assurance, external development dependency and supply-chain change. **Worktree:** `codex/pytest-security-update`. **Acceptance:** exclude pytest versions below the patched 9.0.3 floor; keep all non-pytest package versions, runtime/optional requirements, tests, contracts, pilot and release decisions unchanged; run full existing gates before delivery; state residual advisories and rollback.

## Scope and decision

The [reviewed GitHub advisory](https://github.com/advisories/GHSA-6w46-j5rx-g56g) identifies CVE-2025-71176 in pytest releases before 9.0.3. This package changes only the dev-group requirement `pytest>=8.4,<9` to `pytest>=9.0.3,<10`. `uv lock --upgrade-package pytest==9.0.3` resolves the first patched release, preserving the project’s major-version boundary and its SHA-256 distribution hashes. `pytest` remains a development tool, absent from core runtime requirements. The [pytest upstream project](https://pypi.org/project/pytest/9.0.3/) identifies MIT licensing, active maintainers and Python support compatible with OpenARDP's Python 3.12 baseline. Existing `pytest-cov 6.3.0` and `pytest-socket 0.8.0` remain locked; actual compatibility is checked by tests.

This is necessary security maintenance during the F038 expansion pause. It is not a product successor, F038 human-pilot result or F015 release GO. No ADR is required: no architecture, public contract, persisted identity, provider-profile or release-decision boundary changes. The completed `spec.md` is the durable requirement record; the full planning lifecycle and pre-implementation analysis had no unresolved critical/high findings.

## Dependency and environment evidence

The branch diff against `main` changes one dev constraint, its `uv.lock` specifier, the pytest package version 8.4.2 → 9.0.3 and the pytest sdist/wheel URLs, sizes, timestamps and hashes. A `tomllib` comparison of the old and new lock parsed 143 package names on each side, with no additions/removals and exactly one changed package version: pytest. `uv lock --check` passed. A locked install reported pytest 9.0.3, pytest-cov 6.3.0 and pytest-socket 0.8.0.

An intermediate test invocation using the fresh default-only Worktree environment produced **46 passed, 2 failed**. The failures had bounded setup causes: the repository validator rejected F039’s still-active transient planning files, and the Docling dependency contract could not find the optional Docling extra. They did not show pytest 9 incompatibility. Re-running the relevant checks with the repository’s all-extras profile and excluding only the temporary active-feature governance assertion yielded **27 passed** for text parser + Docling dependency and **20 passed, 1 deselected** for repository-validation unit cases. The omitted governance assertion, full coverage and all tests are mandatory in the final compacted state below; they are not treated as passed yet.

## Security boundary and remaining findings

`uv audit --locked --output-format json` audited 142 packages and reported four advisory records for **two unique CVEs** in unchanged optional model packages: `accelerate 1.14.0` / CVE-2026-69112 and `transformers 5.8.1` / CVE-2026-9856. The command returns exit 1 because these remain. CVE-2025-71176 is absent from this post-change audit, which is the bounded pytest closure claim. Duplicate GHSA/PYSEC records are not four distinct vulnerabilities. No scanner or audit result establishes that the entire optional graph is free of vulnerabilities.

GitHub Dependabot alerts were activated separately from this branch. The read-only API snapshot during this work package showed three open alerts on the repository’s current main dependency graph: pytest GHSA-6w46-j5rx-g56g, transformers GHSA-xrqw-3rrv-vx5w and accelerate GHSA-4j2p-28q2-5m79. This unmerged worktree does not yet update GitHub's main-branch graph or close the pytest alert. The pytest-only bump should close only GHSA-6w46-j5rx-g56g after a verified main-branch graph refresh; the two optional model alerts remain independent.

## Exact preliminary commands and results

```text
uv lock --upgrade-package pytest==9.0.3                  PASS; pytest 8.4.2 -> 9.0.3
uv lock --check                                          PASS; resolved 143 packages
uv tree --locked --depth 1 --package pytest             PASS; pytest 9.0.3
uv run --locked pytest --no-cov tests/test_repository_validation.py tests/unit/test_text_parser.py tests/contract/test_docling_dependency.py
                                                         INTERMEDIATE FAIL; 46 passed, 2 setup/active-artifact failures
uv run --locked --all-extras pytest --no-cov tests/unit/test_text_parser.py tests/contract/test_docling_dependency.py
                                                         PASS; 27 passed
uv run --locked --all-extras pytest --no-cov tests/test_repository_validation.py -k 'not test_real_repository_contract_is_clean'
                                                         PASS; 20 passed, 1 temporarily deselected
uv audit --locked --output-format json                   EXIT 1; 4 records / 2 unchanged optional CVEs, no pytest CVE
```

No test, socket setting, coverage floor, CI policy or application source was changed to resolve the intermediate failures. The full required gates ran after Spec-Kit convergence and removal of transient artifacts; their exact outputs appear below. The existing ready-PR Linux/macOS/Windows matrix remains a pre-merge delivery condition.

## Tradeoffs, rollback and residual risk

Choosing the first patched pytest release and a `<10` cap limits lock drift but moves the development test runner across a major version. The complete suite and three-platform CI are therefore required before merge. If a genuine compatibility problem appears, revert this one scoped change through a reviewed branch; do not drop tests, disable socket denial, reduce coverage or silently restore vulnerable pytest 8. Optional model advisories require separate, evidence-backed work if those profiles become necessary; this F039 package makes no claim about them.

## Final local validation after convergence

Spec-Kit convergence assessed all five functional requirements, four success criteria, the single maintainer scenario, the exact dependency diff and the governing constitution. It found **zero missing, partial, contradictory or unrequested implementation gaps**, and no new convergence task was needed. The first local commit `4979228` preserves the complete analyzed planning lifecycle in Git history. Transient planning files were then removed from the live tree, and `.specify/feature.json` returned to the F038 product-pilot record. The normal repository contract test therefore runs against the intended final state rather than a special-case exception.

The final all-extras environment and unchanged required gates passed:

```text
uv sync --all-extras --locked                    PASS; resolved 143 packages, checked 121 installed packages
uv run --locked ruff check .                     PASS; All checks passed
uv run --locked ruff format --check .           PASS; 423 files already formatted
uv run --locked mypy src                        PASS; no issues in 129 source files
uv run --locked pytest                          PASS; 1,854 passed, 4 skipped in 205.86 seconds; branch coverage 85.56% >= 85%
```

The four skipped tests remain the existing opt-in reference/model checks; no skip was introduced by F039. Full-suite success includes the ordinary repository contract, Docling dependency contract, existing socket denial and unchanged coverage gate. No second full-suite run was needed for the subsequent documentation-only evidence update; the repository validator below checks that final text.

The final worktree still requires exact-head Linux/macOS/Windows ready-PR CI, verified merge and GitHub main-branch dependency-graph refresh before a remote pytest alert can be marked closed. Local success does not override F038's pending human-pilot data or F015's release NO-GO.

## Final repository and audit checks

```text
uv run --locked python scripts/validate_repository.py   PASS; Repository validation passed
uv run --locked python scripts/audit_ci.py audit        PASS; finding_count 0
uv lock --check                                        PASS; resolved 143 packages
uv build                                               PASS; wheel and sdist built
git diff --check                                       PASS; no whitespace errors
uv audit --locked --no-dev --no-extra docling --no-extra semantic --no-extra visual --output-format json
                                                       PASS; 6 core packages, 0 advisory records
```

The core-only audit is profile-specific, not a whole-lock clearance. The all-profile locked audit above still reports two unique optional model CVEs; its nonzero exit is expected until those are resolved in separate reviewed work. The generated distribution files are build outputs, not a release. Independent review of the scoped dependency diff found no critical/high static finding and matched the pytest 9.0.3 PyPI artifact hashes; local convergence likewise found no critical/high gap. Remote three-platform CI and alert closure are not claimed here.
