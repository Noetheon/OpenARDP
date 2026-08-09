# F024 contract surfaces

F024 adds no runtime API or public package module. Its governed interchange and evidence contracts are:

- [`corpus-lock.schema.json`](../../../corpora/realworld/v0.1.0/corpus-lock.schema.json) for the closed, exact corpus lock;
- [`protocol.json`](../../../benchmarks/realworld-corpus/v0.1.0/protocol.json) for the frozen structural benchmark;
- [`baseline.json`](../../../benchmarks/realworld-corpus/v0.1.0/baseline.json) for pre-run facts; and
- the independent validators documented in the
  [real-world corpus guide](../../../docs/23_REALWORLD_CORPUS.md).

The CSV probe is benchmark-only and is not a stable ingestion API. F025 owns semantic-question and source-evaluation
contracts.
