# Start here

OpenARDP is built implementation-first, one bounded Spec Kit feature at a time. The
repository is complete through the Feature 005 lexical-search runtime, Feature 005A
strategic/governance boundary, Feature 006 experimental evidence contracts, Feature
007's bounded Docling-native adapter and Feature 008's deterministic context compiler
with body-free selection receipts, plus Feature 009's dependency-free read-only MCP
stdio interface and Feature 010's conservative reconciliation plus exact derivation
DAG lifecycle, followed by Feature 011's explicit bounded PDF visual-evidence
materialization and handle-only context integration.
Feature 012 adds explicit bounded local polling, durable stability observations and
cancellable foreground ingestion jobs without a daemon or MCP write surface.
Feature 013 adds conservative retention explanation, reversible quarantine, separately
acknowledged reclamation, paired recovery, explicit migration and atomic index rebuild.

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
openardp ingest ./document.docx --store .openardp --json
openardp evidence <document-uuid> --store .openardp --json
openardp get-evidence <projection-sha256> --document <document-uuid> --store .openardp --json
openardp context "Which exact controls are documented?" \
  --document <document-uuid> --budget 12000 --unit tokens --mode verification \
  --store .openardp --json
openardp context-receipt <receipt-sha256> --store .openardp --json
openardp context "Which exact controls are documented?" \
  --replay <receipt-sha256> --store .openardp --json
openardp visual-materialize <document-uuid> <projection-sha256> \
  --store .openardp --json
openardp visual-evidence <visual-evidence-sha256> --store .openardp --json
openardp watch /absolute/documents --store .openardp --once --stability-ms 0 --json
openardp jobs --store .openardp --limit 50 --json
openardp storage-inventory --store .openardp --json
openardp storage-diagnostics --store .openardp --json
openardp workspace-backup --store .openardp --destination ../openardp-backup --json
openardp mcp --store .openardp
```

Feature 002 provides the domain models, public schemas and deterministic identities. Feature 003 provides the filesystem
CAS, SQLite catalog, migrations and persistence/reachability services. Feature 004 provides bounded local TXT/Markdown
ingestion and progressive exact navigation. Feature 005 provides deterministic lexical search, fail-closed coverage,
verified snippets and explicit index rebuild. Feature 008 compiles bounded evidence
under an exact estimator budget, persists bundle and receipt atomically and replays the
recorded snapshot byte-identically. Feature 009 exposes those verified query, evidence,
search and context services as nine identifier-scoped MCP tools without accepting client
filesystem paths or opening a network listener.

Feature 010 reconciles two explicitly selected READY F002 representations, persists
logical continuity separately from exact reuse eligibility, and transactionally
invalidates or reactivates only the exact derivation dependency closure. It adds no
CLI/MCP mutation, watcher, provider or model execution.

Feature 011 explicitly materializes one accepted PDF projection into a reusable page
raster, exact crop and thin descriptor. VISUAL compilation selects only an already
materialized verified descriptor handle; it never renders implicitly. The optional
OCR/caption port has no built-in provider and all results remain untrusted F010
derivations. DOCX/PPTX page rendering is still unavailable.

Feature 012 watches only one operator-supplied canonical local directory disjoint from
the workspace. Complete bounded rescans establish truth; metadata only controls
stability while existing ingestion still hashes exact bytes. Deletes create watcher
tombstones, queue pressure requests a later rescan, and job retry/cancellation remain
durable and fenced across restart.

Feature 013 treats every catalog reference as a conservative live root. A reclamation
plan is read-only and must be supplied unchanged to quarantine. Quarantine is reversible;
commit is the only irreversible command and requires an expired named batch plus
`--acknowledge-irreversible-removal`. Backups use a verified internal manifest, restores
target only fresh disjoint paths, and older supported workspaces migrate only through
`workspace-migrate` after a paired pre-upgrade backup.

The search index is disposable and non-authoritative. Search content and security-sensitive metadata are verified against
the catalog and CAS. `reindex` rebuilds from verified READY evidence without altering original, representation or CAS
identity. Context compilation applies the same rule: accelerator hits are reverified
against content-addressed bodies, and drifted or incomplete coverage fails closed until
an explicit `reindex`.

## 5. Respect the current boundary

The optional Docling extra provides bounded DOCX/PPTX parsing and PDF parsing only
with reviewed local assets. Feature 008 provides deterministic local context
compilation, body-free receipts and replay. Feature 009 exposes the same verified
application services through a bounded read-only stdio MCP server. The current
implementation does not provide a watcher daemon, network-share correctness, scheduled
or automatic garbage collection,
HTTP transport, stable export or Microsoft Graph access. The
[005A–017 sequence](spec-kit/FEATURE_MAP.md) owns these
outcomes individually.

Public contracts remain experimental interoperability candidates. Feature 006 publishes
the first four provider-neutral evidence/native/trust roots; Feature 008 adds the
public `ContextBundle 0.2.0` and experimental `SelectionReceipt 0.1.0` roots. Later
examples under [`contracts/`](contracts/README.md) remain design guidance unless their
own feature promotes them to reviewed schemas. Feature 007 implements Docling while
preserving complete provider-native output.

## 6. Find focused evidence

- [F002 quickstart](specs/002-domain-models-schemas/quickstart.md)
- [F003 quickstart](specs/003-cas-sqlite-catalog/quickstart.md)
- [F004 quickstart](specs/004-text-ingestion-slice/quickstart.md)
- [F005 quickstart](specs/005-lexical-search/quickstart.md)
- [F005A validation](specs/005A-strategic-realignment/quickstart.md)
- [F006 validation](specs/006-evidence-contract-foundation/quickstart.md)
- [F007 quickstart](specs/007-docling-native-adapter/quickstart.md)
- [F008 quickstart](specs/008-context-compiler-receipts/quickstart.md)
- [F009 quickstart](specs/009-read-only-mcp/quickstart.md)
- [F010 quickstart](specs/010-reconciliation-derivation-dag/quickstart.md)
- [F011 quickstart](specs/011-visual-evidence-escalation/quickstart.md)
- [F012 quickstart](specs/012-local-watcher-and-jobs/quickstart.md)
- [F013 quickstart](specs/013-retention-recovery-migrations/quickstart.md)
- [Validation record](VALIDATION.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

Do not rerun Spec Kit bootstrap during normal clone setup. Recovery and governance procedures are documented in the
[Spec Kit integration guide](docs/12_SPEC_KIT_INTEGRATION.md).
