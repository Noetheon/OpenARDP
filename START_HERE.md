# Start here

**Using OpenARDP for a document task?** Start with the short
[practical document workflow](docs/30_LOCAL_DOCUMENT_WORKFLOW.md). It covers importing, reading selected evidence,
checking a source and replaying a receipt. The [prospective pilot](pilots/local-document/v0.1.0/README.md) then tests
whether that workflow is worth continued work. The sections below are contributor setup and a broader command reference.

OpenARDP is built implementation-first through bounded, independently testable changes. The authoritative delivered
sequence and current outcomes live only in the [feature map](spec-kit/FEATURE_MAP.md); feature directories retain accepted
requirements, final evidence and normative contracts without duplicating the project status registry.

## 1. Read the authoritative rules

Read [AGENTS.md](AGENTS.md), [Constitution 3.0.0](.specify/memory/constitution.md), the
[feature map](spec-kit/FEATURE_MAP.md), [operating procedure](spec-kit/OPERATING_PROCEDURE.md), accepted
[ADRs](docs/adr/) and the durable active feature record required by its risk tier.

Version-suffixed v3.1 files are preserved adoption sources, not parallel authority. Removed transient feature planning is
recoverable from Git history; retained specifications and implementation notes are the durable merged record.

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
uv run python scripts/audit_maintainability.py
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
  --replay <receipt-sha256> --unit tokens --store .openardp --json
openardp visual-materialize <document-uuid> <projection-sha256> \
  --store .openardp --json
openardp visual-evidence <visual-evidence-sha256> --store .openardp --json
openardp watch /absolute/documents --store .openardp --once --stability-ms 0 --max-jobs-per-cycle 30 --json
openardp jobs --store .openardp --limit 50 --json
openardp storage-inventory --store .openardp --json
openardp storage-diagnostics --store .openardp --json
openardp workspace-backup --store .openardp --destination ../openardp-backup --json
openardp package-export --request ./synthetic-export-request.json \
  --destination ./evidence-package.zip --json
openardp package-verify --package ./evidence-package.zip --json
openardp package-import --package ./evidence-package.zip \
  --destination ./verified-snapshot --json
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

Feature 014 package operations are explicit trusted-operator commands and do not require
or modify a workspace. An export request declares the exact portable scope plus local
source paths for only those assets whose redistribution is affirmatively asserted. Paths
are consumed locally and never serialized. Verification and import remain offline;
successful SHA-256 verification establishes byte integrity, not authenticity, truth,
ownership, licensing or execution authority. The durable requirements and contract are in the
[F014 feature record](specs/014-export-interchange-experiment/spec.md).

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
HTTP transport, stable/universal export or Microsoft Graph access. The experimental
F014 BagIt profile is intentionally versioned and narrower than general BagIt. The
[005A–018 sequence](spec-kit/FEATURE_MAP.md) owns these
outcomes individually.

Public contracts remain experimental interoperability candidates. Feature 006 publishes
the first four provider-neutral evidence/native/trust roots; Feature 008 adds the
public `ContextBundle 0.2.0` and experimental `SelectionReceipt 0.1.0` roots. Later
examples under [`contracts/`](contracts/README.md) remain design guidance unless their
own feature promotes them to reviewed schemas. Feature 007 implements Docling while
preserving complete provider-native output.

## 6. Find durable evidence

- [Feature status and sequence](spec-kit/FEATURE_MAP.md)
- [Feature specifications and implementation notes](specs/README.md)
- [Architecture decisions](docs/adr/)
- [F018/F031 hygiene record](docs/17_CODEBASE_HYGIENE.md)
- [Validation record](VALIDATION.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

Do not rerun Spec Kit bootstrap during normal clone setup. Recovery and governance procedures are documented in the
[Spec Kit integration guide](docs/12_SPEC_KIT_INTEGRATION.md).
