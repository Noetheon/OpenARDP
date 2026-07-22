# Codex execution plan — Spec Kit integrated

This plan is intentionally sequential. Each work package is implemented as the matching bounded feature in
[`spec-kit/FEATURE_MAP.md`](../spec-kit/FEATURE_MAP.md). Do not ask one agent to implement the entire platform in a single
unreviewed change.

## Mandatory lifecycle per work package

Before implementation, use the matching file in `spec-kit/feature-prompts/` and complete:

```text
$speckit-specify
$speckit-clarify
$speckit-plan
$speckit-checklist
$speckit-tasks
$speckit-analyze
```

Implementation is blocked by unresolved critical analysis findings. Implement in bounded phases, run repository quality
gates, then use `$speckit-converge` until the feature converges. Project-level architecture is referenced rather than
duplicated into every feature.

## Work package 0 — repository baseline

Deliver:

- `uv` project and lock file;
- package layout from `AGENTS.md`;
- Ruff, mypy, pytest and coverage;
- pre-commit hooks;
- CI with least privileges;
- license/security/contribution files;
- basic docs validation.

Acceptance:

```bash
uv sync --all-extras
uv run ruff check .
uv run mypy src
uv run pytest
```

all pass on Linux, macOS and Windows where practical.

## Work package 1 — domain models and schemas

Implement Pydantic models and JSON Schemas for manifest, block, derivation, relation and context bundle. Add canonical JSON
serialization and hash utilities.

Acceptance:

- schema round-trip tests;
- deterministic hashes across process runs;
- unsupported major schema rejected;
- golden fixtures validated.

## Work package 2 — filesystem CAS and SQLite catalog

Implement immutable object writes, atomic staging, document registration, version and job tables, migrations and garbage
collection reachability analysis.

Acceptance:

- concurrent duplicate writes store one valid object;
- interrupted commit exposes no partial version;
- catalog recovery tests pass;
- path traversal tests pass.

## Work package 3 — text vertical slice

Implement TXT/MD parser, normalizer, ingestion service and CLI commands `init`, `ingest`, `list`, `status`, `outline`, `get`.

Acceptance:

- second ingest of unchanged file records cache hit and does not call parser;
- changed file creates new version;
- original source remains unchanged;
- every block has source provenance.

## Work package 4 — lexical search

Implement SQLite FTS5, block indexing, filters and `search` command.

Acceptance:

- exact term and phrase tests;
- deterministic ranking tests where possible;
- deleted/superseded versions excluded by default;
- result includes exact version and block source.

## Work package 5 — Docling adapter

Pin and integrate Docling behind `ParserAdapter`. Preserve native Docling JSON. Normalize core text/table/picture/page/slide
metadata. Run parser in a subprocess with limits.

Acceptance:

- synthetic PDF/DOCX/PPTX fixtures;
- parser warnings retained;
- no external model/network call in default profile;
- timeout/crash produces clean failed job;
- repeated source hash skips conversion.

## Work package 6 — context compiler

Implement deterministic evidence modes and budget allocation. Begin with lexical retrieval and structural expansion. Add CLI
`context --json`.

Acceptance:

- numeric task includes exact table/source evidence;
- visual task reports required visual evidence even if asset retrieval is not yet implemented;
- budget never exceeded beyond declared estimator tolerance;
- bundle pins exact versions.

## Work package 7 — MCP server

Use stable MCP Python SDK version available at implementation time; pin upper bounds across major transitions. Wrap services
with read-only tools and resource handles.

Acceptance:

- Codex can list, search, compile context and fetch a block;
- large outputs return file/resource handles;
- arbitrary filesystem paths cannot be read;
- injection fixture cannot invoke a side-effect tool because none exists.

## Work package 8 — watcher and job recovery

Implement local watcher, debouncing, stable snapshot checks and persistent job states.

Acceptance:

- multiple Word-like save events create one job;
- `~$` files ignored;
- process restart resumes/reconciles pending work;
- file deletion state handled without deleting historical versions.

## Work package 9 — block reconciliation and derivation DAG

Implement stable block matching, derivation records, cache reuse and invalidation.

Acceptance:

- one paragraph edit preserves unrelated block IDs/artifacts;
- low-confidence matches do not reuse derived data;
- changed table invalidates dependent summaries only;
- algorithm version recorded.

## Work package 10 — visual evidence and lazy enrichment

Implement asset extraction/crops and provider-neutral OCR/caption interfaces. Default remains off or local-only.

Acceptance:

- source image/crop retrievable by handle;
- OCR/caption explicitly labelled derived;
- no model call on cache hit;
- provider egress policy enforced.

## Work package 11 — portable package

Implement export/import/verify with integrity manifest and safe ZIP handling.

Acceptance:

- byte corruption detected;
- path traversal rejected;
- imported package produces equivalent logical records;
- unsupported major version rejected.

## Work package 12 — benchmark and security release gate

Implement all conditions in the benchmark strategy and publish raw results.

Acceptance:

- reproducible command and environment metadata;
- no unsupported marketing claims;
- threat-model test suite green;
- benchmark demonstrates where OpenARDP helps and where it does not.

## Work package 13 — Microsoft Graph design spike, not production

Create connector interface, mocked delta tests and a deployment ADR. Do not request broad production permissions yet.

Acceptance:

- webhook treated as wake-up signal;
- delta link persisted atomically;
- deletion and permission-change scenarios modelled;
- least-privilege permission analysis documented.

## Codex feature execution rule

Use the feature prompt corresponding to the work package. Codex must first produce and analyze Spec Kit artifacts, then
implement only the active feature. The first-session prompt is `spec-kit/FIRST_CODEX_SESSION.md`; later sessions may use
`prompts/CODEX_MASTER_PROMPT.md`.
