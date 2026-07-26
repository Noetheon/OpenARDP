# Start here

OpenARDP is built implementation-first, one bounded Spec Kit feature at a time. The
repository is complete through the Feature 005 lexical-search runtime, Feature 005A
strategic/governance boundary, and Feature 006 experimental evidence contracts. Feature
007 is the next work package; it must implement Docling against the F006 roots rather
than inventing a parallel public model.

## 1. Read the authoritative rules

Read [AGENTS.md](AGENTS.md), [Constitution 2.0.0](.specify/memory/constitution.md), the
[feature map](spec-kit/FEATURE_MAP.md), [operating procedure](spec-kit/OPERATING_PROCEDURE.md), accepted
[ADRs](docs/adr/) and the active feature’s `spec.md`, `plan.md` and `tasks.md`.

Version-suffixed v3.1 files are preserved adoption sources, not parallel authority. Historical feature specifications
remain evidence of the merged work they governed.

## 2. Reproduce the locked environment

Prerequisites are Git and `uv` 0.11.31. The project selects Python 3.12.

```bash
uv sync --all-extras --locked
```

The derived environment may live in uv’s centralized cache. The committed `uv.lock` remains authoritative and locked mode
does not silently rewrite it.

## 3. Run every mandatory gate

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run pre-commit run --all-files
uv run python scripts/validate_repository.py
uv build
```

Tests are offline by default, enforce branch coverage of at least 85 percent and use synthetic or redistributable
fixtures.

## 4. Exercise the delivered workflow

```bash
openardp init --store .openardp
openardp ingest ./notes.md --store .openardp --json
openardp list --store .openardp --json
openardp outline <document-uuid> --store .openardp --json
openardp get <block-uuid> --store .openardp --json
openardp search '"exact phrase" evidence' --store .openardp --json
openardp reindex --store .openardp --json
```

Feature 002 provides the domain models, public schemas and deterministic identities. Feature 003 provides the filesystem
CAS, SQLite catalog, migrations and persistence/reachability services. Feature 004 provides bounded local TXT/Markdown
ingestion and progressive exact navigation. Feature 005 provides deterministic lexical search, fail-closed coverage,
verified snippets and explicit index rebuild.

The search index is disposable and non-authoritative. Search content and security-sensitive metadata are verified against
the catalog and CAS. `reindex` rebuilds from verified READY evidence without altering original, representation or CAS
identity.

## 5. Respect the current boundary

The current implementation does not yet provide PDF/DOCX/PPTX parsing, context compilation, MCP, local watching,
retention/garbage collection, stable export or Microsoft Graph access. The [005A–017 sequence](spec-kit/FEATURE_MAP.md)
owns these outcomes individually.

Public contracts remain experimental interoperability candidates. Feature 006 publishes
the first four provider-neutral evidence/native/trust roots; later examples under
[`contracts/`](contracts/README.md) remain design guidance unless their own feature
promotes them to reviewed schemas. Feature 007 implements Docling while preserving
complete provider-native output.

## 6. Find focused evidence

- [F002 quickstart](specs/002-domain-models-schemas/quickstart.md)
- [F003 quickstart](specs/003-cas-sqlite-catalog/quickstart.md)
- [F004 quickstart](specs/004-text-ingestion-slice/quickstart.md)
- [F005 quickstart](specs/005-lexical-search/quickstart.md)
- [F005A validation](specs/005A-strategic-realignment/quickstart.md)
- [F006 validation](specs/006-evidence-contract-foundation/quickstart.md)
- [Validation record](VALIDATION.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

Do not rerun Spec Kit bootstrap during normal clone setup. Recovery and governance procedures are documented in the
[Spec Kit integration guide](docs/12_SPEC_KIT_INTEGRATION.md).
