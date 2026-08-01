# Implementation Notes: Microsoft Graph Design Spike

## Acceptance criteria restated

Feature 017 is complete when a deterministic offline mock demonstrates tenant-scoped item/cursor
identity, revision hints, complete permission references, ordered delta/tombstone reconciliation,
bounded retry and wakeup-only notification validation with atomic state publication; security,
privacy and permission evidence must then issue separate mock and production decisions. It must
use no credentials/network and must not change public schemas or production defaults.

## Authoritative inputs and baseline

- Prompt SHA-256: `b8d9634daddf4e33ca9f603cc468ed2c222016322aec516460167edc0ae8fd21`.
- Base: F016 merge `c2a90614a38babe978f9e776f6010faa495a4bea`.
- Post-merge F016 CI: run `30706640965`, attempt 2, all seven jobs successful. Attempt 1
  exposed a Windows-only SQLite lock race in an older F012 test; the unchanged rerun passed.
- F015 release decision remains NO-GO and is not overridden by F017.

## Clarification and design result

No user-blocking ambiguity remained after reading the authoritative prompt and project sources.
Reasonable conservative defaults were selected: digested adapter handles instead of raw tokens;
last-occurrence-wins across the whole delta cycle; no partial page commit; explicit tombstones;
complete permission references for upserts; notifications as hints; deterministic bounded retries;
and an independent production NO-GO.

ADR 0016 authorizes only the mock port exception and explicitly prohibits production Graph access.

## Test-first record

Four complete test modules were added before any F017 source module. The first focused run stopped
during collection with four expected `ModuleNotFoundError` failures for `openardp.domain.graph` and
`openardp.adapters.mock_graph`. After implementing the bounded modules, 29 focused tests passed.

## Implemented slices

### Pure contracts and identities

- Composite tenant/site/drive scope and case-sensitive item IDs use purpose-specific
  RFC 8785/SHA-256 identities. Raw provider values are bounded/control-free at the adapter input
  and never retained by domain models.
- Remote revision hints are explicitly distinct from content identity. Upserts require exact
  complete permission references; deletes and stored deletions are sparse explicit tombstones.
- Delta pages permit repeated items but require strict in-page order and exactly one continuation
  or final opaque handle. State is sorted, unique, scope-bound and generation-numbered.

### Mock adapters and atomic service

- The zero-network adapter owns raw cursors in a private scope-keyed registry and exposes only
  digest handles plus queued pages, 429 and 410 outcomes.
- The in-memory state port builds and validates the full prospective state under one lock, checks
  the expected cursor and supports a pre-publication injected failure.
- Orchestration accumulates the whole bounded page set, applies last occurrence across pages and
  commits once. Reset, cycle, scope mismatch, limit, retry-later and commit failure expose no
  partial item or cursor state.
- Retry-After is honored exactly within policy; missing delay uses deterministic capped exponential
  backoff. Notifications use constant-time digest comparisons and can only return a scheduling hint.

### Governance and decision

- ADR 0016 permits the narrow one-mock port exception while explicitly withholding production
  authorization.
- Official-source research, permission matrix, threat model and data-protection assessment record
  platform facts and unresolved inferences.
- Mock contract architecture is GO. Production Graph remains NO-GO and F015 release NO-GO remains
  binding.

## Tradeoffs and residual risks

- Scoped digests minimize disclosure but do not provide secrecy against low-entropy identifier
  guessing without a keyed production design; production tokenization/key management is unresolved.
- In-memory atomicity proves transaction semantics, not crash durability or distributed consistency.
- Deterministic no-jitter backoff is appropriate for tests, not a production fleet policy.
- Official documentation cannot establish tenant-specific permission behavior; live synthetic-tenant
  validation remains mandatory.
- A passing mock does not establish the enterprise latency target or production privacy/security.

## Verification log

- Test-first red: four expected import errors before F017 source existed.
- Focused F017: 29 passed with sockets disabled.
- Combined package/repository/F017 regression: 72 passed.
- Ruff check and format: passed for all 240 files.
- Strict mypy: passed over 81 source files.
- Repository validation: passed.
- Full pytest: 1,371 passed with 85.28% branch coverage.
- Build: wheel SHA-256 `6919d8cf5e45b89a45218a2d1ee87737c77d70308b486eab5fd9f8834cedb882`;
  sdist SHA-256 `73b9861b462789f3f1355287ec25eabcacd1f5e8661854001095321e9576f607`.
- Pre-commit: all Ruff, format, strict mypy and full pytest hooks passed.
- Publication: private repository `Noetheon/OpenARDP`, branch
  `codex/f017-microsoft-graph-design-spike`, PR `#22`. Immutable final PR and post-merge
  workflow conclusions are recorded in the PR discussion after GitHub completes them.
