# Spec Kit input — Isolated Docling adapter

**Feature directory:** `006-docling-adapter`  
**Maps to:** Work Package 5 in `docs/09_CODEX_EXECUTION_PLAN.md`

Use this document as the input to `$speckit-specify`. Read `AGENTS.md`, the constitution, relevant architecture docs and ADRs before creating the feature specification.

## User and outcome

Ingest synthetic PDF, DOCX and PPTX fixtures through a pinned Docling adapter while preserving parser-native output, core structure, warnings and provenance. The default profile must remain local and offline.

## Mandatory outcomes

- Docling is behind ParserAdapter and version-pinned.
- Parser executes in a constrained subprocess with timeout/resource controls.
- Native parser JSON is preserved alongside normalized blocks.
- PDF, DOCX and PPTX synthetic fixtures cover text, table and picture metadata.
- Parser crash or timeout creates a clean failed job.
- Repeated unchanged source skips conversion.
- No external model or network call occurs by default.

## Explicit non-goals

- No custom PDF or Office parser.
- No OCR/caption provider beyond parser-local capabilities.

## Specification requirements

- Express behavior as prioritized, independently testable user/operator stories.
- Include Given/When/Then acceptance scenarios, negative cases and relevant security cases.
- Define measurable success criteria without inventing unsupported performance targets.
- Preserve all project-level constraints; flag ambiguity rather than silently changing architecture.
- Require tests for every public contract, security boundary and persisted behavior introduced by this feature.
- Keep later work packages outside this feature even if their abstractions appear convenient.
