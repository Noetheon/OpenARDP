# Contract: Docling Native Adapter Boundary

## Status

Internal provider adapter and persistence contract for F007. Public interchange remains
the unchanged F006 experimental evidence family `0.1.0`.

## Rich parser port

The provider-neutral port exposes:

```text
recipe -> exact immutable rich parser recipe
supports(media_type) -> bool
parse(chunks, media_type) -> RichParseOutput
resolve(native_json, provider_pointer) -> bounded safe JSON
```

The port accepts source bytes, not paths or URLs. The returned value contains bytes and
provider-neutral candidates, not Docling runtime objects. All public failures inherit
the existing sanitized parser boundary.

## Supported media

| Media type | Provider input | Local assets |
|---|---|---|
| `application/pdf` | in-memory `.pdf` stream | validated model bundle required |
| DOCX MIME | in-memory `.docx` stream | none |
| PPTX MIME | in-memory `.pptx` stream | none |

Any other media fails before provider import.

## Worker protocol

Parent-to-child messages:

1. strict configuration containing media, source identity, safe synthetic name, limits
   and optional validated model-root path;
2. bounded byte chunks;
3. one end marker.

Child-to-parent result:

- `ok` plus one strict serialized `RichParseOutput`; or
- `error` plus one allowlisted machine code.

The protocol never transmits traceback, source path, model path, document text in an
error, provider object, exception instance or arbitrary pickled class. IPC is closed and
the process is joined/terminated/killed on every exit.

## Error taxonomy

| Category | Meaning |
|---|---|
| `rich_dependency_unavailable` | optional provider extra absent or wrong version |
| `unsupported_rich_media` | media not in F007 allowlist |
| `model_assets_required` | PDF profile has no local reviewed bundle |
| `model_assets_invalid` | manifest/root file, path, length, digest or license drift |
| `malformed_document` | provider rejects source structure |
| `partial_conversion` | provider returns partial rather than complete success |
| `parser_timeout` | elapsed deadline exceeded |
| `parser_cancelled` | parent interruption/cancellation |
| `parser_crashed` | child exits or provider fails unexpectedly |
| `network_denied` | provider attempts socket use |
| `resource_limit` | worker CPU/memory/descriptor/page/source bound |
| `native_output_limit` | complete JSON exceeds configured bound |
| `projection_limit` | candidate count exceeds configured bound |
| `retrieval_limit` | per-body or aggregate retrieval bytes exceed bounds |
| `invalid_rich_output` | strict output/domain/evidence validation fails |
| `rich_integrity_error` | persisted cache/bundle/object disagreement |
| `rich_storage_error` | atomic publication/commit fails |
| `pointer_invalid` | malformed, wrong-profile or unsafe pointer |
| `pointer_missing` | valid pointer has no target in exact native JSON |

Messages remain generic and body/path-free.

## Native export profile

`openardp-docling-document-json-v1`:

- accepts only a complete successful conversion;
- exports the complete `DoclingDocument` value with JSON aliases and explicit nulls;
- encodes only an out-of-I-JSON-range `origin.binary_hash` as its exact decimal string
  and rejects every other unsafe numeric value;
- preserves provider arrays, references, provenance, tables, pictures, pages and
  metadata;
- uses no provider coordinate/confidence rounding;
- validates safe JSON and serializes with RFC 8785;
- uses a synthetic source name derived from media type and source digest prefix;
- excludes conversion timing, host/platform facts, exception text and local input path.

## Evidence projection profile

`openardp-docling-evidence-v1`:

- deterministic collection and array order;
- deterministic Unicode text view with `\n` between text/heading entries;
- labels `title`, `section_header` and `heading` project as heading evidence;
- other non-empty text entries project as text evidence;
- table cells project in table order then row/column order;
- picture/page provenance converts to fixed-point normalized top-left regions only after
  finite/bounds/origin validation;
- reviewed unprojected nodes may receive an opaque `#/...` JSON reference;
- unknown labels remain only in native JSON and may emit a body-free warning;
- no semantic equivalence is claimed outside this Docling profile/version.

## Pointer grammar

F007 resolves only JSON references emitted by the adapter:

```text
#/<escaped-segment>/<escaped-segment>/...
```

Segments use RFC 6901 `~0` and `~1` escapes. Empty segments, URI schemes, relative path
tokens, control characters, leading values other than `#/`, excessive depth and
excessive length are rejected. Resolution traverses already parsed JSON dictionaries and
arrays only, under depth/value-size limits, and returns a copied safe JSON value.

## Atomic rich commit

Inputs:

- existing fenced representation acquisition;
- exact source and base manifest objects;
- descriptor/native/native-record/bundle objects;
- complete ordered evidence record objects;
- source observation and ready time.

Transaction verifies:

- lease owner/token/revision or reviewed force path;
- source/version/recipe/scope consistency;
- all object IDs and immutable lengths;
- canonical bundle/record inventories;
- contiguous ordinals and unique IDs;
- no prior conflicting rich facts;
- head/event update semantics.

Only then does it insert the canonical attempt/evidence rows, set the base
representation READY, bind its accepted attempt, update the head and append the
successful ingest event.

## Forced-reparse attempt

A forced reparse first verifies the accepted READY aggregate, then parses and validates a
complete candidate attempt. In one transaction it:

1. inserts an immutable `CONVERGED` or `DIVERGED` attempt and all its evidence rows;
2. verifies every attempt object and source/recipe scope;
3. appends a truthful parser-invoked event;
4. leaves the accepted-attempt link and current representation scope unchanged.

`DIVERGED` is a parse-attempt outcome, not a new public ingestion disposition. The
bounded result reports it explicitly. No differing provider output is silently selected
as current.

## Cache verification

Before `CACHE_HIT`, load one catalog snapshot and:

1. verify source, base manifest and every rich object in CAS;
2. parse strict descriptor, native record, bundle, references and projections;
3. require canonical bytes for every structured record;
4. verify native JSON is safe and matches descriptor/native record;
5. verify evidence aggregate with caller-pinned source version;
6. verify catalog rows equal bundle inventory;
7. verify every retrieval digest/length and parent/ordinal relation.

Any discrepancy fails as `rich_integrity_error`; the parser is not invoked and no head
event is written.

## Compatibility

- F002/F005 public schemas and F006 schemas/vectors remain byte-identical.
- Existing text rows have no rich extension row and load unchanged.
- Migration 5 is additive, transactional and checksummed.
- A workspace at revision 5 cannot be opened by older software; rollback requires
  restoring a revision-4 backup or reverting before opening/migration. Because migration
  is additive and no rich rows exist before F007 use, a documented export/backup is the
  safe rollback boundary.
- Provider profile changes create new representation identities and never reinterpret
  an existing READY rich aggregate.
