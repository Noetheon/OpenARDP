# OpenARDP v0.1 Release Gate

**Decision**: `NO-GO`
**Candidate**: `0.1.0rc1`
**Decision ID**: `sha256:8814b3b4ac438f3b4e20bab273492e624d53f583baa926ab6adc66aae6c117f6`
**Source tree**: `sha256:4d96d8363e16b8037ae80c55d16999cecf34275469c0594fc4b72bc56bcefc5a`
**Policy**: `sha256:6c4100c13332cb6c27b43bcf1e7c88a8b074c79a6484bfcad110e710f93fbe16`

## Evidence registry

- `release-evidence.json`: policy, every platform bundle and every raw observation.
- `platform-evidence.json`: immutable per-sample benchmark and suite evidence.
- `artifacts.json` and `checksums.json`: candidate member inventories and digests.
- `sbom.cdx.json`: normalized dependency, license and graph inventory.

## Gate checks

- `platform-completeness`: **FAIL** (`platform-evidence-incomplete`; observed `1`, expected `3`)
- `evidence-identity-agreement`: **PASS** (`evidence-identities-agree`)
- `baseline-completeness`: **PASS** (`baselines-complete`; observed `1`, expected `1`)
- `suite-completeness`: **FAIL** (`mandatory-suite-failed`; observed `7`, expected `8`)
- `reference-timing-uniqueness`: **PASS** (`reference-timing-present`; observed `1`, expected `1`)
- `timing-sample-sufficiency`: **PASS** (`timing-samples-sufficient`; observed `63`, expected `7`)
- `raw-reparse-latency-value`: **PASS** (`raw-reparse-interval-exceeded`; observed `7333`, expected `267875`)
- `warm-parser-avoidance`: **PASS** (`warm-parser-invocations-zero`; observed `0`, expected `0`)
- `correctness-threshold`: **PASS** (`correctness-threshold-met`; observed `1`, expected `1`)
- `coverage-threshold`: **PASS** (`coverage-threshold-met`; observed `1`, expected `1`)
- `bounded-context-value`: **FAIL** (`bounded-context-value-not-demonstrated`; observed `0.5083333333333333`, expected `0.5`)

## Supported platform evidence

- None established by this decision.

## Residual limits

- Results apply only to the committed synthetic corpus and declared environments.
- Integrity and passing controls do not prove universal security or license legality.
- A GO is release-ready evidence, not publication or third-party reproduction.

## Install, upgrade and rollback

- Install only the checksum-verified `0.1.0rc1` wheel in an offline Python 3.12 environment.
- Back up a prior workspace before migration; never edit migration history manually.
- Restore the verified pre-upgrade backup to a fresh disjoint destination for rollback.
- A `NO-GO` decision prohibits release publication regardless of successful local drills.

## Blockers

- `platform-evidence-incomplete`
- `mandatory-suite-failed`
- `bounded-context-value-not-demonstrated`
