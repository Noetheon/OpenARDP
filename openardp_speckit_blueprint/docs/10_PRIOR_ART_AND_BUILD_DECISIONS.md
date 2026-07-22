# Prior art and build decisions

## Docling

Use as the default rich parser candidate. It supports many formats, structured/lossless output, layout, tables, images,
OCR, chart understanding, local execution, API service and MCP integration. Docling MCP already provides conversion and
caching. OpenARDP should therefore integrate rather than duplicate it.

Gap relative to OpenARDP scope: a general durable package contract, logical/version/block identity, dependency-aware derived
cache invalidation, evidence policies, portable export and enterprise source reconciliation are not the same as conversion.

## MinerU and MinerU Document Explorer

MinerU targets high-quality complex document parsing and provides rich output. MinerU Document Explorer already combines
PDF/DOCX/PPTX indexing, BM25/vector/reranking and MCP deep-reading tools. It is the closest current overlap and must be
benchmarked before investing heavily.

OpenARDP differentiator should not be “MCP document search.” It must prove stronger reproducibility, versioned provenance,
portable packages, incremental derivation reuse, explicit source/derived trust and enterprise synchronization.

Review MinerU's custom core license and every model license before redistribution or enterprise use.

## MarkItDown

Useful lightweight adapter for token-efficient Markdown and broad file support. It is not a high-fidelity canonical document
model and should not be the only source for table/layout/visual evidence. Its security guidance also reinforces that it
operates with process privileges and inputs must be constrained.

## MCP

MCP is the agent integration protocol, not the document schema. Keep OpenARDP business logic independently callable. Pin the
stable SDK major version; the ecosystem was transitioning from v1 to v2 in mid-2026.

## RO-Crate, JSON-LD and W3C PROV

RO-Crate demonstrates a practical package plus JSON-LD metadata pattern. W3C PROV provides provenance concepts. Use these as
alignment targets and consider an OpenARDP RO-Crate profile after the core model has real users. Do not force full linked-data
complexity into the local MVP.

## Microsoft Graph and Open XML

Open XML enables native Office inspection and later part-level hashing. Microsoft Graph provides drive items, change
notifications and delta synchronization for OneDrive/SharePoint. The enterprise connector should use both notifications and
delta reconciliation, not assume save-event semantics.

## Decision summary

| Capability | Build | Reuse |
|---|---|---|
| PDF/Office parsing | adapter only | Docling default; alternatives benchmarked |
| Durable IR/package | yes | align with JSON Schema/RO-Crate/PROV |
| Content-addressed store | yes, small | standard SHA-256/filesystem patterns |
| Lexical search | integration | SQLite FTS5 |
| Vector search | provider adapter | optional existing engine |
| MCP protocol | integration | official SDK |
| Context compiler | yes | project differentiator |
| Incremental derivation DAG | yes | project differentiator |
| OneDrive/SharePoint source sync | adapter | Microsoft Graph |
| Office rendering/editing | not MVP | evaluate Open XML/Pandoc/Quarto later |
