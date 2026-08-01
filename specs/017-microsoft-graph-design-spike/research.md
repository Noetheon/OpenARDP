# Research: Microsoft Graph Design Spike

**Reviewed**: 2026-08-01. Sources are official Microsoft documentation unless noted.

## Delta is authoritative reconciliation, not an event stream

**Decision**: Follow every `@odata.nextLink` until one `@odata.deltaLink`, reduce repeated item
occurrences by last occurrence and publish the final cursor only with the complete reduced state.
Represent 410 Gone as reset-required with no partial commit.

**Evidence**: [DriveItem delta](https://learn.microsoft.com/en-us/graph/api/driveitem-delta?view=graph-rest-1.0)
documents next/delta pagination, deleted facets, repeated items where the last occurrence wins and
410 reset behavior. [Delta overview](https://learn.microsoft.com/en-us/graph/delta-query-overview)
also notes replay and token-expiry/reset conditions.

**Rejected**: Treating each page as independently committable or treating notifications as a
complete event log. Either can expose partial truth after a late reset or missed delivery.

## Item ID is identity; path is mutable metadata

**Decision**: Hash the case-sensitive item ID inside exact tenant/site/drive scope. Never use a
path or name as identity, and never expose either in this contract.

**Evidence**: [DriveItem addressing](https://learn.microsoft.com/en-us/onedrive/developer/rest-api/concepts/addressing-driveitems?view=odsp-graph-online)
states that ID-based addressing survives rename/move within a drive while paths change, and IDs
are case-sensitive. Delta documentation notes parent paths can be absent.

## Revision values are hints, not byte identity

**Decision**: Store only scoped digests of `eTag`, optional `cTag` and optional version value.
At least one hint is required for an upsert; none proves original bytes or replaces SHA-256.

**Evidence**: [DriveItem resource](https://learn.microsoft.com/en-us/graph/api/resources/driveitem?view=graph-rest-1.0)
describes `eTag` as item metadata/content state and `cTag` as content state; `cTag` is unavailable
for folders in OneDrive for Business/SharePoint. Delta documentation records additional omission
conditions. Version history depends on service configuration and retention; see
[List versions](https://learn.microsoft.com/en-us/graph/api/driveitem-list-versions?view=graph-rest-1.0).

## Least privilege is a two-layer, unresolved production question

**Decision**: A future pilot should prefer delegated permission when appropriate or selected
application permissions assigned to exact resources. F017 records permission evidence but makes no
live compatibility claim. Tenant-wide `Files.Read.All` is not an acceptable silent fallback.

**Evidence**: The [permissions reference](https://learn.microsoft.com/en-us/graph/permissions-reference)
classifies application `Files.Read.All` as tenant-wide and administrator-consented and lists
selected scopes. The [selected permissions overview](https://learn.microsoft.com/th-th/graph/permissions-selected-overview?view=graph-rest-1.0)
requires Entra consent, explicit resource assignment and a matching token. Listing effective
permissions can be caller-dependent and incomplete; see
[List DriveItem permissions](https://learn.microsoft.com/en-us/graph/api/driveitem-list-permissions?view=graph-rest-1.0).

**Inference**: Complete permission-drift processing may conflict with least privilege because the
delta documentation's sharing-change guidance mentions `Sites.FullControl.All`. This must be
validated in a synthetic tenant and reviewed with Microsoft before any pilot; F017 does not widen
the permission set.

## Notifications are authenticated hints with lifecycle gaps

**Decision**: Validate scoped subscription/client-state digests and expiry in constant time, then
enqueue only a delta reconciliation hint. Periodic reconciliation remains mandatory.

**Evidence**: [Subscription resource](https://learn.microsoft.com/en-us/graph/api/resources/subscription?view=graph-rest-1.0)
documents drive notification limits and latency ranges. [Create subscription](https://learn.microsoft.com/en-us/graph/api/subscription-post-subscriptions?view=graph-rest-1.0)
limits OneDrive for Business subscriptions to the root folder. [Webhook delivery](https://learn.microsoft.com/en-us/graph/change-notifications-delivery-webhooks)
requires a public HTTPS endpoint, rapid acknowledgement and client-state validation, and documents
retries/missed delivery. [Lifecycle events](https://learn.microsoft.com/en-us/graph/change-notifications-lifecycle-events)
covers reauthorization, removal and missed notifications.

**Rejected**: Directly applying notification payloads or claiming a five-minute guarantee. The
documented maximum notification delay can exceed that target.

## Throttling must preserve atomicity

**Decision**: Honor a valid Retry-After exactly when within policy; otherwise use deterministic
capped exponential backoff. If the wait exceeds policy or retries exhaust, return retry-later and
leave state untouched.

**Evidence**: [Graph throttling guidance](https://learn.microsoft.com/en-us/graph/throttling)
requires respecting 429 Retry-After and recommends exponential backoff when it is absent. It also
prefers change tracking/notifications over polling.

## Data protection remains a deployment blocker

**Decision**: Inventory tenant metadata, permissions and optional content as personal/confidential
data, minimize storage, prohibit cross-tenant dedupe and require controller decisions on purpose,
retention, residency, subprocessors, rights, incident response and deletion before production.

**Evidence**: Microsoft's current [Products and Services Data Protection Addendum](https://www.microsoft.com/licensing/docs/view/Microsoft-Products-and-Services-Data-Protection-Addendum-DPA?isToggleToList=True&lang=1&year=2021)
is the vendor-contract starting point, not a project DPIA or legal conclusion.

## Final research decision

The mock-only architecture is feasible and useful for contract validation. Production remains
NO-GO because current OpenARDP is local/single-user and lacks tenant authorization, persistent
enterprise isolation, secret/certificate management, proven least-privilege compatibility,
public webhook operations, quota tests, completed privacy decisions and independent security review.
