# Threat Model: Microsoft Graph Connector Boundary

## Assets and trust boundaries

- Tenant/site/drive authorization, access and refresh tokens, certificates and client-state secrets.
- Delta cursors, subscription IDs, provider item identities and permission snapshots.
- Original document bytes and derived evidence.
- Boundary sequence: public notification ingress -> reconciliation queue -> Graph adapter ->
  permission-aware ingestion -> tenant-scoped storage/index -> policy-enforced query.

F017 implements only deterministic records, service and mocks inside the middle contract. Public
ingress, identity provider, network, durable queue/store and query authorization do not exist.

## Threats and required controls

| Threat | F017 control | Production requirement |
|---|---|---|
| Forged/replayed notification | Constant-time scoped digests, expiry, wakeup-only semantics | HTTPS validation, replay window, durable idempotent queue, monitoring |
| Token/cursor/secret disclosure | Raw values adapter-private; body-free errors/models | Managed identity/certificate vault, redaction tests, rotation and revocation |
| Tenant/site/drive confusion | Every digest and cursor bound to composite scope | Authorization on every read/write/query and isolated tenant storage |
| Mutable path identity | Case-sensitive item-ID digest; no path in identity | Rename/move live tests and metadata handling |
| Permission drift/incomplete ACL | Complete snapshot reference required for upsert | Proven permission crawler, deny-before-allow publication, revocation SLA |
| Lost deletion | Explicit tombstones plus final-cursor atomicity | Durable tombstone retention and periodic full reconciliation |
| Partial delta/reset | Accumulate then one commit; 410 resets with no commit | Durable restart state and controlled full-resync procedure |
| Throttling/resource denial | Page/change/retry/delay bounds | Per-tenant quotas, circuit breakers, capacity and alerting |
| SSRF/egress abuse | No network implementation; provider content is data | Fixed Graph hosts, proxy allowlist, redirect/DNS controls, workload isolation |
| Prompt/tool injection | Notification/content grants no execution authority | Parser sandbox, policy gateway and output encoding |
| Cross-tenant equality/timing leak | No global dedupe/cache in feature | Partitioned encryption keys, stores, metrics and timing review |
| Malicious administrator/overbroad app | No credentials or permission request | Separation of duties, audit trail, access reviews and break-glass controls |

## Residual decision

The mock controls demonstrate fail-closed orchestration only. They do not mitigate production
identity, network, platform, operator or multi-tenant threats. Production remains NO-GO pending
implementation-specific threat modeling and external security review.
