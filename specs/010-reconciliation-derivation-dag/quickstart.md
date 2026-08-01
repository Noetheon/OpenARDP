# Quickstart: Reconciliation and Derivation DAG

## Purpose

Demonstrate safe cross-version lineage, exact dependency invalidation and A→B→A reuse
without a model, network call, watcher or MCP mutation.

## Prerequisites

- Python 3.12 and `uv`.
- A clean checkout on `codex/f010-reconciliation-derivation-dag`.
- No external service or document is required; all fixtures are synthetic.

## Install and validate the locked environment

```bash
uv sync --frozen --all-extras --dev
uv run python scripts/validate_repository.py
```

## Run the labelled reconciliation safety corpus

```bash
uv run pytest --no-cov tests/domain/test_reconciliation_corpus.py -q
```

Expected properties:

- at least 100 labelled reuse decisions;
- reusable precision exactly `1.000` and false-reuse count `0`;
- ambiguous duplicate/tie cases receive new lineages;
- reported recall and per-phase counts are deterministic.

## Run transactional lifecycle demonstrations

```bash
uv run pytest --no-cov \
  tests/integration/test_f010_catalog.py \
  tests/domain/test_reconciliation.py \
  tests/domain/test_derivation_lifecycle.py -q
```

The tests demonstrate:

1. CAS-backed relations and complete lineage membership appear atomically.
2. Exact duplicate publication converges while divergent output conflicts.
3. One changed leaf stales only its direct/transitive dependants.
4. Slot replacement uses `SUPERSEDED`, not `STALE`.
5. A→B→A reactivates the original record/output identities without generation.
6. Cancellation/fault injection leaves no partial catalog facts.

## Run migration and reachability evidence

```bash
uv run pytest --no-cov \
  tests/integration/test_f010_migration.py \
  tests/integration/test_reachability.py -q
```

Back up a real revision-6 workspace before opening it with revision-7 software. There
is no in-place downgrade; rollback requires restoring that backup.

## Full quality gate

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv build
uv run python scripts/validate_repository.py
```

## Safety interpretation

A `same_logical_block_as` relation records conservative continuity. It does not by
itself authorize reuse. Reuse additionally requires the exact same binding digest and
all other derivation inputs. `STALE` means ineligible for current-head use, not deleted
or intrinsically invalid for its historical pinned scope.
