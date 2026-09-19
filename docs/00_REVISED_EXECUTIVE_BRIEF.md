# Revised executive brief

**Status:** Current strategy supplement. For delivered behavior, use the repository
[README](../README.md); for execution order, use the canonical [feature map](../spec-kit/FEATURE_MAP.md).

## Current decision: bounded practical validation

The delivered foundation is substantial; evidence of recurring human value is still missing. F037 corrected the actual
MCP preparation lifetime and cumulative provider-cache exhaustion. F038 makes one local document workflow readable and
prepares a [fair manual pilot](../specs/038-local-document-pilot-readiness/contracts/pilot-protocol.md).

Pause wider platform expansion. Continue only with the existing workflow, necessary maintenance and the bounded pilot:
at most 20 additional person-hours and ten working days, with setup/checking/repair included, strong baselines and human
supporting-passage judgments. A confirmed limited-GO justifies a further bounded slice; otherwise pause expansion.
The current state is pilot preparation, not demonstrated time savings, external adoption or a release GO.

## Problem

AI agents repeatedly parse, chunk and reinterpret the same source documents. Existing document-intelligence engines already solve much of the parsing problem, but downstream systems still lack a consistent operational lifecycle for:

- logical source identity versus immutable source versions;
- parser-native representations and provider-neutral evidence references;
- reproducible derived artifacts and invalidation;
- untrusted-source handling and data/instruction separation;
- bounded context selection with traceable omissions;
- exact escalation back to original text, tables, images or page regions.

## Product thesis

**Compress access, not truth.**

Original sources remain authoritative. Native parser representations remain intact. OpenARDP manages durable identity, evidence projections, derived-artifact lifecycle and task-specific context delivery without pretending that a summary or embedding is the source of truth.

## Product first, specification later

OpenARDP must first prove value as useful software. Public contracts should be stable enough to test across languages and implementations, but are labelled experimental until external adoption exists.

## Planned success definition for v0.1

A future v0.1 should allow a developer to locally:

1. initialize a workspace;
2. ingest TXT/MD and PDF/DOCX/PPTX;
3. reuse unchanged native parse results;
4. retrieve exact source-backed evidence;
5. compile a bounded context bundle with a selection receipt;
6. access the prepared corpus through a read-only MCP server;
7. verify provenance, trust labels and freshness;
8. reproduce benchmark results against fair Docling baselines.

This list originated at F005A. The delivered implementation now includes the local ingestion, evidence, context/MCP
and operational foundations recorded in the [feature map](../spec-kit/FEATURE_MAP.md). Delivery of those mechanisms does
not itself satisfy the current practical-value test, and the separate release decision remains NO-GO.
