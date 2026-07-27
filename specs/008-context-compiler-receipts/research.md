# Research: Context Compiler and Selection Receipts

## Decision 1 — Add a bundle minor and a separate receipt contract

**Decision**: Keep the existing public `ContextBundle 0.1.0` model/schema
byte-compatible and available, add `ContextBundle 0.2.0` as a separate experimental
schema with discriminated block-or-projection provenance, and add
`SelectionReceipt 0.1.0` as an independent experimental public root.

**Rationale**: The `0.1.0` bundle requires a F002 block UUID in every evidence item, while
F007 rich evidence intentionally has F006 SHA-256 projection/reference identities.
Fabricating a block UUID would falsify provenance. The additive `0.2.0` release preserves
the same bundle purpose but makes provenance a closed discriminated union. A bundle is
the evidence handoff; a receipt is a privacy-conscious audit trace. The blueprint already
governs both candidates, so additive experimental releases follow the contract lifecycle
without creating another document representation.

**Alternatives considered**:

- Encode F006 IDs inside `ContextBundle 0.1.0` extensions while inventing a required
  block UUID: rejected because the core provenance would be false.
- Change `context-bundle.schema.json` in place under version `0.1.0`: rejected as an
  unversioned compatibility break.
- Put receipt fields in bundle extensions: rejected because receipt invariants would be
  informal and schema-unverifiable.
- Keep receipts internal only: rejected because F009 and external auditors need a
  stable, provider-neutral body-free boundary.

## Decision 2 — Snapshot current heads once, then operate on exact scopes

**Decision**: Initial requests accept document IDs and resolve each to one current READY
head in a single bounded snapshot phase. All downstream discovery and replay use the
sorted exact scopes recorded by the receipt.

**Rationale**: Document IDs are usable; exact scopes are replayable. Re-reading mutable
heads during selection would mix versions. A head change after snapshot resolution
cannot change an in-flight result.

**Alternatives considered**:

- Require callers to know all representation IDs: rejected as poor local CLI ergonomics.
- Always use latest during each stage: rejected as non-deterministic and unauditable.
- Copy complete catalog state into the receipt: rejected as unnecessary and private.

## Decision 3 — Use two verified deterministic lexical sources

**Decision**: Text candidates come from the existing F005 FTS accelerator, followed by
full exact catalog/CAS verification and deterministic rescoring. F007 rich projections
use a bounded verified lexical scan of accepted retrieval bodies. Both implement one
narrow candidate-source port.

**Rationale**: F005 already proves explicit coverage/drift failure for normalized text.
F007 intentionally added no rich index. A bounded scan makes rich context useful now
without introducing migration/index duplication just to optimize an unmeasured workload.
Two implementations justify the small port and keep provider-specific types outside the
service.

**Alternatives considered**:

- Extend FTS to rich projections in F008: rejected because index lifecycle integration
  materially expands this feature and performance evidence does not yet justify it.
- Bypass FTS and scan all text: rejected because it would ignore the required corrupted
  accelerator boundary.
- Index or compare native Docling JSON: rejected because provider-native detail is not a
  provider-neutral retrieval contract.

## Decision 4 — Recompute a provider-neutral lexical score

**Decision**: Candidate sources return exact normalized query-term occurrence and
coverage counts. Ordering uses evidence priority, descending phrase/term coverage,
descending occurrence count, then exact scope, source order, representation and evidence
identity.

**Rationale**: SQLite BM25 is useful for discovery but ranks from separate document
queries are not directly comparable and may vary with corpus/index details. Rescoring
verified bodies with integer facts creates a documented total order while retaining FTS
coverage/integrity checks.

**Alternatives considered**:

- Order directly by BM25: rejected for cross-scope comparability and float portability.
- Alphabetical-only ordering: rejected because it discards task relevance.
- Model reranking: explicitly deferred and incompatible with deterministic offline
  baseline acceptance.

## Decision 5 — Version estimators and measure canonical bundle bytes

**Decision**: Ship three local estimators: exact UTF-8 bytes, exact Unicode scalar
characters and conservative tokens at one token per UTF-8 byte. Their name/version/unit
are identity inputs. The compiler repeatedly canonicalizes the bundle until the embedded
usage field reaches a fixed point.

**Rationale**: Byte and character units are exact. The conservative token estimator
cannot undercount an unknown provider tokenizer and makes no compatibility claim. Full
canonical-bundle measurement includes content, provenance, trust, warnings and metadata,
not only body strings.

