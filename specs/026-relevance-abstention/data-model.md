# Data Model: Minimum Relevance and Explicit Abstention

## RelevancePolicy

Immutable application configuration defining:

- policy name and semantic version;
- integer score scale and minimum numerator;
- maximum task signals and maximum signal characters;
- frozen function-word and volatile-time signal sets;
- ordinary and identifier signal weights;
- canonical policy identity over all fields.

Validation requires sorted unique sets, positive bounds, a floor within the score scale and a reproducible config hash.

## RelevanceSignal

One normalized task signal containing:

- normalized token;
- class (`ordinary`, `identifier`, `volatile_time`);
- positive integer weight.

Signals are sorted unique by normalized token. They retain no source body and are not persisted independently.

## CandidateRelevance

Body-free observation for one verified candidate:

- exact policy identity;
- total and matched signal counts;
- total and matched integer weights;
- scaled integer score;
- volatile-time requirement status;
- `meets_minimum` decision.

The score is derived by integer division for display only. Eligibility uses exact cross-multiplication so rounding never
changes the decision.

## ContextCandidate extension

The existing internal candidate gains an optional `CandidateRelevance`. Legacy candidate sources leave it absent. The
F026 decorator supplies it for every textual/structured candidate it returns. Evidence identity, provenance, trust,
freshness, source order and body handle remain unchanged.

## Receipt relevance extension

One existing `ReceiptDecision.extensions` entry under a fixed absolute namespace records:

- policy ID;
- matched/total weights and counts;
- scaled score;
- threshold outcome.

No task text, token values or evidence body is emitted. This applies to selected, omitted and insufficient-relevance
decisions produced by the F026 algorithm profile.

## Evidence abstention

Derived state, not a stored entity:

- selected count is zero;
- no failure occurred;
- discovery was empty or every otherwise eligible candidate failed relevance;
- bundle warning and receipt notice both contain `no_relevant_evidence`;
- truncation, when present, remains separately disclosed.

## State flow

```text
discovered
  -> stale                     (freshness)
  -> rejected trust/sensitivity
  -> rejected duplicate
  -> rejected relevance
  -> eligible
       -> selected
       -> omitted by budget

empty discovery OR all otherwise eligible rejected relevance
  -> successful evidence abstention
```
