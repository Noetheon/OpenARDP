# Operational and enterprise requirements

## SLO candidates for a pilot

- Catalog/search availability: 99.5% during business hours.
- Ingestion completion: 95% of standard documents under an agreed size within 10 minutes.
- Change detection: 95% visible within 5 minutes after OneDrive/SharePoint reconciliation.
- Authorization decision p95: under 200 ms excluding identity provider latency.
- Zero known cross-tenant data disclosure.

These are placeholders until workload measurements exist.

## Observability

Use OpenTelemetry-compatible traces, metrics and logs.

Trace stages:

```text
source.detect → snapshot → hash → parse → normalize → reconcile → commit → index → enrich → context.compile
```

Metrics:

- ingestion jobs by state/type;
- parser duration and peak memory;
- cache hits by layer;
- bytes/pages/slides processed;
- enrichment provider calls/tokens;
- context bundle size and evidence types;
- stale artifact count;
- authorization denials;
- queue age and retries.

Do not attach document text, embeddings or filenames containing personal data to telemetry by default.

F003 does not yet emit an observability backend. Its error boundary deliberately reports identifiers/classifications only:
source locators, document bytes, raw SQL parameters, raw lease tokens and untrusted exception text are excluded. Future
telemetry adapters must preserve that default.

## Data lifecycle

- Source binaries: reference or copy according to governance policy.
- Canonical versions: retention aligned with source system/legal obligations.
- Derived artifacts: configurable TTL and recomputable.
- Deleted source: preserve/tombstone based on policy; remove from default retrieval immediately.
- Garbage collection: mark-and-sweep from live manifests and retention holds.

F003 implements only the safe observation prerequisite: every historical source-version and job object reference is a
conservative live root; verified unreferenced objects are advisory candidates; missing, corrupt, malformed, unsafe and
staging entries are inconsistencies. There is no deletion API, retention decision or secure-erasure claim.

## Authorization

For enterprise mode:

- maintain source connector identity and ACL metadata;
- re-check current authorization at query time;
- do not rely only on ingestion-time ACL snapshots;
- avoid cross-tenant global deduplication side channels;
- separate admin, ingestion worker and query gateway identities;
- use managed identities where available.

## Disaster recovery

- catalog backups and point-in-time recovery;
- artifact store versioning/immutability;
- reproducible indexes from canonical records;
- documented restore drills;
- saved Graph delta state and a safe full-rescan procedure.

### Current local persistence recovery boundary

- CAS publication is atomic on the configured same filesystem and synchronized with the strongest supported local calls.
- SQLite uses checksummed ordered migrations, rollback journaling and `synchronous=EXTRA`; a pending chain commits wholly
  or rolls back wholly.
- Reopen validates migration order/checksums, exact expected tables, foreign keys and supported revision before work.
- Expired running jobs are requeued only while attempts remain; exhausted work becomes terminal and repeated recovery is
  empty until state changes again.
- Backups, point-in-time recovery, network filesystems, disk failure and universal power-loss durability are not provided
  by F003 and require explicit operational validation in the deployment environment.

## Cost controls

- per-tenant/user/document quotas;
- lazy enrichment and model allowlists;
- maximum page/image sizes;
- budgeted context compilation;
- cache hit dashboards;
- cancellation/supersession of obsolete jobs;
- provider spend alerts.
