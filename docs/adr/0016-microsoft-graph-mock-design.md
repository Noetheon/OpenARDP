# ADR 0016: Permit a mock-only Microsoft Graph connector design

Status: Accepted for Feature 017

Date: 2026-08-01

## Context

The roadmap requires validating a future SharePoint/OneDrive synchronization architecture, but
the constitution forbids production Microsoft Graph integration without an ADR and keeps cloud
services disabled by default. Current OpenARDP is a local, single-user runtime without tenant-aware
authorization, enterprise secret management, public webhook ingress or production cloud storage.

The design also needs a port before two concrete implementations exist. Here the mock must be
structurally independent from a future network adapter so pagination, resets, throttling and atomic
state behavior can be tested without credentials or external effects.

## Decision

Feature 017 may add one experimental provider-neutral delta/state port, pure records, one explicitly
named in-memory mock adapter/store and deterministic orchestration tests. It may document official
Graph behavior and a future permission strategy.

Feature 017 may not add a Graph SDK, OAuth flow, credential/certificate handling, HTTP request,
public webhook endpoint, live tenant fixture, persistent enterprise store, background daemon or
cloud-enabled default. It changes no public schema or persisted identifier.

The one-implementation interface is a narrow Constitution Article X exception: its anticipated
second implementation is a separately governed production Graph adapter, and the mock is needed to
falsify the contract before that higher-risk work. The interface must not become a generic cloud or
authentication framework.

## Production boundary

This ADR does not authorize production Graph access. A future feature requires a new ADR grounded
in live synthetic-tenant evidence, exact permissions, tenant isolation, secret management, privacy
decisions, webhook/reconciliation operations, quota testing and security review.

## Consequences

- Mock contract feasibility and production readiness are separate decisions.
- Raw provider IDs/cursors/client state remain adapter-private; core records use scoped digests.
- Notifications remain wakeups and delta remains the reconciliation authority.
- Current SQLite/CAS/search are not represented as enterprise multi-tenant safe.
- The local-first default and dependency set remain unchanged.

## Alternatives considered

- Implement a live Graph client now: rejected by scope, constitution and missing controls.
- Documentation only: rejected because atomicity, scope and retry assumptions need executable tests.
- Add no port and embed mock logic in tests: rejected because the production boundary would remain
  implicit and orchestration could accidentally depend on test internals.
- Create a generic cloud connector framework: rejected as premature abstraction.
