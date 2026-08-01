# Alternate Parser Conformance Profile 0.1.0

**Status**: Repository conformance evidence; not a public interoperability standard.

## Process boundary

The coordinator invokes:

```text
python -I -S scripts/alternate_evidence_process.py <command> --request <absolute-file>
```

Supported commands are exactly `consume` and `produce`. The request is a bounded canonical
JSON file created in an operation-owned directory. Standard output is one bounded canonical
JSON response; diagnostics use a stable body-free category on standard error. No command
accepts inline source content, ambient workspace discovery or an output path.

## Consume request

Contains the resolved conformance root, manifest-relative evidence corpus/vector paths,
their expected digests and limits. The process validates every manifest-declared case and
returns ordered independent observations plus coverage counters. It must reject path or
manifest drift before parsing a case.

## Produce request

Contains the resolved conformance root, an exact allowlist of source descriptors and limits.
The process reads only those sources and returns canonical native artifact payloads plus
OpenARDP evidence record sets under provider `stdlib-text-csv` and profile
`deterministic-grid` `0.1.0`.

## Response envelope

Every successful response contains exactly:

- `profile_version`: `0.1.0`;
- `command`: `consume` or `produce`;
- `implementation_sha256`: digest of the exact standalone executable;
- `observations`: canonical ordered observation objects;
- `outputs`: empty for consume; closed source-keyed record sets for produce;
- `coverage`: exact counters and represented classes.

The envelope contains no timestamps, hostnames, absolute paths or source bodies. Failure is
non-zero with one allowlisted diagnostic category and no partial response.

## Identity profile

The safe canonical domain is JSON null, booleans, strings, arrays, string-keyed objects and
integers in `[-9007199254740991, 9007199254740991]`. Floats and invalid Unicode are rejected.
Identity envelopes use exact F006 domain strings, `identity_version: 1`,
`canonicalization: RFC8785`, explicit field allowlists and SHA-256.

## Decision rule

`supported_for_scoped_claim` requires all declared input digests, all consumer expectations,
all identity vectors, all producer determinism checks, all required coverage classes and all
reference-consumer validations to pass. Any absence or failure produces `not_supported`.
There is no override. Contract stability remains `experimental` in both outcomes.
