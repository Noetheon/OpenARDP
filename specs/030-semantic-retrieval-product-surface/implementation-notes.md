# Implementation Notes: Semantic Retrieval Product Surface

## Acceptance criteria restatement

- Preserve lexical, provider-free context compilation and replay as the default CLI/MCP behavior.
- Expose only the exact F029 v0.3 semantic profile through explicit local capability configuration; do not add a new
  ranking policy, answer generator, network path, persisted vector or universal-vector claim.
- Require bundle and source-lock paths together at the trusted CLI/server boundary and grant MCP clients only a bounded
  lexical/semantic enum.
- Bind semantic receipts and replay to the complete provider recipe plus algorithm identity and fail closed on missing,
  drifted or mismatched capability.
- Reuse one provider lifecycle per MCP session, close it on all exits, retain handle-first output and sanitize failures.
- Measure two exact-bundle cold/warm pairs on fresh workspaces and independently validate body-free evidence, identities,
  cache reuse, memory, latency and deterministic projections.

## Delivered behavior

`context_composition.py` classifies only known persisted lexical and semantic algorithms and builds the fixed F029
profile. The cohesive `context_cli.py` module owns compile/replay profile resolution, all-or-none configuration and
provider cleanup, keeping the legacy CLI composition root below its reviewed maintainability ceiling. The CLI delegates
without changing its output envelope or lexical behavior.

MCP interface `0.2.0` adds one optional `retrieval_profile` property to `compile_context`. The operator alone supplies
semantic bundle paths at process start. An unconfigured semantic request returns `invalid_params`, never falls back, and
does not prevent later lexical use. One provider instance serves the session and is closed in a `finally` boundary.

Semantic replay first verifies and loads the persisted receipt through the lexical-capable loader, infers its profile
from the algorithm identity, then constructs the requested exact compiler. A mismatched profile or provider recipe is
rejected before replay returns evidence. No catalog, CAS, schema, receipt or dependency change was required.

## Exact binding outcome

- Decision: `SEMANTIC_SURFACE_READY`
- Binding runs: 2; fresh workspaces per run: 2
- Cold query wall total: 348,695,467,667 ns
- Warm query wall total: 252,879,736,291 ns
- Warm/cold ratio: 0.725216 (27.4784% lower warm wall time)
- Warm passage-cache reuse: 121,828/121,828 (100%)
- Peak provider-worker RSS: 1,500,725,248 bytes (1.398 GiB)
- Exact bundle verification total: 444,947,750 ns
- Within-run and across-run timing-free projection identity: true
- Provider bundle: 6 files, 492,794,646 bytes, external to Git

## Tradeoffs and residual risks

The profile materially benefits repeated queries but remains expensive: it needs a 492.8 MB external bundle and reached
roughly 1.50 GB worker RSS on the reference Mac. The cold/warm totals include the unchanged nineteen-query workload and
fresh product workspaces, not a single-request SLO. Linux and Windows model timing is unmeasured even though model-free
surface behavior is portable and covered in CI. One small NASA/CISA corpus cannot establish broad-domain retrieval or
generation quality. Lexical retrieval therefore remains the correct default.

The benchmark's cold phase already records 57,708 cache hits because passages repeat across its nineteen questions;
"cold" means a fresh provider lifecycle, while "warm" means the second fresh workspace against the same in-process
passage cache. The report exposes both raw counts so this distinction cannot be mistaken for a completely uncached
single query.

## Convergence evidence

- `uv run --locked ruff check .`: passed
- `uv run --locked ruff format --check .`: 377 tracked files formatted
- `uv run --locked mypy src`: 107 source modules, no issues
- `uv run --locked pytest`: 1,720 passed, 4 skipped, 85.35% branch coverage in a clean staged-tree export
- `uv run --locked pre-commit run --all-files`: all four hooks passed, including the complete no-network test gate
- Repository, CI-policy and maintainability validators: passed
- F030 reference validator and retained F029 v0.1/v0.2/v0.3 validators: passed
- Release-specific tests/security controls: 22/22 and 44/44 passed
- Wheel and sdist build, isolated offline wheel installation and CLI smoke test: passed
- Dependency review and SBOM: all 125 components current
- Release evidence: regenerated for the exact clean F030 source tree and independently validated; existing global
  release decision remains truthfully `NO-GO`

The main workspace retains 39 unrelated untracked duplicate files owned by the user. They were neither modified nor
staged. Because four use Python filenames ending in ` 2.py`, they contaminate local package discovery and coverage if
tests scan the dirty directory directly. The authoritative gate therefore used `git checkout-index` to export exactly
the staged product tree, preserving both the user's files and the repository's strict module-inventory test.
