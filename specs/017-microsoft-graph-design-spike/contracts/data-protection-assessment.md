# Data-Protection Assessment

Status: architecture-spike assessment, not legal advice or a completed DPIA.

## Data inventory and minimization

| Category | Potential examples | F017 treatment | Production question |
|---|---|---|---|
| Tenant/resource metadata | Tenant, site, drive, item, subscription identifiers | Tenant UUID plus scoped digests only | Lawful purpose, access roles, residency |
| Document metadata/content | Names, paths, authors, files | Excluded from F017 models | Necessity, classification, retention, DLP |
| Permission data | Principal IDs, groups, inherited grants | Opaque complete snapshot reference only | Completeness, special-category inference, revocation |
| Operational telemetry | Timing, throttles, errors | Bounded counts/categories only | Retention, tenant attribution, support access |
| Secrets/tokens | OAuth tokens, certificates, client state, delta URLs | Explicitly excluded/raw adapter-private | Vault, rotation, compromise and deletion procedures |

## Purpose and legal governance

The proposed purpose is permission-aware organizational document retrieval. A controller must
document lawful basis, purpose limitation, employee transparency, access roles and proportionality.
Microsoft's DPA is a vendor contract input; it does not replace the controller's record of
processing, DPIA decision or jurisdiction-specific advice.

## Required production controls

- Data residency and transfer mapping for Graph, hosting, backups, telemetry and support.
- Current subprocessor and contractual review, including Microsoft DPA/product terms.
- Per-tenant encryption/keys, authorization, storage, metrics and deletion queues.
- Retention schedules for content, derivatives, permission snapshots, tombstones, audit and backups.
- Data-subject access/correction/deletion and legal-hold conflict procedures.
- Permission revocation and tenant offboarding that reach all derived indexes/caches.
- Breach detection, response, notification, forensics and credential revocation runbooks.
- Human access controls, auditability, least privilege and periodic access review.
- Completed DPIA/works-council or other organizational review where applicable.

## F017 decision

The mock minimizes data by design and introduces no live processing. Production processing is
NO-GO until the controller owns and approves every unresolved item above and implementation tests
prove erasure, revocation and tenant isolation end to end.
