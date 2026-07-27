# Data Model: Context Compiler and Selection Receipts

## Version dimensions

| Dimension | F008 value | Changes when |
|---|---|---|
| application | package release | code ships |
| receipt contract | `0.1.0` experimental | receipt shape/semantics change |
| receipt identity | `1` | identity projection changes |
| context algorithm | `openardp.lexical-context` / `1.0.0` | discovery/order/policy semantics change |
| estimator | name + semantic version + unit | measurement semantics change |
| workspace | SQLite revision `6` | persisted linkage changes |
| ContextBundle contract | existing `0.1.0` plus additive `0.2.0` | provenance can cite F006 projection |
| provider profile | unchanged | not changed by F008 |

## ContextCompileLimits

| Field | Rule |
|---|---|
| `max_scopes` | 1–32 |
| `max_discovered` | 1–10,000 |
| `max_candidates` | 1–512 |
| `max_body_bytes` | 1 KiB–8 MiB |
| `max_decisions` | 1–12,000 |
| `max_bundle_units` | 1 KiB–16 MiB equivalent |

All limits participate in algorithm configuration identity when they can change accepted
output.

## EstimatorIdentity

| Field | Rule |
|---|---|
| `name` | bounded non-empty identifier |
| `version` | exact semantic version |
| `unit` | `bytes`, `characters` or `tokens` |
| `config_hash` | SHA-256 of estimator configuration |

The runtime estimator must match all fields exactly. No fallback occurs during replay.

## ContextSelectionPolicy

| Field | Meaning |
|---|---|
| `mode` | existing summary/exact/numeric/visual/verification/mixed intent |
| `required_evidence` | sorted unique representation requirements |
| `allowed_trust_zones` | sorted non-empty allowlist |
| `maximum_sensitivity` | highest accepted sensitivity |
| `freshness` | `current_only` in F008; receipt model reserves explicit value |
| `include_history` | false for initial compilation; replay exact snapshot is separate |
| `response_reserve_percent` | exactly 10 in profile 1 |
| `provenance_target_percent` | exactly 10 in profile 1 |

The complete policy is safe to store in the receipt and its canonical digest enters
receipt identity.

## ContextCompileRequest

| Field | Rule |
|---|---|
| `task` | 1–4,096 characters; untrusted and never logged |
| `document_ids` | 1–32 sorted unique UUIDv7 IDs after normalization |
| `budget_limit` | positive, bounded for selected estimator |
| `estimator` | exact identity |
| `policy` | strict policy above |
| `limits` | strict limits above |

`task_digest` is the SHA-256 of exact UTF-8 task bytes. The receipt never retains `task`.

## CorpusSnapshot

A tuple of existing `VersionScope` values sorted by:

1. document UUID string;
2. version ID;
3. representation ID.

It is non-empty, unique and immutable. Snapshot time is the maximum deterministic READY
completion/observation timestamp among these scopes.

## ContextCandidate

| Field | Rule |
|---|---|
| `evidence_id` | exact block ID or F006 projection ID |
| `scope` | exact source/representation scope |
| `representation` | existing evidence representation enum |
| `source_order` | stable non-negative source ordinal |
| `body_object` | verified CAS object ID and length |
| `body_media_type` | bounded UTF-8 text or canonical JSON |
| `trust` | data-only classification; no promotion |
| `freshness` | `current`, `historical_exact` or `stale` |
| `term_coverage` | number of distinct query items matched |
| `occurrences` | total deterministic lexical occurrences |
| `reason` | stable candidate origin code |
| `high_value` | derived from mode/evidence policy |

Candidate identity is provider-neutral and scope-complete. The same evidence identity
may appear only once; duplicates become rejected decisions.

## BudgetLedger

| Field | Invariant |
|---|---|
| `unit`, `limit` | exactly request estimator unit/limit |
| `response_reserved` | `ceil(limit / 10)` |
| `bundle_ceiling` | `limit - response_reserved` |
| `provenance_target` | `ceil(limit / 10)` |
| `base_bundle_used` | fixed-point canonical empty/notice bundle measurement |
| `selected_incremental_used` | sum of accepted incremental bundle deltas |
| `bundle_used` | exact fixed-point final canonical bundle measurement |
| `remaining` | `bundle_ceiling - bundle_used`, non-negative |

`bundle_used + response_reserved <= limit` always holds. If base bundle usage alone
exceeds the ceiling, compilation fails before publication.

## SelectionDecision

Common fields:

