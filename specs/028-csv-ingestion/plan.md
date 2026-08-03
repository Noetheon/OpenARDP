# Implementation Plan: Stable CSV Ingestion

**Branch**: `codex/f028-csv-ingestion` | **Date**: 2026-08-03

## Summary

Extend the existing built-in text parser rather than add a second ingestion service. A focused standard-library CSV
projector decodes the verified stream, retains physical newlines for correct quoted-field semantics and produces one
canonical JSON-text table block per logical record. The unchanged ingestion service publishes those blocks and exact
native bytes atomically. An explicit F028 benchmark mode ingests CSV and evaluates Q15/Q16 while default F025 replay
preserves its frozen unsupported-format contract.

## Technical Context

- Python 3.12, `csv`, Pydantic v2, existing SQLite/FTS/CAS; no dependency or network change.
- Existing 100 MiB source, 1 MiB physical-line and 100,000-block bounds.
- New immutable limits: 256 cells per record; 1 MiB decoded field and canonical record text.
- `TextMediaType.CSV`, `BlockKind.TABLE`, canonical RFC-8785-compatible JSON text and exact physical line ranges.
- Full Ruff, formatting, strict mypy, pytest, build, pre-commit, repository validation and remote matrix checks.

## Architecture

```text
explicit .csv path -> stable snapshot -> source CAS -> isolated text worker
                                                   -> strict CSV projector
                                                   -> canonical row blocks
                                                   -> atomic READY + FTS
                                                   -> F027 context compiler
```

The CSV adapter lives in `adapters/csv_parser.py`; the existing isolated adapter receives an explicit closed parser kind
and composes either the unchanged text recipe or the new CSV recipe. The parser port/domain remain provider-neutral.
Composition stays in existing `interfaces/` code. Benchmark execution and validation stay in `scripts/`.

## Constitution Check

Originals remain authoritative; the exact source CAS object is the native artifact. Derived records are disposable,
recipe-bound and reproducible. CSV content remains untrusted data. The adapter is local, deterministic, bounded and
provider-free. No ADR-governed store, identifier, schema or cloud change is required.

## Phases

1. Freeze CSV semantics, resource limits, losslessness oracle and F025 compatibility boundary.
2. Add domain, pure parser, isolated parser, source, CLI/watcher and security tests first.
3. Implement the focused CSV projector and minimally extend existing composition/publication.
4. Add explicit F028 execution and independent body-free validator against unchanged Q15/Q16 fixtures.
5. Run two fresh evaluations, document results/limitations and complete all clean-worktree gates.

## Risks and Controls

- **Logical cell loss**: ordered pair arrays and independent native-byte reconstruction tests; never use `DictReader`.
- **Quoted newline drift**: preserve decoded newline bytes for `csv.reader(newline="")`; use `line_num` ranges.
- **Amplification**: field/column/block/text limits plus measurement of source and representation storage.
- **Formula injection**: values remain untrusted inert strings; no spreadsheet export or execution.
- **Historical recipe drift**: CSV has a distinct recipe; the text recipe remains byte-identical. F028 benchmark mode is
  opt-in and the default frozen F025 behavior/reference remain unchanged.
- **Oracle leakage**: runtime code never imports questions or atoms; benchmark code only observes selected verified bodies.
