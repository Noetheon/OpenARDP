# Research: Text Ingestion Vertical Slice

**Date**: 2026-07-22

**Scope**: Resolve F004 parser, source-snapshot, representation, cache, workspace and CLI decisions before design. The
research combines the repository's accepted architecture with independent parser/persistence reviews and official Python
and SQLite documentation. Runtime behavior remains local and network-free.

## Decision 1 — The built-in text adapter is narrow, deterministic and streaming

**Decision**: Add a provider-neutral `ParserAdapter` port and one standard-library adapter named `openardp-text`, version
`1`, profile `default`. It accepts verified byte chunks, decodes UTF-8 incrementally with strict errors, accepts one leading
UTF-8 BOM as a signature, rejects NUL, limits total bytes/line length/block count and emits pure candidate records.

TXT recognizes blank-line-delimited paragraphs. Markdown recognizes only:

- ATX and setext headings;
- blank-line-delimited paragraphs;
- fenced code blocks using matching backtick or tilde fences;
- unordered/ordered list items grouped under a list block;
- block quotes.

Inline Markdown, HTML execution, tables, link fetching and CommonMark-conformance claims are excluded. Syntax-like text
inside a code fence remains code. Source decoding preserves Unicode code points without normalization.

**Rationale**: F004 must prove the parser port and cache boundary without importing Docling or a broad Markdown framework.
Incremental UTF-8 decoding is equivalent to decoding joined chunks while bounding chunk memory. A reviewed subset is more
honest and testable than accidental partial CommonMark behavior.

The default composition wraps the pure adapter in a spawned worker process. The parent streams byte chunks through a
bounded IPC protocol, supplies no source path, disables socket creation in the worker and terminates it at a 30-second
deadline. Input/line/block limits bound portable resource use; POSIX resource limits are additional defense in depth where
available. Parser crash, timeout and malformed worker output become sanitized failures. Direct in-process construction is
reserved for deterministic unit tests of the pure adapter, not the product ingestion path.

**Native artifact**: For TXT/Markdown, the exact source CAS object is also the parser-native lossless artifact. Creating a
second JSON copy would add storage and an atomicity surface without preserving more information. Normalized block records
are separate derived/canonical representation objects.

