# Operator CLI Contract: Experimental Interchange

All commands are explicit trusted-operator actions. They are absent from MCP, watcher,
startup and document-triggered paths. Default output is body-free; `--json` emits one
closed JSON object and never includes local paths or member bodies.

## `openardp package-export`

```text
openardp package-export \
  --request REQUEST.json \
  --destination PACKAGE.zip \
  [--json]
```

The request is a closed JSON document containing the portable record and local
operator-selected asset source paths. Source paths are consumed only by the trusted
composition root and are never copied into package metadata or output. Included bytes
require affirmative redistribution assertion. Destination must be absent and disjoint
from every source.

Success reports operation, outcome, package/archive identities, profile/schema version
and bounded counts/bytes. Failure uses a stable category and exit code 2; no partial
destination is visible.

## `openardp package-verify`

```text
openardp package-verify --package PACKAGE.zip [LIMIT OPTIONS] [--json]
```

Reads and hashes but never extracts or publishes. Success returns the same bounded
identity/count projection used by import preflight. Unsupported version, malformed,
policy, resource, integrity and relationship failures are distinct categories.

## `openardp package-import`

```text
openardp package-import \
  --package PACKAGE.zip \
  --destination SNAPSHOT_DIR \
  [LIMIT OPTIONS] \
  [--json]
```

Destination must be absent and disjoint. The command verifies completely before
staging, copies only the declared regular members, reverifies and atomically publishes.
Repeating the exact package/destination converges after complete verification. A
foreign or different existing destination is `DESTINATION_CONFLICT`.

## Limit options

- `--max-archive-bytes`
- `--max-expanded-bytes`
- `--max-entry-count`
- `--max-entry-bytes`
- `--max-metadata-bytes`
- `--max-path-bytes`
- `--max-path-depth`
- `--max-relationships`

Every override must fall inside the installed range. Invalid CLI values fail before
opening the archive. Limits do not enable compression, unknown entries or unsupported
versions.

## Exit behavior

- `0`: complete verified success or exact converged result;
- `2`: expected sanitized package/policy/resource/integrity/destination rejection;
- `1`: other sanitized operational failure.

No result calls a package authentic, trusted, licensed, safe or universally
conformant.
