# Release Evidence Contract 0.1.0

The generated JSON Schema root is `schemas/openardp-release-evidence.schema.json`. Every JSON
record is closed, RFC 8785 canonicalizable and versioned independently of the application,
workspace, provider and interchange profiles.

## Evidence directory

```text
evidence/
├── manifest.json
├── environment.json
├── observations.jsonl
├── correctness.json
├── security.json
├── privacy.json
├── dependency-review.json
├── sbom.cdx.json
├── artifacts.json
├── reproduction.json
└── decision.json
```

`manifest.json` inventories every other normative entry by portable path, byte length and
SHA-256. Unknown/missing/extra/case-colliding entries fail. JSONL is LF-delimited canonical JSON,
bounded per line and globally, with unique observation keys.

## Identity and validation

1. Validate paths, lengths/counts and closed schemas before loading child records.
2. Rehash every entry, protocol/corpus/configuration/policy/source-tree/lock/artifact input.
3. Recompute record, suite and decision identities from documented projections.
4. Recompute statistics and every gate check; declared aggregate/status fields are assertions.
5. Reject non-finite numbers, wrong units, duplicate keys, unknown enums/fields and unsupported
   versions.

An integrity-valid bundle remains untrusted evidence. Validation does not prove benchmark
fairness, authenticity, vulnerability absence, license compatibility or release authority.

## Statistics

- timings are integer nanoseconds;
- release summaries require at least seven valid post-warmup samples;
- median and MAD use sorted exact decimal input;
- 10,000 percentile-bootstrap median resamples use a deterministic SHA-256 counter stream
  seeded by suite/group identity;
- lower/upper positions use the documented nearest-rank rule;
- report rounding is half-even to six decimal places;
- invalid/rejected/unavailable samples remain listed and reduce completeness.

## Gate behavior

The evaluator emits all policy checks in canonical order. Any failing check produces `NO-GO`.
There is no override property or command option. Unknown policy clauses/major versions fail.
An unsupported future minor is accepted only when every unknown extension is under an explicit
non-normative container and the installed reader declares that minor compatible.

## Privacy boundary

Machine evidence may contain stable identifiers, versions, platform class, durations, counts,
bytes, ratios, hashes, advisory IDs and closed outcomes. It may not contain document/query/task
bodies, absolute paths, usernames, hostnames, credentials/tokens, arbitrary environment values,
raw exception strings or test output.

## Generated projections

`report.md` and `claim-map.json` are generated from verified `decision.json`. Their generator
digest is recorded in `manifest.json`; manual changes fail drift validation. README references
claim IDs, not hand-copied benchmark numbers.
