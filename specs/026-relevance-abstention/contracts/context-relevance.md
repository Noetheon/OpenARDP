# Context relevance contract

## Compatibility boundary

F026 does not change the context bundle or selection receipt version. It uses the existing namespaced `extensions`
object and a distinct `AlgorithmIdentity`. Legacy lexical context remains the default algorithm identity and can verify
historical receipts.

## Algorithm profile

The F026 profile identity binds:

- relevance-policy identity and all scoring inputs;
- candidate-source identities/order;
- existing selection ordering and budget reserves;
- abstention notice semantics.

Replay requires exact equality with the recorded identity.

## Relevance extension

Namespace: `https://openardp.example/ns/context-relevance/v1`

Closed body-free value:

```json
{
  "matched_signals": 2,
  "matched_weight": 2,
  "meets_minimum": true,
  "policy_id": "sha256:...",
  "score_millionths": 400000,
  "total_signals": 5,
  "total_weight": 5,
  "volatile_time_matched": true
}
```

The extension never contains task terms, source bodies, snippets, paths or provider data.

## Stable outcomes

- `insufficient_relevance`: rejected decision for a verified, otherwise admissible candidate below the floor.
- `no_relevant_evidence`: receipt notice and bundle warning for genuine evidence abstention.
- Existing integrity, trust, sensitivity, stale, duplicate, limit and cancellation outcomes retain their current meaning.

## Invariants

1. One candidate appears in exactly one decision partition.
2. Trust/sensitivity/freshness reasons are not overwritten by relevance.
3. Eligibility uses exact integer cross-multiplication.
4. An absent relevance observation under the F026 profile fails closed for textual/structured candidates.
5. Every scored body is CAS-verified before normalization.
