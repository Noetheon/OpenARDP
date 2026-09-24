# F041 implementation notes — lean governance

**Record type:** durable feature record (project governance). **Constitution:** 3.0.0 → 4.0.0 (major: the mandatory
lifecycle for high-assurance changes is replaced, and two articles are added).

## What changed

| Artifact | Change |
|---|---|
| `.specify/memory/constitution.md` and `spec-kit/CONSTITUTION_SOURCE.md` | Version 4.0.0, byte-identical, with a Sync Impact Report. Article XI becomes Lean Change Records; Article XII limits mandatory ADRs to irreversible or architectural decisions; Article XIII Usefulness First and Article XIV Agent Efficiency are added. X.4 requires only that a feature merges before dependent work begins. |
| `AGENTS.md` | Principles 15 (usefulness first) and 16 (agent efficiency); the "Lean change records" section replaces the tier workflow. |
| `CONTRIBUTING.md`, `specs/README.md`, `spec-kit/FEATURE_MAP.md`, `START_HERE.md` | Same rules; the feature map lists F040/F041 and replaces the pause boundary. |
| `pilots/usage-log/` | README and an empty CSV with one line per real task. |
| F038 pilot, `docs/31_MAINTENANCE_STATUS.md` | Marked as no longer gating development, with links to their replacements. Content kept. |
| Repository tests | Constitution tests now pin version 4.0.0 and the lean-record policy; the active feature is F040. |

The constitution text for Articles I–X (evidence preservation, derived data, provider neutrality, determinism, test
gates and fair measurement) is unchanged apart from X.4. The CI workflows, the coverage floor, the
three-platform gate and the release NO-GO are unchanged.

## Validation

The following ran on the final tree of this branch (F040 and F041 together), with the locked all-extras environment,
on Linux:

```text
uv run ruff check .                                  PASS  All checks passed!
uv run ruff format --check .                         PASS  452 files already formatted
uv run mypy src                                      PASS  no issues found in 146 source files
uv run pytest                                        PASS  1956 passed, 4 skipped in 671 s; branch coverage 86.29% (floor 85%)
uv run python scripts/validate_repository.py         PASS  Repository validation passed.
uv run python scripts/audit_maintainability.py       PASS  Maintainability audit passed.
SKIP=pytest uv run pre-commit run --all-files        PASS  ruff, format and mypy hooks; the pytest hook is the run above
uv build                                             PASS  openardp-0.1.0rc1 sdist and wheel
```

A fresh virtual environment with only the built wheel (no extras, no `docling-core`) ran `add`, `find` and `verify`
on Markdown. It reported a missing path as not found and a DOCX with the `uv sync --extra docling` hint.

The macOS and Windows jobs run in CI on the pull request.

## Tradeoffs and residual risks

- **Weaker upfront review.** Fewer mandatory stages mean less planning for complex changes. The ADR requirement for
  irreversible decisions, the durable-record requirement and the unchanged gates limit this risk.
- **Harder-to-read value evidence.** A usage log is weaker evidence than a controlled trial. The F038 protocol remains
  available when a formal comparison is worth its cost.

## Rollback

Revert this feature's commit. The constitution returns to 3.0.0 and the F038 pause text becomes current again. No
product behavior depends on this change.
