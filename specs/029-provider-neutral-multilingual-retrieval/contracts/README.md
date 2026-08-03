# F029 Contract Boundary

The production contract is the typed Python `SemanticRetrievalProvider` port. Inputs are one bounded untrusted query plus
exact-ID verified passages. Output is a complete unique score tuple bound to `SemanticProviderRecipe`; provider errors are
sanitized. Context bundles continue to contain only exact evidence and body-free receipt facts.

The benchmark result is a closed feature-local JSON contract independently validated from the unchanged F025 inputs.
It is not promoted to a public stable schema.
