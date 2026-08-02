# Feature 024 prompt — Redistributable real-world corpus

## Authoritative request

Add a licensed, realistic and independently reproducible multi-format corpus that can exercise the delivered OpenARDP
ingestion/evidence path offline and can be redistributed with the repository without relying on synthetic fixtures.

## Frozen scope

- Include one genuine PDF, DOCX, PPTX, CSV, Markdown and plain-text source from authoritative public-sector publishers.
- Retain exact source bytes, immutable or drift-detecting source references, SHA-256, byte lengths, authorship,
  publication metadata, rights evidence, required notices and non-endorsement limitations.
- Treat every corpus document as untrusted data; fetching is explicit, verification is offline and ordinary tests never
  use the network.
- Provide an independent closed-tree validator and a reproducible parser/evidence baseline for all six formats,
  including PDF through the validated F023 offline model bundle.
- Preserve unfavorable parse, provenance, resource and reproducibility evidence.
- Semantic question answering, retrieval ranking and source-quality scoring remain exclusively Feature 025.

## Completion boundary

Complete the full Spec Kit lifecycle, tests-first implementation, actual corpus reproduction and six-format offline
baseline, independent validation, full local gates, one private pull request and green Linux/macOS/Windows CI before
starting Feature 025.
