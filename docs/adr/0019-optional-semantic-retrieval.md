# ADR 0019: Add optional bounded provider-neutral semantic retrieval

Status: Accepted for Feature 029

Date: 2026-08-03

## Context

F025 proved that exact lexical retrieval misses paraphrases and German-to-English evidence. F026 added abstention, F027
added lexical allocation and F028 added CSV, but no reviewed provider boundary can score verified evidence semantically.
ADR 0003 requires embeddings to remain optional, model-specific and disposable.

## Decision

Feature 029 adds one narrow semantic scoring port. Provider recipes bind the exact model/revision, independently verified
offline bundle, inference profile, dimensions, limits and quantizer. Inputs are bounded query/passage text from exact
CAS-reverified snapshot evidence; outputs are fixed-point scores keyed to exact evidence/object IDs.

The first adapter is `intfloat/multilingual-e5-small` at revision
`f470c6a1a906014160ece1968c484b275f0396de`, using SafeTensors, local-only Transformers loading, upstream query/passage
prefixes, mean pooling, L2 normalization and cosine scoring. It runs in a spawned socket-denied process with bounded IPC,
time, batch, text and cache resources. Passage vectors exist only in that worker and disappear on close.

Semantic eligibility uses a frozen score floor plus the existing exact volatile-time guard. Accepted RichEvidence takes
precedence over generic rows. Before global Top-K, semantic candidates receive a ranked prefix, per-document cap and fair
document round-robin. Minimum-relevant F027 lexical candidates form a higher-priority fallback tier; F027 deduplication,
quota and fair allocation exhaust that tier before semantic additions. Returned evidence and citations remain the
existing exact objects. The default compiler remains provider-free lexical; semantic composition is explicit and replay
requires the same recipe and allocation/representation-precedence identity.

The model files remain outside Git. A committed source lock pins upstream revision, file hashes, byte sizes and MIT
license evidence; connected provisioning and offline runtime verification are separate operations.

## Compatibility

No workspace/catalog/public-schema revision or historical identity changes. Existing lexical receipts and validators are
unchanged. Removing the optional adapter leaves no persisted vectors or provider-specific evidence.

## Consequences

- Cross-language/paraphrase retrieval can be measured honestly against F025 without manual keyword substitution.
- The optional runtime adds roughly 493 MiB of model assets and substantial CPU/RAM cost.
- The v0.3 reference uses about 1.23 GB peak worker RSS and 2.65 times the F027 summed query wall time; repeated queries
  reuse 94.73 percent of scored passages after the first cache-building request.
- Dense similarity can still select plausible but unsupported evidence; exact abstention, provenance and frozen scoring
  remain mandatory, and a negative benchmark result is acceptable.

## Alternatives

- Hand-written translation/synonym rules were rejected as benchmark leakage.
- Cloud embeddings were rejected as a default privacy/cost/egress regression.
- Persisted universal vectors or a vector database were rejected as unnecessary and contrary to ADR 0003.
- Replacing FTS was rejected because exact identifiers and the lightweight default remain valuable.

## Feature 035 amendment: process-local preparation and exact additive budgeting

Feature 035 retains the decision above and adds an opt-in `1.3.0` execution profile for repeated queries over one exact
snapshot. The provider may prepare the ordered evidence/object identities once inside its already isolated process and
return only an opaque, recipe-bound handle. Later requests carry the query and handle, not the corpus bodies. Prepared
state is bounded by the existing provider limits, is never persisted, is invalidated on any snapshot, recipe, policy or
limit drift, and disappears when the worker closes or fails. Selected metadata is reconciled with the catalog and every
delivered body is still read and verified from authoritative CAS storage.

The same profile uses exact additive canonical-prefix accounting during greedy selection. This changes computational
work, not budget semantics: for the three versioned built-in estimators, each item and selection-trace fragment is
measured once and the two embedded decimal usage fields are solved to the same fixed point as complete bundle
reserialization. Cross-estimator equivalence tests require byte-identical bundles and receipts. Unknown estimators fail
closed; the `1.2.0` F029 path retains its historical full-reserialization behavior and identity.

Because profiling showed the retained lexical tier—not budgeting or warm E5 scoring—to dominate later queries, `1.3.0`
may also keep one bounded exact-snapshot rich-text cache in the compiler process. Query-specific lexical and relevance
scores are recomputed; returned matches are CAS-reverified. A catalog-native digest binds the accepted attempt and every
ordered reference/projection/retrieval object mapping, so warm lexical and semantic accelerators reconcile current
authoritative metadata without reconstructing the complete provider-native model graph. Snapshot heads are still read
for every compile, selected objects are still verified during bundle materialization, and fingerprint drift fails closed.
The cache is disposable derived data, contains no embedding and is never persisted or exposed in receipts.

This amendment does not authorize persistent embeddings, a provider-neutral vector store, weaker evidence verification,
mandatory semantic retrieval or a cloud-enabled default. The provider-free lexical profile remains the product default.
