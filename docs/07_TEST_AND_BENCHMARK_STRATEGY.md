# Test and benchmark strategy

## 1. Test pyramid

### Unit tests

- canonical JSON and hashing;
- identifier stability;
- schema validation;
- path safety;
- derivation keys;
- block reconciliation;
- budget allocation;
- trust-policy decisions.

### Contract tests

- parser adapter output invariants;
- artifact store atomicity;
- catalog migrations;
- MCP JSON schemas;
- portable package import/export compatibility.

### Integration tests

- ingest → search → context;
- unchanged re-ingest skip;
- changed source invalidation;
- parser crash recovery;
- watcher debounce;
- no-network local mode.

### End-to-end tests

Codex/MCP client against synthetic documents. Validate tool sequence and evidence bundle, not model prose alone.

### Security tests

Use the threat-model corpus and property/fuzz testing for parsers' boundary code.

## 2. Golden fixture corpus

Create redistributable synthetic files with:

- headings, lists, tables and footnotes;
- repeated and changed paragraphs;
- PowerPoint notes and charts;
- images with embedded text;
- scanned page;
- complex multi-column PDF;
- malformed and hostile cases;
- multilingual text;
- exact expected block/source mappings.

Never commit proprietary company documents.

## 3. Benchmark conditions

### A — raw file workflow

Agent/parser receives the original on every task.

### B — conversion-only cache

Cached Markdown/JSON but no structured evidence policy.

### C — conventional text RAG

Chunked text + retrieval.

### D — OpenARDP

Normalized blocks + versioning + provenance + progressive context + optional visual escalation.

## 4. Workloads

- document summary;
- exact fact lookup;
- table numeric comparison;
- chart/visual question;
- cross-document consistency check;
- update after a one-paragraph edit;
- repeated tasks on unchanged content;
- indirect prompt-injection document.

## 5. Metrics

### Efficiency

- wall-clock time to first evidence and final answer;
- parser/OCR/vision/embedding invocation count;
- input bytes and provider tokens;
- CPU time, peak RSS and GPU time if applicable;
- derived cache hit ratio;
- bytes stored before/after deduplication.

### Quality

- exact answer accuracy;
- table cell accuracy;
- evidence recall/precision;
- source-location accuracy;
- hallucination rate;
- visual-evidence escalation correctness;
- stale-data incidents.

### Security

- prohibited tool-call rate;
- data-exfiltration attempt success;
- malicious content appearing as trusted instruction;
- isolation/resource-limit enforcement.

## 6. Release gates

MVP release requires:

- all schemas and golden packages pass;
- unchanged source invokes parser zero times;
- no high-severity security test failure;
- evidence citation accuracy target ≥ 95% on the synthetic suite;
- benchmark scripts and raw results committed;
- performance claims limited to measured hardware/workloads.
