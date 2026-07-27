# Contract: Selection Receipt 0.1.0 Experimental

## Status

F008 adds `schemas/selection-receipt.schema.json` as a strict JSON Schema 2020-12
experimental root alongside additive `schemas/context-bundle-0.2.0.schema.json`. It does
not modify the installed `ContextBundle 0.1.0` schema or any F006 evidence schema. Schema
identifiers are offline identifiers, never URLs to fetch.

## Purpose

The receipt explains a bounded context result without duplicating its task text, source
bodies, native payloads, paths, secrets or credentials. It is an audit object, not a
trust grant, answer or instruction.

## Required root

```text
SelectionReceipt
├── contract_version = "0.1.0"
├── stability = "experimental"
├── identity_version = 1
├── receipt_id
├── created_at
├── task_digest
├── algorithm
├── estimator
├── policy + policy_digest
├── corpus_snapshot[]
├── budget
├── selected[]
├── omitted[]
├── rejected[]
├── stale[]
├── truncated
├── notices[]
└── extensions
```

Direct fields are closed. Unknown JSON-only data is permitted only inside namespaced
`extensions`. Readers distinguish malformed input, unsupported major family and
well-formed but uninstalled release.

## Identity contract

```text
receipt_id = sha256(
  RFC8785({
    "canonicalization": "RFC8785",
    "domain": "openardp:selection-receipt",
    "identity_version": 1,
    "payload": <all direct receipt fields except receipt_id>
  })
)
```

No Unicode normalization or unsafe-number coercion occurs. Decision array order is
semantic. Changing task digest, snapshot, algorithm, estimator, policy, budget, decision,
notice or timestamp changes the identity.

Policy digest uses the same envelope with domain `openardp:context-policy` and the
complete policy payload.

## Decision partition

Each discovered subject appears exactly once across:

| Inventory | Meaning |
|---|---|
| `selected` | valid and included, with final order |
| `omitted` | valid but excluded by budget/cap/priority |
| `rejected` | unsafe, invalid, duplicate or unsupported |
| `stale` | otherwise valid but excluded by freshness |

All entries are body-free and source-path-free. Reason codes are stable machine values;
optional human messages belong in CLI presentation, not identity-bearing decisions.

## Budget contract

- Units are exactly `bytes`, `characters` or `tokens`.
- Estimator name/version/config must match runtime and receipt.
- Response reserve is 10% rounded upward.
- `bundle_used + response_reserved <= limit`.
- `remaining = bundle_ceiling - bundle_used`.
- `bundle_used` is the fixed-point measurement of canonical ContextBundle bytes.
- Receipt bytes are not part of the context-window budget because they are a separate
  audit artifact and contain no evidence body.

## Trust and privacy contract

- Every selected item remains role `data` with instruction execution false.
- Receipt trust values describe selected evidence; they do not promote it.
- Receipt fields reject raw task/query/body/native/path/credential values by shape and
  aggregate privacy tests.
- Extension values are untrusted inert JSON and never resolved as paths, URLs or commands.

## Persistence and replay

Receipt and bundle canonical bytes are stored in CAS and linked atomically by workspace
revision 6. Replay:

1. loads and fully verifies both objects and exact scope rows;
2. rejects algorithm, estimator or policy mismatch;
3. reuses the exact snapshot, never current heads;
4. recompiles with the task supplied out-of-band and requires its digest to match;
5. requires byte-identical bundle and receipt output.

## Compatibility

Adding these roots is additive. The nine pre-F008 schemas and both established identity
vector files remain byte-identical. Any later direct-field or identity change requires a
new reviewed contract release, migration notes and fixtures; breaking changes require
the governed ADR/migration process.
