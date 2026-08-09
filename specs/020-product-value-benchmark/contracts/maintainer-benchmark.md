# Maintainer Contract: Product Value Benchmark 0.1.0

## Commands

### Generate corpus

```text
uv run --locked python scripts/generate_product_benchmark.py \
  --profile {smoke|reference|scale} \
  --output <fresh-directory>
```

Produces deterministic source copies plus `corpus-manifest.json`. `--check <directory>` regenerates in a temporary
location and compares exact bytes without modifying the target.

### Run benchmark

```text
uv run --locked python scripts/run_product_benchmark.py \
  --profile {smoke|reference|scale|full} \
  --output <fresh-directory> \
  [--pdf-model-root <directory> --pdf-model-manifest <file>]
```

The default is offline and accepts no URL. `full` includes reference, scale and rich workloads. It atomically publishes
raw observations, summaries, the decision, the report and a checksummed run manifest. Existing non-identical output is
rejected. An honest conditional or negative decision exits successfully; malformed evidence or an incomplete run does
not.

For `reference` and `full`, rich fixture digests and format-bound parser configurations are validated before text work.
`--pdf-model-root` names the manifest-bound assets directory, not its parent installation directory. The supplied model
bundle is granted only to the PDF parser; DOCX and PPTX use independent model-free parser instances in the same run.
Parser-domain failures map to `benchmark_execution_failed` without reflecting exception text.

### Validate evidence

```text
uv run --locked python scripts/validate_product_benchmark.py \
  --result <complete-result-directory>
```

Recomputes file checksums, record identities, summary statistics, policy checks, decision and report. Success emits one
body-free JSON line. Failure uses a stable category and non-zero exit code.

## Stable output files

- `observations.json`: validated raw samples and explicit terminal failures
- `summary.json`: deterministic homogeneous aggregations and workload outcomes
- `decision.json`: frozen-policy worth-it decision
- `report.md`: human projection generated solely from verified machine evidence
- `run-manifest.json`: manifest-last completion and integrity record

## Failure categories

- `benchmark_input_rejected`
- `benchmark_capability_unavailable` (observation status, not command failure)
- `benchmark_execution_failed`
- `benchmark_evidence_invalid`
- `benchmark_output_conflict`
- `benchmark_drift_detected`

Messages contain no source body, task text, absolute path, username, hostname or raw exception text.

## Exit semantics

- `0`: complete valid evidence, regardless of the three-state value outcome
- `2`: invalid invocation
- `4`: bounded input or corpus rejected
- `6`: execution or evidence invalid
- `8`: output conflict or deterministic drift

There is no threshold override, waiver or network-enabling flag.