Budget allocation:

1. response reserve is `ceil(limit / 10)`;
2. bundle ceiling is `limit - response_reserve`;
3. provenance target is `ceil(limit / 10)` and is reported separately;
4. candidates are admitted only when the fully rebuilt canonical bundle remains at or
   below the bundle ceiling;
5. the receipt is outside the handoff budget and strictly body-free.

**Alternatives considered**:

- Estimate tokens as characters divided by four: rejected because it can undercount.
- Count evidence bodies only: rejected because provenance/metadata can overflow a handoff.
- Import a provider tokenizer: rejected as a mandatory provider dependency; the port
  supports a later exact local implementation.

## Decision 6 — Derive both identities without cycles

**Decision**: Receipt ID is a domain-separated RFC 8785/SHA-256 identity over every
semantic receipt field except `receipt_id`. Bundle UUID is UUIDv5 over a domain-separated
canonical digest of the complete semantic bundle fields except `bundle_id`.
The catalog, rather than either public object, links the bundle object to the receipt.

**Rationale**: This avoids a receipt↔bundle identity cycle and gives byte-identical
repeated output. A deterministic snapshot timestamp derived from persisted READY facts,
not wall-clock compilation time, supplies the public `created_at`.

**Alternatives considered**:

- Random UUID and current time: rejected because stable replay would fail.
- Receipt references bundle hash while bundle references receipt: rejected due cyclic
  construction.
- Exclude decisions from receipt identity: rejected because differing explanations could
  share an ID.

## Decision 7 — Persist both objects with catalog revision 6

**Decision**: Publish canonical bundle and receipt bytes to CAS, then atomically insert
one immutable compilation row plus its sorted exact scope rows. The receipt ID is unique;
replay is idempotent only when all row and object facts match exactly.

**Rationale**: CAS publication is not catalog reachability. A narrow linkage makes
receipts durable, loadable and auditable without putting bodies in SQLite. Existing
reachability inventory can add compilation roots.

**Alternatives considered**:

- Return ephemeral objects only: rejected because receipts could not be audited/replayed.
- Put JSON bodies in SQLite: rejected by current storage architecture.
- Delete CAS objects on rollback: rejected because identical bytes may already be shared.

## Decision 8 — Treat omissions, rejections and stale facts differently

**Decision**:

- `selected`: valid candidate included in ordered bundle;
- `omitted`: valid candidate not included because budget/cap/policy priority;
- `rejected`: malformed, unsupported, trust/scope/body mismatch or duplicate candidate;
- `stale`: otherwise valid derived candidate whose exact inputs are not current under
  the declared freshness policy.

Every discovered subject is classified exactly once. High-value is deterministic from
mode/evidence policy, never model inference.

**Rationale**: Combining these states would hide whether evidence was unsafe, outdated or
merely too expensive. The distinction is central to honest context.

## Decision 9 — Visual escalation is an honest notice only

**Decision**: F008 may select an already available verified visual handle but performs no
rendering/cropping. If required visual evidence is unavailable, the bundle and receipt
emit stable `visual_evidence_required` facts scoped to the exact document.

**Rationale**: Constitution VII requires surfacing visual need; F011 owns production of
exact visual artifacts.

## Decision 10 — CLI wraps one service and returns handles by default

**Decision**: `openardp context TASK --document ID ... --budget N --unit UNIT` compiles
and returns receipt/bundle IDs, counts, accounting and notices. `--include-bundle` is an
explicit bounded JSON opt-in. `openardp context-receipt RECEIPT_ID` returns the exact
body-free receipt. F009 invokes the same service later.

**Rationale**: Large evidence should not be dumped by default, and interface code must not
duplicate business logic.

## Limits and known limitations

| Limit | Default | Accepted range |
|---|---:|---:|
| exact corpus scopes | 8 | 1–32 |
| discovered records | 2,000 | 1–10,000 |
| verified candidates | 100 | 1–512 |
| one evidence body | 1 MiB | 1 KiB–8 MiB |
| receipt decisions | 2,500 | 1–12,000 |
| canonical bundle | 4 MiB | 1 KiB–16 MiB |
| task text | 4,096 chars | fixed |

These are safety/reproducibility bounds, not throughput claims. FTS tokenization and the
conservative token estimator are explicitly profile-specific. Bounded rich scanning may
be slower than an index for large documents; measured need should precede a new index.
