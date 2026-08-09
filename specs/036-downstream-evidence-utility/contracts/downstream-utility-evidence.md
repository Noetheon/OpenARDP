# Downstream Utility Evidence Contract

The normative protocol is `benchmarks/downstream-utility/v0.1.0/protocol.json`. A result package contains exactly:

- `observations.json`: bounded per-question/per-budget review facts;
- `summary.json`: independently recomputable aggregates and time-to-ready comparisons;
- `decision.json`: separate validity, F025 candidate and F034 generalization verdicts;
- `report.md`: human-readable projection with limitations;
- `run-manifest.json`: exact protocol/input/output identities, written last.

Trusted answerable completion at budget K requires all required atoms and required sources in the first K selected items,
counting only relevant evidence with a valid citation. Safe unsupported completion requires explicit abstention and no
selected item. Missing support is a task miss, not an evaluator failure.

The complete `1, 3, 5, 10, 64` budget curve is binding; budget 3 is the predeclared F025 decision point. Time-to-ready is
the retrieval wall duration for the unchanged F035 warm population and excludes any inferred human reading time.

The producer reads but never mutates exact F034/F035 evidence. Output is body-free and may not contain document/question
text, reference answers, absolute paths, embeddings or provider payloads. The independent validator uses only the Python
standard library and may not import producer/evaluator modules. It rejects unexpected files, symlinks, duplicate JSON
members, unknown fields, invalid ordering/arithmetic, identity drift, incomplete treatment/run coverage or result-led
protocol changes.

This contract measures deterministic evidence-review utility. It does not establish human comprehension, generated-answer
correctness, domain readiness or universal retrieval quality.