- `evidence_id`, exact scope and representation;
- stable reason code;
- high-value flag;
- deterministic score facts and final order when relevant;
- estimated/incremental cost;
- no evidence body, source locator or task text.

Decision kinds:

- `selected`: accepted item and zero-based final order;
- `omitted`: valid but excluded by budget/candidate cap/policy priority;
- `rejected`: unsafe/invalid/duplicate/unsupported;
- `stale`: valid derived assertion excluded by freshness.

The four inventories are mutually exclusive and jointly cover every discovered subject.

## SelectionReceipt

Public experimental root fields:

| Field | Meaning |
|---|---|
| `contract_version` | exact `0.1.0` |
| `stability` | constant `experimental` |
| `identity_version` | constant `1` |
| `receipt_id` | recomputed domain-separated JCS/SHA-256 |
| `created_at` | deterministic corpus snapshot timestamp |
| `task_digest` | exact UTF-8 task digest |
| `algorithm` | name/version/config hash |
| `estimator` | exact identity |
| `policy`, `policy_digest` | complete safe policy and recomputed digest |
| `corpus_snapshot` | exact sorted version scopes |
| `budget` | complete ledger |
| `selected` | ordered selected decisions |
| `omitted` | ordered valid omissions |
| `rejected` | ordered invalid/unsafe decisions |
| `stale` | ordered stale decisions |
| `truncated` | discovery/decision cap reached |
| `notices` | body-free missing/escalation/coverage notices |
| `extensions` | JSON-only namespaced optional values |

Identity projection excludes only `receipt_id`. All remaining direct semantic fields,
including `created_at` and decisions, are inputs.

## ContextBundle 0.2.0

The prior `ContextBundle 0.1.0` class and schema remain unchanged. F008 adds a new exact
minor contract whose item provenance is a discriminated union:

- `record_type=block`: existing F002 document/version/representation/block UUID plus
  source locator;
- `record_type=evidence_projection`: document/version/representation plus F006 source,
  native, reference and projection SHA-256 identities.

Every provenance branch is scope-complete and rejects fields from the other branch. This
preserves true identities instead of projecting a rich anchor into a fake F002 block.

F008 constructs the `0.2.0` public model with:

- `query`: exact task, retained only inside the context handoff;
- `mode`: policy mode;
- `versions`: exact corpus snapshot;
- `items`: selected block or projection evidence in receipt order;
- `selection_trace`: compact selected-stage facts only;
- `warnings` and `missing_evidence`: exact notices;
- `budget`: exact unit/limit/used/estimator;
- `created_at`: deterministic snapshot timestamp;
- `bundle_id`: UUIDv5 over a domain-separated canonical projection of all other semantic
  bundle fields.

Each `EvidenceItem.content` uses a JSON delimiter envelope:

```json
{
  "content_role": "untrusted_data",
  "delimiter": "openardp-evidence-v1",
  "media_type": "text/plain",
  "body": "exact verified content"
}
```

The envelope is data, not prompt syntax or an authority boundary by itself; trust
classification is also enforced structurally.

## ContextCompilationRecord

Catalog row fields:

- `receipt_id` primary key;
- receipt and bundle object ID/length;
- deterministic bundle ID;
- task digest, algorithm, estimator and policy digest;
- exact budget limit/unit and created timestamp;
- selected/omitted/rejected/stale counts;
- canonical row fingerprint.

Child scope rows contain sorted `{receipt_id, ordinal, document_id, version_id,
representation_id}` values. No task text or evidence body is stored in SQLite.

## State and transaction model

```text
resolve exact heads
       |
verify/discover/classify
       |
build fixed-point bundle + receipt
       |
publish/verify both CAS objects
       |
BEGIN IMMEDIATE
  validate exact scope roots
  insert or exact-idempotent-match compilation
  insert exact ordered scope rows
COMMIT
       |
verified return
```

Cancellation/failure before commit exposes no compilation. CAS objects published before
failure remain immutable unreachable candidates. A same-receipt retry succeeds only when
every immutable fact and object byte matches.

## Aggregate verification

Loading or replay verifies:

1. compilation row fingerprint and indexed count facts;
2. exact scope rows are sorted, unique and still reference immutable READY/historical
   representations;
3. receipt and bundle CAS digest/length;
4. canonical JSON bytes and exact public model validation;
5. receipt/policy/bundle identities;
6. row/object identity and count agreement;
7. every selected item scope, trust, source handle and body digest;
8. budget fixed point and decision partition;
9. runtime algorithm/estimator identity before replay.
