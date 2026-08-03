# OpenARDP v0.1 Release Gate

**Decision**: `NO-GO`
**Candidate**: `0.1.0rc1`
**Decision ID**: `sha256:13bb88e3a5f22ee26e75420bf80ace31685e894fcc3d3ae8aedbdbeb8966b333`
**Source tree**: `sha256:06cd35de5dfb2c56f53e2727d1a40aec3184eaa64fcffe2a1e8546d620f9df3d`
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
- `raw-reparse-latency-value`: **PASS** (`raw-reparse-interval-exceeded`; observed `6833`, expected `270583`)
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
