# Feature Specification: Product Benchmark Correctness

**Feature Branch**: `codex/f033-product-benchmark-correctness`

**Created**: 2026-08-09

**Status**: Accepted

**Governance Tier**: high-assurance

**Input**: Correct the F020 measurement harness before independent holdout or retrieval optimization.

## User Scenarios & Testing

### User Story 1 - Complete rich-format measurement (Priority: P1)

A maintainer can supply one valid offline PDF model bundle and measure PDF, DOCX and PPTX in the same reference or full
run. Model configuration for PDF must not make the Office workloads unavailable.

**Why this priority**: Mutually exclusive format results invalidate the rich-format comparison and the derived completeness
decision.

**Independent Test**: Exercise the rich-workload preparation boundary with all three frozen fixtures and prove that only
the PDF parser receives model assets while every format remains runnable.

**Acceptance Scenarios**:

1. **Given** valid paired PDF model inputs, **when** rich workloads are prepared, **then** PDF uses the validated bundle and
   DOCX/PPTX use model-free parser configurations.
2. **Given** no PDF model inputs, **when** rich workloads are prepared, **then** DOCX/PPTX remain runnable and PDF retains
   the existing explicit capability-unavailable behavior.

---

### User Story 2 - Fail before expensive phases (Priority: P1)

A maintainer receives an immediate stable failure when PDF model assets or rich fixture integrity are invalid, before the
text or scale phases consume significant time.

**Why this priority**: A late failure can waste nearly a full benchmark run and produce no valid evidence.

**Independent Test**: Replace the text phase with a sentinel and prove invalid rich configuration fails before the sentinel
is entered and before any result directory is published.

**Acceptance Scenarios**:

1. **Given** invalid PDF model assets, **when** a reference or full run starts, **then** it fails during preflight before any
   text workload begins.
2. **Given** a smoke or scale-only run, **when** no rich workload is selected, **then** no rich preflight is required.

---

### User Story 3 - Preserve a body-free command boundary (Priority: P1)

A maintainer invoking the benchmark CLI sees only the stable `benchmark_execution_failed` category for public parser
domain failures; no traceback, absolute path, username or document content is emitted.

**Why this priority**: Parser failures cross an untrusted-data boundary and must not leak sensitive local context.

**Independent Test**: Force a parser-domain failure containing secret-like path/body text and assert the command exit code,
stdout and stderr remain closed and body-free.

**Acceptance Scenarios**:

1. **Given** any public parser-domain failure, **when** the CLI handles it, **then** it exits with code 6 and emits only
   `benchmark_execution_failed` on stdout.
2. **Given** the same failure, **when** diagnostic logging is enabled, **then** only its safe exception class is available
   to internal logging and raw exception text is excluded.

### Edge Cases

- Only one of PDF model root or manifest is supplied: retain argument rejection before execution.
- A fixture changes after preflight: the execution-time digest check still fails closed.
- PDF model inputs are supplied to a profile without rich workloads: they do not trigger unnecessary bundle validation.
- Preflight fails after an output parent exists: no staging, work or published result directory remains.

## Requirements

### Functional Requirements

- **FR-001**: The harness MUST use format-bound rich parser configurations so PDF model assets are supplied only to PDF.
- **FR-002**: Reference and full runs MUST validate selected rich fixtures and parser configurations before text workloads.
- **FR-003**: The rich execution phase MUST reuse the preflighted parser instances rather than constructing conflicting
  configurations later.
- **FR-004**: Missing PDF model assets MUST remain an explicit unavailable PDF observation without suppressing Office
  measurements.
- **FR-005**: The CLI MUST explicitly catch the public parser error hierarchy and map it to
  `benchmark_execution_failed` with exit code 6.
- **FR-006**: CLI output and internal diagnostic data MUST exclude raw exception text, source bodies and local paths.
- **FR-007**: Existing F020 corpus, thresholds, value policy, evidence files and validator semantics MUST remain unchanged.

### Non-Goals and Compatibility Impact

- **Non-goal**: Add an independent holdout, new retrieval algorithm, provider, answer generator or latency optimization.
- **Non-goal**: Regenerate historical F020 result evidence as part of this correction.
- **Compatibility impact**: Corrective only. No schema, application, workspace, provider-profile or export-profile version
  changes. Existing successful commands and published evidence remain valid.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Automated tests prove all three rich formats are assigned runnable, non-conflicting parser configurations in
  one preflight when valid PDF assets are present.
- **SC-002**: Invalid rich configuration prevents the first text-profile call and leaves no published or temporary benchmark
  directories.
- **SC-003**: Every public parser-domain subclass produces exit code 6, exactly one stable stdout category and empty stderr
  in the maintained CLI contract test.
- **SC-004**: All focused F020 tests and complete repository quality gates pass without changing benchmark policy inputs or
  lowering any gate.

## Assumptions

- The existing `ParserError` base class is the public closed parser-domain hierarchy.
- The existing PDF model-root contract continues to mean the manifest-bound assets directory.
- Fixture SHA-256 values in the frozen F020 corpus remain authoritative.
