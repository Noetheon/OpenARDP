# F028 Contract Note

F028 adds no public interchange schema. The stable product boundary is the existing provider-neutral `ParserAdapter`,
`ParsedTextDocument`, F002 `ContentBlock`, local CLI and immutable representation contracts.

The new reviewed behavior is `text/csv` -> ordered canonical JSON-text `table` blocks with `openardp-csv-v1` provenance.
Original CSV bytes remain the native artifact. These blocks are evidence projections, not an exported CSV replacement.
