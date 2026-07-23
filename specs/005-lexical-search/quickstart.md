# Quickstart Validation: Lexical Search over Prepared Evidence

**Feature**: `005-lexical-search` | **Spec**: [spec.md](spec.md) | **Contracts**: [contracts/lexical-search.md](contracts/lexical-search.md)

Runnable end-to-end validation scenarios. All commands run offline against a synthetic temporary workspace; no
network access occurs at any point.

## Prerequisites

```bash
uv sync --locked
uv build
```

## Scenario 1 — First ingest becomes searchable atomically

```bash
printf '# Alpha Guide\n\nThe quick brown fox jumps.\n\n## Setup\n\nInstall the alpha package.\n' > /tmp/alpha.md
printf 'alpha release notes\n\nThe quick brown fox appears again.\n' > /tmp/notes.txt
openardp init --store /tmp/ws
openardp ingest /tmp/alpha.md --store /tmp/ws
openardp ingest /tmp/notes.txt --store /tmp/ws
openardp search "quick brown fox" --store /tmp/ws --json
```

Expected: hits from both documents, each with exact document/version/representation/block identity, line range,
kind, trust zone and a bounded snippet; no full bodies; exit code 0. Deleting `/tmp/alpha.md` and `/tmp/notes.txt`
and repeating the query returns identical results (search reads only persisted evidence).

## Scenario 2 — Phrase, term and filter semantics

```bash
openardp search '"quick brown fox"' --store /tmp/ws --json   # exact adjacent phrase
openardp search 'quick setup' --store /tmp/ws --json         # AND of two terms, no adjacency
openardp search 'alpha' --kind heading --store /tmp/ws --json
openardp search 'fox' --document /tmp/notes.txt --limit 1 --store /tmp/ws --json
```

Expected: phrase matches only adjacent sequences; term AND requires both tokens anywhere in one block; kind/trust
filters validate against the F002 vocabularies; `--limit 1` returns one hit with `truncated: true` and
`available >= 2`.

## Scenario 3 — Superseded versions excluded by default

```bash
printf '# Alpha Guide\n\nThe quick brown fox sprints.\n' > /tmp/alpha.md
openardp ingest /tmp/alpha.md --store /tmp/ws
openardp search 'jumps' --store /tmp/ws --json
openardp search 'jumps' --all-versions --store /tmp/ws --json
```

Expected: the default query returns zero hits (the old version is superseded); the history query returns the old
version's hit with its exact previous `version_id`.

## Scenario 4 — Backfill a pre-F005 workspace

Construct a workspace whose representations were committed with the F004 binary (or delete the scope's entries with a
disposable probe), then:

```bash
openardp search 'alpha' --store /tmp/ws --json    # fails: search_index_incomplete, exit 6
openardp reindex --store /tmp/ws --json           # per-scope outcomes: rebuilt
openardp reindex --store /tmp/ws --json           # idempotent: every scope reports current
openardp search 'alpha' --store /tmp/ws --json    # now serves verified hits
```

Expected: representations and CAS objects are byte-identical before and after backfill; the second `reindex` is a
no-op.

## Scenario 5 — Rejection and safety corpus

```bash
openardp search '' --store /tmp/ws --json                       # rejected_input, exit 4
openardp search 'AND OR NEAR(' --store /tmp/ws --json           # literal tokens; zero or lexical hits, exit 0
openardp search 'fox' --kind nope --store /tmp/ws --json        # rejected_input, exit 4
openardp search 'fox' --store /tmp/missing --json               # workspace classification, exit 6
```

Expected: sanitized classifications without document bodies, SQL text or internal details; hostile document content
inside snippets is escaped and inert.

## Acceptance gate

All five scenarios pass offline; `uv run pytest` covers each scenario deterministically; the locked repository gates
(Ruff, format, strict mypy, pytest with coverage, pre-commit, build) pass on Linux, macOS and Windows.
