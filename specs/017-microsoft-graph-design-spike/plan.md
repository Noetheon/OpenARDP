# Implementation Plan: Microsoft Graph Design Spike

**Branch**: `codex/f017-microsoft-graph-design-spike` | **Date**: 2026-08-01 | **Spec**: [spec.md](spec.md)

## Summary

Define and test an experimental, provider-neutral Microsoft Graph synchronization boundary
without credentials or network activity. Pure domain records carry tenant-scoped digests,
remote revision hints, permission references, ordered deltas, tombstones and notification
decisions. Ports isolate delta transport and atomic state publication. Deterministic in-memory
mock adapters exercise pagination, reset, throttling and failures; a service accumulates and
validates complete cycles before one commit. Security/privacy documents make the resulting
mock GO and production NO-GO independently reviewable.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Existing Pydantic v2 and RFC 8785 identity support; Python standard
library `hmac`, `threading` and collections; no Graph SDK or new dependency

**Storage**: In-memory feature mock only; no SQLite schema, CAS layout or migration change

**Testing**: pytest with sockets disabled; pure model, port-contract, orchestration, atomicity,
tenant-confusion, notification and leakage tests

**Target Platforms**: Linux, macOS and Windows with Python 3.12

**Performance Goals**: A cycle is bounded to 100 pages, 10,000 observed changes and five retry
attempts by default; focused tests complete in under ten seconds without wall-clock sleeping

**Constraints**: Zero credentials/network/live tenant, raw provider cursors and secrets remain
adapter-private, exact scope binding, no cross-tenant dedupe, no partial state publication,
body/path/token-free diagnostics, deterministic retry behavior

**Scale/Scope**: Synthetic single- and multi-tenant scenarios, two or more pages, repeated item
occurrences, update/tombstone transitions, reset and throttle outcomes

**Contract/Version Impact**: Experimental internal Python modules only. Public schemas,
application `0.1.0rc1`, workspace revision 10, provider profiles and export profile stay unchanged.

**Trust/Operational Impact**: Connector metadata and notifications are untrusted. A valid
notification schedules reconciliation but grants no read, write, execution or state-change
authority. Production deployment remains prohibited.

## Constitution Check

### Before design

- **Articles I-II**: The mock stores remote observations/tombstones, not source bytes; derived
  connector state is replaceable and final cursor publication is atomic.
- **Articles III-IV**: Remote revision values are hints, never universal content identity;
  permission/native provider details remain references behind a neutral boundary.
- **Article V**: Provider content and notifications remain untrusted data and cannot initiate
  tools or mutations without explicit orchestration.
- **Article VI**: Persisted mock identities use scope-bound RFC 8785/SHA-256 envelopes; no
  randomized hash or raw secret becomes core identity.
- **Articles VIII-IX**: Tests precede source implementation; reset, permission limitations and
  production blockers are first-class results.
- **Article X**: ADR 0016 authorizes this single mock implementation because the future Graph
  transport is the anticipated second implementation; no reusable framework is added.
- **Articles XI-XII**: F016 is merged and green. F017 changes no public or persisted version axis.
- **Explicit ADR boundary**: Constitution Article X forbids production Graph integration
  without ADR; ADR 0016 authorizes mock-only design and explicitly does not authorize production.

**Gate result**: PASS for the bounded mock spike. Production implementation remains blocked.

## Project Structure

```text
src/openardp/
├── domain/graph.py
├── ports/graph.py
├── adapters/mock_graph.py
└── services/graph_sync.py
tests/
├── domain/test_graph.py
├── contract/test_graph_ports.py
├── integration/test_graph_sync.py
└── security/test_graph_boundaries.py
specs/017-microsoft-graph-design-spike/
├── contracts/{connector-contract,permission-matrix,threat-model,data-protection-assessment}.md
├── checklists/{requirements,security-privacy}.md
└── spec,plan,research,data-model,quickstart,tasks,analysis,implementation-notes.md
```

**Structure Decision**: The domain and ports are provider-neutral synchronization concepts even
though Graph is the studied provider. The only implementation is named `mock_graph` to prevent
production ambiguity. No interface/CLI entrypoint is added.

## Phase 0: Research

[research.md](research.md) records official Microsoft facts about delta semantics, stable item
IDs, revision tags, selected permissions, effective-permission visibility, subscriptions,
lifecycle events and throttling. All accesses are dated; inferences are labeled. No
`NEEDS CLARIFICATION` remains.

## Phase 1: Design and contracts

- [data-model.md](data-model.md) defines scope-bound records and invariants.
- [contracts/connector-contract.md](contracts/connector-contract.md) freezes the mock port and
  orchestration semantics.
- The permission matrix, threat model and data-protection assessment define the production
  decision inputs without granting deployment authority.
- [quickstart.md](quickstart.md) provides one offline focused verification command.

### Post-design constitution re-check

PASS. The design adds no cloud dependency/default, credentials, production call, schema migration,
public endpoint, persistent identifier change or content-triggered side effect. Production Graph
remains an explicit future ADR and separate feature.

## Implementation strategy

1. Freeze contracts and write failing tests for models, ports and boundaries.
2. Implement pure records and identity helpers.
3. Implement protocols, deterministic mock adapter/store and atomic delta service.
4. Add notification validation and security/leakage checks.
5. Complete governance documents and fail-closed decision.
6. Run focused/full gates, converge and publish one F017 PR.

## Complexity tracking

The mock-only port exception is justified in ADR 0016. It is deliberately narrow: no Graph client,
authentication abstraction, generic cloud framework or persistent enterprise store is introduced.
