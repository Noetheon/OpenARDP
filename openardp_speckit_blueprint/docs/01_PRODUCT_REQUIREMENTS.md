# Product requirements document

## 1. Problem statement

Knowledge workers and coding agents repeatedly pay the perception cost of the same documents. Parsing, OCR, layout
analysis, image interpretation, chunking and context construction happen again even when a file has not changed. The
result is avoidable latency, model usage, duplicated derived data and inconsistent interpretations.

## 2. Primary users

### Local technical user

Uses Codex/ChatGPT/another agent with local project documents and wants faster repeat tasks without uploading everything
again.

### Team knowledge worker

Works normally in Word and PowerPoint. Expects background preparation without learning a new authoring tool.

### Platform engineer

Needs a controlled service for SharePoint/OneDrive document libraries with inherited permissions, observability and audit.

### Open-source integrator

Wants to add a parser, storage backend, model provider or agent client without forking the core.

## 3. Jobs to be done

- Prepare a document once and reuse the result.
- Know whether prepared data matches the current source version.
- Find exact passages, tables and figures quickly.
- Ask for the smallest sufficient context for a task.
- Escalate to original visual evidence when necessary.
- Understand how every derived statement was produced.
- Rebuild only what became stale.
- Run locally or in an air-gapped environment.

## 4. Functional requirements

### FR-1 Ingestion

- Accept local files in MVP; PDF, DOCX, PPTX, TXT and MD are priority formats.
- Detect media type by content where practical, not extension alone.
- Record source size, SHA-256, timestamps, parser profile and ingestion result.
- Never modify the source file.

### FR-2 Durable identity

- Maintain a stable `document_id` across versions.
- Identify each immutable source version by content hash.
- Give blocks deterministic or reconciled stable identifiers.
- Persist explicit schema and normalization versions.

### FR-3 Normalized document model

- Represent hierarchy, text, lists, tables, code, equations, pictures, charts, notes and page/slide locations.
- Preserve parser-native lossless output as an attached artifact.
- Keep original assets or exact references to them.

### FR-4 Derived artifacts

- Support summaries, OCR, captions, chart data, entities and embeddings as optional derived artifacts.
- Record generator, model, prompt/config hash, input dependencies and confidence.
- Allow complete deletion and deterministic regeneration.

### FR-5 Change handling

- Skip unchanged source versions.
- Compare new normalized blocks against the previous version.
- Reuse unchanged derived artifacts where inputs and generation profile are identical.
- Mark dependent summaries/indexes stale when inputs change.

### FR-6 Retrieval

- Provide exact lexical search by default.
- Add optional semantic retrieval behind a provider interface.
- Support filters by document, version, block type, page/slide and trust classification.
- Return evidence references with every result.

### FR-7 Context compilation

- Accept task/query, evidence policy and token/character budget.
- Select representations progressively: metadata → outline → summary → exact block → visual crop → original.
- Never silently replace exact numeric evidence with a generated summary.
- Explain selection and omitted evidence in machine-readable metadata.

### FR-8 Interfaces

- CLI for all MVP use cases.
- Read-only MCP server for agent access.
- Stable HTTP API after the local core is proven.

### FR-9 Automation

- Local directory watcher with debouncing, stable-file checks and retries.
- Later: Microsoft Graph change notification + delta reconciliation connector.

### FR-10 Portability

- Export a document version as `.ardp.zip` containing a manifest, normalized records, assets and integrity metadata.
- Runtime storage may remain unpacked and content-addressed for efficiency.

## 5. Non-functional requirements

### Performance

- Unchanged file check p95 under 250 ms for local files up to 100 MB, excluding slow/network filesystems.
- Search p95 under 300 ms for 100k blocks on reference hardware.
- No parser invocation for a known source hash.
- Stream large records; do not load all assets into memory.

### Reliability

- Idempotent ingestion.
- Atomic commits: a failed job cannot expose a partially committed version.
- Retry transient operations with bounded exponential backoff.
- Crash recovery through persisted job states.

### Security and privacy

- Local-only by default.
- No external model call without explicit provider configuration.
- Document content is untrusted data.
- Path traversal, archive bombs, macros and hostile parsers are threat-modelled.
- Sensitive content must not appear in default telemetry.

### Maintainability

- Hexagonal architecture.
- Versioned schemas and migration tests.
- Small dependency set in the core.
- Parser/model/storage adapters are optional extras.

### Sustainability

- Reuse cached results before invoking compute-heavy models.
- Lazy image enrichment.
- CPU-compatible baseline.
- Publish benchmark energy proxies: wall time, CPU time, GPU time where available and bytes/model tokens processed.

## 6. Explicit non-goals for MVP

- Universal latent vectors or embeddings shared by all models.
- Perfect semantic compression without information loss.
- Editing source Office documents.
- Bidirectional synchronization between Word, PowerPoint and PDF.
- Enterprise permissions, DLP and retention enforcement.
- Knowledge graph reasoning as a mandatory component.
- A hosted SaaS.
- Replacing Docling, MinerU or Office Open XML parsers.

## 7. Success metrics

- Repeat-task time-to-first-useful-evidence reduction.
- Number of avoided parser, OCR, vision and embedding invocations.
- Input bytes/tokens delivered to the final model.
- Answer accuracy and evidence citation correctness.
- Stale-cache error rate.
- Retrieval evidence recall/precision.
- Prompt-injection attack success rate.
- Peak memory and compute per ingested page/slide.
