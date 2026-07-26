# Prior art and due-diligence register

**Status:** Living evidence register. It must be updated before material novelty, interoperability or adoption claims.

## Closest systems

### Docling

Provides multimodal document conversion, `DoclingDocument`, layout, tables, images, JSON/DCLX persistence, chunking, API and MCP access. OpenARDP must preserve native Docling output and add lifecycle/evidence behavior above it.

### ContextNest

Defines versioned, checksummed, addressable Markdown context, selector grammar, context packs, checkpoints and MCP integration. It is closer to governed curated knowledge and may include executable source-node instructions. OpenARDP differs by focusing on source-document evidence and default non-execution.

### Open Context Protocol / Universal Context Package / ctxpkg-style systems

Demonstrate that persistent context, invalidation, token-bounded packages, provenance and receipts are not novel in isolation. OpenARDP must differentiate through native multimodal source anchoring, derivation lifecycle and security semantics.

## Foundational standards to reuse

- W3C PROV for provenance mapping;
- W3C Web Annotation for selectors/anchors where appropriate;
- JSON Schema 2020-12 for structural validation;
- RFC 8785 for canonical JSON;
- RO-Crate, OCFL and BagIt as export/archive references;
- C2PA concepts for separating integrity, authenticity, trust and truth;
- MCP as an access protocol, not storage format.

## Claims discipline

Allowed:

- “We did not find an open profile covering this exact combination.”
- “OpenARDP tests whether this interoperability gap is real.”
- “The project integrates existing standards rather than replacing them.”

Disallowed without evidence:

- “first ever”;
- “universal standard”;
- “90% token savings”;
- “secure against prompt injection”;
- “better than Docling”;
- “lossless across all formats.”
