# Feature 007 — Docling native adapter

## Goal
Ingest local PDF, DOCX and PPTX through Docling, preserve the complete provider-native representation immutably and emit the Feature-006 thin evidence contracts.

## Scope
- Provider-neutral rich-parser port and Docling adapter with locked compatible version.
- Spawned bounded worker with denied sockets where supported; document that this is not a universal strong sandbox.
- Descriptor with provider/version/config digest/media type/CAS digest and reproducibility metadata.
- Contract-conformant text, heading, table, picture/page and opaque native pointers.
- Cache reuse, cancellation, idempotency and CLI behavior.

## Non-scope
No custom Office/PDF parser, second rich-document IR, semantic search, context compiler, MCP or unreviewed model service.

## Tests
Synthetic licensed fixtures; unchanged ingest avoids parser invocation; changed bytes create immutable version; native and projection integrity; timeout/crash/cancel/disk-full cleanup; malformed files; denied network; pointer resolution; supported OS matrix. Record parser nondeterminism where byte-identical native serialization cannot be guaranteed.
