# Data Model: Provider-Neutral Multilingual Retrieval

- `SemanticProviderRecipe`: provider/model/revision, bundle ID, dimension, prefixes, pooling, normalization, quantizer,
  library versions and config hash.
- `SemanticRetrievalLimits`: maximum passages, text bytes, passage bytes, tokens, batch size, cache entries, response
  entries and wall time.
- `SemanticRetrievalPolicy`: minimum score, top-k, volatile-signal guard and exact F027 allocation-policy identity.
- `SemanticPassage`: exact evidence ID, object ID and bounded verified text used only at the provider call boundary.
- `SemanticScore`: evidence/object ID, signed score millionths and provider recipe ID; contains no text or vector.
- `SemanticCandidateObservation`: optional internal candidate field used for receipt extensions and total ordering.
- `EmbeddingBundleSourceLock`: exact upstream revision/files/hashes/license/limits; independent installation trust root.

No new persistent database entity or public interchange schema is introduced.
