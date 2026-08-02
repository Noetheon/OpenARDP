# Benchmark and evidence plan

**Status:** Feature 015 implements the frozen evidence protocol and fail-closed gate. The
current committed candidate decision is `NO-GO`; this document makes no release or
general performance claim.

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

## Feature 015 frozen protocol

The normative inputs are under `benchmarks/release/v0.1.0/`. They fix five baseline
identities, three judged document families, three byte budgets, seven retained timing
samples after one warm-up and 10,000 deterministic percentile-bootstrap resamples.
Raw observations retain failures and unavailable treatments. Mechanical correctness is
computed only from committed exact terms, evidence identities and anchors; no model
evaluator result is implied when `model_evaluator` is `unavailable`.

The committed local reference capture contains 4,222 raw observations across all five
baselines, three document families and three budgets. Exact mechanical quality passes;
the selected/native ratio does not meet the predeclared `0.5` ceiling. This unfavorable
result is a binding blocker, not a hidden or relabelled success.

Only one explicitly declared reference environment may supply binding timing evidence.
Shared CI supplies platform semantics but is not silently treated as an idle reference
machine. Operational value requires the OpenARDP retrieval upper confidence bound to
remain below the raw-reparse lower bound, zero warm parser calls, exact judged quality
and selected bytes at most half the direct-native bytes.

The authoritative result is
[`release/evidence/v0.1.0/decision.json`](../release/evidence/v0.1.0/decision.json).
Its report and claim map are generated projections. Current missing evidence remains a
release blocker; it is not a benchmark failure hidden behind narrative wording.

## Feature 020 product-value result

F020 adds a separate workload-bounded question: whether the delivered parse-once and exact-evidence paths create useful
repeated-task value. Its frozen corpus and policy are under `benchmarks/product-value/v0.1.0/`; the committed macOS arm64
run contains 878 observations and 98 robust timing summaries across 10,000- and 100,000-block text workloads plus actual
DOCX/PPTX and explicitly unavailable PDF execution.

The decision is `CONDITIONALLY_WORTHWHILE`. All mechanically judged search, anchor, context and replay results are exact;
stale incidents and unchanged-source parser invocations are zero. Worst observed 100,000-block search p95 is 70.200 ms
against the 300 ms target, and the reference repeated-lookup break-even against raw reparsing is 32 tasks. DOCX/PPTX
reuse crosses raw reparsing after two tasks.

The result is not unconditional. Reference status p95 is 2,087.372 ms against the 250 ms target; the scale status p95 is
28,625.664 ms and remains visible in the report. PDF requires an unavailable provisioned offline model bundle, 256- and
512-byte context budgets cannot hold the safe base envelope, the workspace is approximately 37.9 times the source bytes,
and direct persisted-native loading remains faster than verified rich reuse. These facts are measured limitations, not
waivers. The F015 release decision remains `NO-GO`.

The authoritative F020 projection is
[`benchmarks/product-value/v0.1.0/results/reference-macos-arm64/report.md`](../benchmarks/product-value/v0.1.0/results/reference-macos-arm64/report.md).
