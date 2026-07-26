# Feature 008 — Context compiler and selection receipts

## Goal
Compile bounded evidence for a task and emit a deterministic, privacy-conscious selection receipt.

## Requirements
Inputs include task, corpus scope, byte/token budget, tokenizer identity, trust and retrieval policy. Outputs include selected references, order, omissions, rejection reasons, stale items, truncation and exact accounting. Source bodies remain delimited untrusted data. The receipt records algorithm/config/corpus snapshot but does not duplicate full source bodies or secrets. Deterministic baseline only; model rankers deferred.

## Tests
Stable replay; no budget overflow; tokenizer-version mismatch detected; stale derivation excluded; malicious instructions remain quoted data; high-value omissions visible; corrupted indexes fail closed or explicitly rebuild; empty corpus/query and cancellation behavior defined.
