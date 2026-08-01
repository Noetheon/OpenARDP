# Maintainer Command Contract: Release Evidence

These are explicit local maintainer actions. They are not exposed through MCP, watcher jobs,
startup hooks or document-triggered execution. All default output is body-free; `--json` emits
one closed object. No command has a network or release-publication side effect.

## `openardp release-evidence`

```text
openardp release-evidence \
  --corpus benchmarks/release/v0.1.0 \
  --output OUTPUT_DIR \
  --source-root SOURCE_TREE \
  [--reference-timing] \
  [--json]
```

Creates an absent output directory atomically. `--source-root` is inventoried through the
closed release allowlist; absolute paths are neither serialized nor identity-bearing. Runs the bounded benchmark, correctness,
security/privacy, artifact/SBOM and local reproduction suites selected by the exact corpus and
configuration. `--reference-timing` is required to assert a stable reference environment;
ordinary CI runs still emit semantic observations but cannot satisfy that gate.

## `openardp release-gate`

```text
openardp release-gate \
  --policy benchmarks/release/v0.1.0/gate-policy.json \
  --evidence EVIDENCE_DIR [--evidence EVIDENCE_DIR ...] \
  --output DECISION_DIR \
  --decision-at 2026-08-01T00:00:00Z \
  [--json]
```

Verifies each bundle completely, requires one bundle for every policy platform and exactly one
reference-timing bundle, recomputes checks and atomically publishes `decision.json`, `report.md`,
`claim-map.json`, normalized `sbom.cdx.json` and checksums. A valid `NO-GO` is command success;
malformed evidence is exit 2. Consumers inspect the decision field rather than shell success.

There is deliberately no `--force`, `--waive`, `--ignore`, `--allow-missing` or threshold
override. A new policy version is the only way to alter release rules and must predate its
observations.

## `openardp release-report`

```text
openardp release-report --decision DECISION.json --output REPORT_DIR [--check] [--json]
```

Validates and renders body-free human/claim projections. `--check` compares exact expected
bytes and writes nothing. Existing output is never overwritten outside the exact check mode.

## Exit behavior

- `0`: evidence/report completed; inspect `decision` for `GO` versus `NO-GO`;
- `2`: sanitized expected validation, policy, resource, integrity or conflict failure;
- `1`: other sanitized operational failure.

Output reports operation, outcome/decision, evidence or decision ID, counts and stable reason.
It never prints supplied paths, bodies, canaries, exception text or environment secrets.
