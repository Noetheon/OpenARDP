# Provider-Neutral Retrieval Benchmark v0.3.0

v0.3 preserves every v0.2 question, atom, judgment, model, score threshold, hybrid ordering and gate. The independently
valid v0.2 negative run remains committed. Adapter diagnostics proved that the correct Q04 and Q08 rich projections rank
first in their respective documents, but the product adapter preferred a generic catalog representation and therefore
never submitted the accepted RichEvidence projections to the provider.

This protocol freezes the contract repair `rich_then_text`: when an exact snapshot has accepted rich artifacts, semantic
enumeration verifies and scores those retrieval projections; generic text/CSV rows are used only when no rich artifact
exists. A model-free integration test covers this precedence. No evaluation or threshold changed after either negative
run.