**Primary source**: [Python 3.12 codecs](https://docs.python.org/3.12/library/codecs.html).

## Decision 2 — Provenance is exact one-based line evidence

**Decision**: Every candidate records inclusive `line_start` and `line_end`. The resulting F002 `ContentBlock.source`
contains `extraction_method="openardp-text-v1"` and namespaced extension data:

```json
{
  "openardp.text": {
    "line_start": 4,
    "line_end": 6
  }
}
```

Markdown structural markers may be omitted from normalized text, but the exact source bytes remain in CAS and the line
range always identifies the evidence that produced the block. CRLF and CR source endings are recognized as line breaks;
normalized block text uses `\n`. An accepted leading BOM is excluded from first-block text but remains in the original.

Sibling `order` starts at zero within each parent. A separate global ordinal preserves document reading order. Heading
parents use the nearest preceding lower-level heading; non-heading blocks use the active heading, and skipped levels do
not create invented placeholder blocks. Empty/whitespace-only input validly produces zero blocks.

**Rationale**: The existing public `SourceLocator` deliberately supports extensions, so no F002 schema change is needed.
Line evidence is sufficient for plain text while future rich adapters retain page/slide/bounding-box fields.

## Decision 3 — F004 block handles are deterministic SHA-256-derived UUIDv8 values

**Decision**: Derive a block handle from a versioned domain string and RFC 8785 payload containing document identity,
structural path, kind, canonical content hash, source line range and same-parent occurrence. The representation identity is
deliberately excluded so unchanged source-backed structure can retain its logical handle across recipe changes. Hash
with SHA-256, take 128 bits and set RFC variant plus UUID version 8 bits.

The F002 `canonical_hash` remains the authoritative SHA-256 content identity. The UUID is only a stable opaque block
handle. Equivalent forced parsing reproduces it. Unchanged blocks may also retain it across source versions when their
structural path/content/range remain equal, but F004 makes no reconciliation or cross-version-reuse claim; F010 owns that
larger policy.

**Rationale**: Random IDs make `--force` unable to converge safely. UUIDv5 would introduce SHA-1 despite the repository's
SHA-256 identity posture. Page numbers or mutable filenames are not embedded. The complete algorithm and golden vectors
are contract-tested so a later change requires explicit compatibility review.

**Rejected alternatives**:

- Random UUID per parse: divergent forced output.
- `representation_id + ordinal` only: every source edit changes all handles and duplicate insertion shifts unrelated IDs.
- Canonical content hash as `block_id`: duplicates are legitimate and a content hash is not a logical handle.

## Decision 4 — Snapshot an explicitly authorized regular source, then parse CAS only

**Decision**: The local source adapter accepts `.txt`, `.md` and `.markdown` (case-insensitive), validates content as text,
rejects path control characters, links/junctions and non-regular files, and opens read-only with non-following flags where
available. It compares path and descriptor identity, size and modification time before/after streaming. Sources are
limited to 100 MiB, lines to 1 MiB and normalized blocks to 100,000.

The open descriptor is streamed once into the F003 CAS. Parser input then comes exclusively from that verified immutable
object. A mid-snapshot replacement/change fails before document-version/representation commit and may leave only a complete
unreferenced object. Atime is not an immutability claim because ordinary reads may update it; the application never writes,
renames, chmods or truncates the source.

**Rationale**: Parsing a live path after hashing creates a hash/content race. Parsing the persisted snapshot pins parser
input to the exact version identity. `os.fstat` and non-following facilities provide the strongest practical standard-
library boundary; an actively malicious same-user process and network/shared filesystems remain outside the claim.

**Primary source**: [Python 3.12 os](https://docs.python.org/3.12/library/os.html).

## Decision 5 — Append one checksummed representation migration

**Decision**: Preserve migrations 1 and 2 byte-for-byte and append revision 3 with four purpose-specific tables:

1. `document_representations`: immutable recipe/scope plus fenced `STAGING`/`FAILED` work or complete `READY` artifact
   references;
2. `representation_blocks`: ordered projection and one CAS object per F002 block;
3. `document_heads`: mutable current successful observation protected from time regression;
4. `ingestion_events`: append-only `COMMITTED`, `CACHE_HIT`, `FORCED_REPARSE` or `CONVERGED` evidence without bodies.

Manifest and native artifacts are mandatory singleton columns. Blocks each reference one exact block object. A speculative
generic artifact graph is deferred until F006 introduces assets and a second real use case.

`STAGING` uses owner, SHA-256 lease-token hash, revision and strict expiry. Acquisition yields `CLAIMED`, `READY` or `BUSY`;
expired/failed work can be fenced and retried. The parser runs outside SQLite transactions. A ready commit registers object
metadata, inserts every block, transitions the header last, advances the document head when the observation is not older,
and appends its event in one `BEGIN IMMEDIATE` transaction.

**Rationale**: READY-only insert races allow duplicate initial parser work. Fenced staging prevents that without holding a
database write lock during parsing. Visible staging is explicitly incomplete and never queryable as content.

## Decision 6 — A document head is necessary for correct A → B → A behavior

**Decision**: `document_heads` points to the latest successfully observed representation and records
`source_observed_at`, `last_ingested_at`, revision and last disposition. A strictly older overlapping observation may
commit historical immutable data but cannot replace a newer head. Equal timestamp plus a different scope is a conflict.

**Rationale**: F003 source versions are immutable and retain first-commit timestamps. Selecting `MAX(committed_at)` fails
when a file changes from A to B and later reverts to the already known A. A head is an operational projection, not a
mutation of historical evidence.

An already known source version is reused without recommitting changed file metadata; current observed metadata belongs to
the head/event. This preserves F003's immutable `source_modified_at` contract.

## Decision 7 — Cache hits require complete physical and semantic verification

**Decision**: A matching READY row is only a cache candidate. The ingestion/query service verifies manifest, native and
every selected block CAS object, strictly deserializes F002 records and cross-checks scope, recipe, object IDs, block count,
ordinals, hierarchy, line provenance and canonical hashes. Only then may it append `CACHE_HIT`, advance the head and return
without invoking the parser.

Corrupt or missing READY artifacts raise an integrity error. F004 does not silently reparse to conceal evidence loss and
never falls back to the current source path for `outline` or `get`.

**Rationale**: Catalog state alone cannot prove CAS availability/integrity. F004 input is bounded, so full verification is
the correct baseline; any later verification cache must be explicit and cannot weaken this guarantee silently.

## Decision 8 — The CLI uses `argparse` and one stable envelope

**Decision**: Add no runtime dependency. The installable `openardp` console command uses `argparse` subcommands and accepts
`--store` and `--json` on every command. The default store is exactly `.openardp` below the current directory; no upward
discovery occurs.

JSON success:

```json
{"command":"list","data":[],"ok":true,"schema_version":"0.1.0"}
```

JSON failure:

```json
{"command":"ingest","error":{"code":"invalid_source","message":"source is invalid"},"ok":false,"schema_version":"0.1.0"}
```

JSON is UTF-8, sorted and compact, with exactly one envelope on stdout. Diagnostics/help use stderr as appropriate. Exit
codes are stable: `0` success, `2` usage, `3` not found, `4` rejected input, `5` conflict/busy, `6` integrity/workspace and
`1` unexpected sanitized failure. Non-`get` results never include full block bodies.

**Rationale**: `argparse` provides reviewed subcommand/help/usage behavior in Python 3.12. A framework dependency is not
justified by six commands. JSON-mode argument errors are caught and rendered through the same envelope.

**Primary source**: [Python 3.12 argparse](https://docs.python.org/3.12/library/argparse.html).

## Decision 9 — Workspace initialization is explicit and atomically marked

**Decision**: A workspace contains `catalog.sqlite3`, the F003 CAS directories and `.openardp-workspace.json`. `init`
creates/validates the CAS and migrates the catalog, then atomically writes a fixed version-1 marker with `tempfile` plus
`os.replace`, file sync and directory sync where supported. A compatible marked workspace initializes idempotently.

Read/ingest commands require the marker and current catalog revision. They never initialize implicitly. Foreign entries,
malformed/newer markers and incompatible catalogs fail without repair. Restrictive POSIX modes are applied best-effort;
they are defense in depth, not a cross-platform authorization claim.

## Decision 10 — Keep F004 isolated from later work packages

No FTS table, search command, Docling dependency, reconciliation graph, watcher, MCP, HTTP, embedding/provider, asset
generalization or portable package enters this migration. A F004 READY representation has zero required indexes because
F005 is not installed; F005 will add index readiness without retroactively weakening F004's artifact completeness.

## Rejected aggregate alternatives

- Store block bodies in SQLite: duplicates CAS and broadens leakage/backup surface.
- Store only one `blocks.jsonl` object: `get`/outline must read and verify unrelated bodies.
- Hold a SQLite write transaction while parsing: unnecessary long writer exclusion.
- Use mtime/size as cache identity: violates exact SHA-256 reuse.
- Choose current version by maximum immutable timestamp: incorrect after reversion.
- Reuse F003 terminal jobs as representation state: terminal jobs cannot express retryable representation ownership cleanly.
- Automatically delete CAS orphans after rollback: unsafe with deduplication and outside retention policy.
- Add Typer/Click or a Markdown framework: no demonstrated need for another runtime dependency in this bounded slice.
