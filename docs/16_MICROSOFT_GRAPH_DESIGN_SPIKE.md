# Microsoft Graph Design Spike

Feature 017 validates a deliberately narrow, offline architecture for a future permission-aware
SharePoint/OneDrive connector. It adds no credential, SDK, network path or production configuration.

## Result

- **Mock contract architecture: GO**, contingent on the committed tests and repository gates.
- **Production Microsoft Graph connector: NO-GO**.

The executable evidence covers tenant/site/drive-scoped identities, stable item-ID semantics,
revision hints, permission snapshot references, ordered multi-page delta reduction, tombstones,
410 reset, throttling, atomic cursor/state publication and notification authentication as a wakeup.

It does not cover live Microsoft behavior, OAuth/consent, content download, complete permission
enumeration, webhook ingress, durable queues, tenant authorization, persistent enterprise storage,
erasure, telemetry, scale, quota, residency or operational response.

## Durable design rules

1. A Graph item is identified by exact scope plus case-sensitive item ID, never by path.
2. Raw provider IDs, delta links and secrets live only inside adapters/secret management.
3. `eTag`, `cTag` and version are remote revision hints, not source-byte identity.
4. Every upsert requires a complete exact-item permission snapshot reference.
5. Deletes are explicit tombstones.
6. Repeated delta items use last occurrence; the final cursor commits with state once.
7. A reset, cycle, scope mismatch, limit, retry-later or commit failure publishes nothing.
8. Notifications only schedule delta reconciliation and never mutate authoritative state.
9. No global cross-tenant dedupe, cache or equality side channel is allowed.

## Production blockers

- tenant-aware authorization and physically/logically isolated persistent storage/indexes;
- managed identity/certificates, secret rotation, revocation and incident response;
- live proof of selected-permission delta plus complete permission-drift behavior;
- approved DPA/DPIA, data residency, subprocessor, retention and data-subject procedures;
- hardened public webhook validation, lifecycle handling, durable queues and periodic reconciliation;
- per-tenant quota/backpressure tests, observability and operational runbooks;
- end-to-end permission revocation/erasure and independent security review;
- a favorable release decision—F015 currently remains an evidence-backed NO-GO.

The detailed evidence is in
[`specs/017-microsoft-graph-design-spike/`](../specs/017-microsoft-graph-design-spike/).
