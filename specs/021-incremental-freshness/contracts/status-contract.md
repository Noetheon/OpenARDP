# Status and freshness contract

## Service

`status(target, mode=HEAD)` returns one `SourceStatus`.

- `target` retains the existing explicit service/CLI path-or-document-ID behavior.
- `HEAD` is the default and never materializes representation blocks.
- `FULL` invokes the existing complete verifier for the exact snapshot scope.
- Every result includes `integrity_coverage`.

## CLI

```text
openardp --workspace <path> status <target> [--full-integrity] [--json]
```

- Default output is bounded HEAD status.
- `--full-integrity` is explicit and may be expensive.
- Human output states both freshness and coverage.
- JSON output adds `integrity_coverage` without renaming existing members.
- Errors retain existing stable exit categories and sanitized text.

## MCP

`get_source_status` retains its existing identifier-only input schema. It returns bounded HEAD status and adds
`integrity_coverage`; no request member enables full verification.

## Assurance semantics

| Coverage | Source SHA-256 | Atomic head/header | Native/manifest/block audit |
|---|---:|---:|---:|
| `NONE` | outcome-dependent | no successful coverage claim | no |
| `HEAD` | yes for inspectable source | yes | no |
| `FULL` | yes | yes | yes |

`CURRENT` plus `HEAD` means the exact live source matches the recorded head and bounded header checks passed. It does not
claim that every derived block was reread. Operators requiring that claim must request `FULL` through service or CLI.

## Compatibility

The field addition is explicit experimental-contract evolution. Freshness tokens, identifiers, CLI command name and MCP
input remain stable. No persisted schema or identity algorithm changes.
