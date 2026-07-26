# Vision and positioning

**Status:** Active positioning policy adopted by Feature 005A. Delivered behavior remains enumerated in the
[README](../README.md).

## Vision

Make prepared document evidence reusable across agent tasks, models and tools without reparsing sources, losing provenance or turning untrusted document content into instructions.

## Positioning sentence

OpenARDP is an implementation-first, local-first open-source reference platform for evidence lifecycle and context
delivery above document-intelligence engines such as Docling.

## Layer boundaries

| Layer | Responsibility |
|---|---|
| Source systems | Authoritative files and permissions |
| Docling/other parsers | Rich native document understanding |
| OpenARDP | Identity, versioning, CAS, evidence projection, derivations, trust, retrieval, context compilation |
| MCP/HTTP/Python | Access transport |
| Agent host/model | Planning, reasoning and task execution |

## Competitive coexistence

- **Docling:** use, do not replace.
- **ContextNest:** curated knowledge/instructions; OpenARDP focuses on source evidence and non-executable document data.
- **OCP/UCP/context packages:** generic or workflow-oriented context packaging; OpenARDP specializes in native multimodal document evidence and exact source anchoring.
- **W3C PROV/Web Annotation:** map to and reuse where suitable.
- **RO-Crate/OCFL/BagIt:** evaluate for export/archive profiles rather than reimplementing blindly.

## Long-term possibility

If multiple independent implementations need the same evidence contracts, extract a neutral specification. Until then, contracts remain part of the open-source project and evolve through implementation evidence.
