# Benchmark and evidence plan

**Status:** Planned evidence protocol. This document contains no benchmark result or performance claim.

## Fair baselines

A. Raw source reparsed for every task.

B. Persisted native `DoclingDocument`, directly reused.

C. Persisted DoclingDocument plus Docling chunking/retrieval.

D. OpenARDP evidence projection and retrieval.

E. OpenARDP context compiler with receipts and optional derivations.

## Metrics

- cold and warm ingestion latency;
- changed-source update latency;
- parser invocations avoided;
- storage overhead;
- retrieval precision/recall;
- source-anchor correctness;
- evidence coverage;
- answer quality using fixed evaluation prompts;
- tokens supplied to model;
- context assembly latency;
- stale-artifact rejection rate;
- prompt-injection success rate;
- deterministic replay rate;
- operator effort and integration complexity.

## Rules

- Never compare only against raw reparsing.
- Pin parser/model versions and configurations.
- Publish datasets or synthetic generators where licensing permits.
- Report failures and confidence intervals.
- Separate mechanical efficiency from downstream model quality.
- Do not generalize from synthetic microbenchmarks to enterprise workloads.
