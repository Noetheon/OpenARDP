# Quickstart: Text Ingestion Vertical Slice

All examples run locally. F004 makes no network or model request.

## Prepare the locked environment

```bash
uv sync --all-extras --locked
```

## Initialize one explicit workspace

```bash
uv run openardp init --store .openardp
```

Repeated initialization of the same compatible workspace is idempotent. Other commands fail rather than initialize a
missing workspace implicitly.

## Ingest TXT or Markdown

```bash
uv run openardp ingest notes.md --store .openardp
uv run openardp ingest notes.md --store .openardp --json
```

The first command snapshots exact bytes into CAS, parses the immutable snapshot and commits one complete READY
representation. Repeating it unchanged returns `CACHE_HIT` and invokes the parser zero times. `--force` deliberately
reparses and must converge on the identical immutable representation.

Supported built-in inputs are strict UTF-8 `.txt`, `.md` and `.markdown` files up to 100 MiB. Links, directories, special
files, NUL-containing input, invalid UTF-8, overlong lines and excessive block counts are rejected.

## Inspect prepared evidence

```bash
uv run openardp list --store .openardp
uv run openardp status notes.md --store .openardp
uv run openardp outline DOCUMENT_ID --store .openardp
uv run openardp outline DOCUMENT_ID --version sha256:SOURCE_HASH --store .openardp
uv run openardp get BLOCK_ID --store .openardp
```

`list`, `status` and `outline` are body-minimizing. `get` is the only command above that returns one exact normalized block
body. All returned content remains untrusted data with instruction execution disabled.

## Stable JSON output

Append `--json` to any command:

```bash
uv run openardp list --store .openardp --json
```

Each JSON-mode command writes exactly one versioned envelope to standard output. Success exits 0; usage exits 2; missing
records exit 3; rejected input exits 4; busy/conflict exits 5; workspace/integrity failure exits 6.

## Focused acceptance commands

```bash
uv run --locked pytest tests/domain/test_ingestion.py tests/contract/test_ingestion_ports.py --no-cov
uv run --locked pytest tests/unit/test_text_parser.py --no-cov
uv run --locked pytest tests/integration/test_ingestion_catalog.py --no-cov
uv run --locked pytest tests/integration/test_ingestion_service.py tests/integration/test_document_query.py --no-cov
uv run --locked pytest tests/integration/test_cli.py tests/security/test_local_source_boundaries.py --no-cov
```

## Mandatory repository gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run --locked pre-commit run --all-files
uv build
git diff --check
```

Passing F004 proves the bounded TXT/Markdown ingestion and navigation slice. It does not prove FTS search, rich-document
parsing, block reconciliation, watcher automation, MCP access or benchmark targets from later features.
