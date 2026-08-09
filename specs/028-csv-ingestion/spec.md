# Feature Specification: Stable CSV Ingestion

**Feature Branch**: `codex/f028-csv-ingestion`

**Created**: 2026-08-03

**Status**: Converged — see the [authoritative feature map](../../spec-kit/FEATURE_MAP.md)

## Clarifications

- CSV means UTF-8 or UTF-8-with-leading-signature, comma delimiter, double-quote escaping and strict malformed-quote
  rejection. LF, CRLF and CR physical line endings are accepted because the frozen publisher source uses LF.
- The first logical record is the header. Empty and duplicate header cells are preserved by position and never collapsed
  into a mapping.
- Each logical record becomes one canonical JSON-text table block. Data records retain an ordered list of
  `[header-or-null, value]` pairs, so short, wide, duplicate-header and empty-cell rows remain distinguishable and exact
  field-aware lexical queries can match one self-contained record.
- Exact original bytes remain the parser-native CAS artifact. The normalized record is a searchable evidence projection,
  not a replacement file or a claim that original quoting and line endings were reproduced.
- Formula-like cells are untrusted strings. OpenARDP neither evaluates nor exports them to a spreadsheet in this feature.
- The F025 corpus, questions, oracle and protocol remain byte-for-byte frozen. Historical F025 replay keeps its declared
  unsupported-CSV treatment; an explicit F028 evaluation profile enables the newly supported product path.

## User Stories

### US1 - Ingest CSV without logical body loss (P1)

As a local operator, I can ingest an explicit CSV source through the normal product command and later retrieve every
logical cell with exact order and source provenance.

**Independent test**: ingest synthetic CSV containing Unicode, quoted commas/newlines, empty and duplicate headers, empty
cells, short and wide rows; independently parse the stored native bytes and compare every normalized record.

### US2 - Bound malformed and hostile tables (P1)

As an operator, malformed or resource-amplifying CSV fails closed without source writes, network access, cell execution or
body-bearing diagnostics.

**Independent test**: exercise invalid UTF-8, NUL, malformed quotes, excessive fields/records/field or block size and
formula-like text through pure and isolated adapters.

### US3 - Retrieve frozen real-world CSV evidence (P1)

As an evaluator, I can answer the two locked KEV CSV questions from exact stable product evidence rather than a benchmark
probe or format conversion.

**Independent test**: ingest the redistributable CISA CSV twice in fresh workspaces, run Q15/Q16 direct and operator
treatments through F027, reverify selected blocks and prove atom/source/citation coverage with a body-free result.

## Functional Requirements

- **FR-001**: Add `text/csv` and `.csv` to the closed local source, parser, CLI and watcher allowlists.
- **FR-002**: Parse only verified CAS bytes in the existing killable, network-denied standard-library worker.
- **FR-003**: Decode incrementally as strict UTF-8, accept at most one leading UTF-8 signature and reject NUL.
- **FR-004**: Use an explicit comma/double-quote profile with strict malformed CSV rejection; do not sniff locale,
  delimiter, encoding or spreadsheet dialect.
- **FR-005**: Treat the first logical record as the header and preserve header order, duplicates and empty names.
- **FR-006**: Preserve every subsequent logical cell exactly as decoded and by position, including empty, missing and
  overflow cells, without dict coercion, type inference, formula evaluation or whitespace normalization.
- **FR-007**: Emit one deterministic `table` block per logical record using canonical JSON text and contiguous source
  order.
- **FR-008**: Record exact inclusive physical line ranges even when one quoted record spans several lines.
- **FR-009**: CSV blocks MUST use `openardp-csv-v1` extraction and a namespaced CSV provenance extension while retaining
  the internal line-range projection required by persisted representation validation.
- **FR-010**: The exact source object remains the lossless native artifact and MUST independently reconstruct every
  logical record; normalized blocks never replace or mutate it.
- **FR-011**: Enforce existing source, line and block bounds plus explicit field-count, field-length and normalized-record
  limits before publication.
- **FR-012**: Parser errors MUST be typed, stable, sanitized and free of rejected cell content.
- **FR-013**: CSV MUST use a distinct `openardp-csv` recipe containing its media/profile and every behavior-affecting
  limit; it MUST NOT change the historical `openardp-text` recipe.
- **FR-014**: Existing TXT/Markdown behavior, representation identifiers and replay MUST remain byte-identical.
- **FR-015**: Search and context discovery MUST index the canonical CSV record text and reverify it from CAS before use.
- **FR-016**: The CLI and watcher MUST route CSV through ordinary text ingestion without Docling or optional model assets.
- **FR-017**: Evaluate Q15/Q16 through stable exact lexical search against unchanged F025 fixtures in two fresh F028
  workspaces and retain honest direct and operator outcomes; general context retrieval remains F029.
- **FR-018**: The F028 result MUST contain no source bodies, host paths, secrets or post-hoc oracle-driven query changes.
- **FR-019**: Historical F025 reference validation MUST remain green without rewriting its locked protocol or results.
- **FR-020**: F029 semantic/multilingual providers, translation, stemming, fuzzy matching, embeddings and rerankers are
  excluded.
- **FR-021**: Full repository gates and Spec-Kit convergence MUST pass before merge.

## Edge Cases

- Empty file, BOM-only file, header-only file and a blank header record.
- Quoted commas, escaped quotes, embedded LF/CRLF, Unicode and no trailing newline.
- Duplicate/empty header cells, short rows, extra cells, empty records and cells containing leading `=`, `+`, `-` or `@`.
- Malformed/unclosed quoting, invalid UTF-8, NUL and limit overflow split across arbitrary input chunks.
- Repeated unchanged ingestion, source removal after commit and byte-identical cells expressed with different source
  quoting or line endings.

## Success Criteria

- **SC-001**: Synthetic losslessness tests compare 100% of logical headers/cells from native bytes with normalized blocks.
- **SC-002**: The 932,085-byte frozen CISA source ingests through the stable product path with all 1,656 logical records,
  exact source SHA-256 and zero network attempts.
- **SC-003**: Q15/Q16 operator treatment retrieves every required atom from the required CSV source with 100% citation
  integrity; direct outcomes are reported without threshold relaxation.
- **SC-004**: Two fresh F028 result projections are byte-identical and independently validate.
- **SC-005**: Malformed/resource-limit/security cases cause no ready representation, source mutation or body leakage.
- **SC-006**: F025 replay and all TXT/Markdown parser tests remain green.
- **SC-007**: The full repository retains at least 85% coverage and all Linux/macOS/Windows checks pass.

## Compatibility

This is an additive media type and a distinct derived-recipe identity. It changes no source identity, CAS/catalog schema,
public JSON Schema, block identity algorithm, cloud default or persisted compatibility guarantee. Existing representations
remain queryable under their recorded recipes.
