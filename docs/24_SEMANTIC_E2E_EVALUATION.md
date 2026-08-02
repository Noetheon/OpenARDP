# Semantic End-to-End and Source Evaluation

Feature 025 asks the product question left open by the structural F024 baseline: can the delivered OpenARDP evidence
layer prepare useful, exactly cited evidence for realistic questions? The independently validated reference decision is
`SEMANTIC_E2E_NOT_READY`. This is a bounded product-quality result, not a failure of the benchmark and not a claim that
the persistence/provenance foundation has no value.

## Method

The frozen set contains nineteen human-reviewed questions over the exact six-file, 6,634,970-byte F024 NASA/CISA
corpus. It covers direct facts, paraphrases, source discrimination, multi-source synthesis, two German prompts, two
unanswerable prompts and two CSV-dependent facts. Minimal answer-support atoms were verified against the exact source
bytes before scoring. Normalization is only Unicode NFC, case folding and whitespace collapse.

Each supported source is ingested into one fresh local workspace. The benchmark then compares:

- `openardp_direct`: the untouched natural-language question;
- `openardp_operator`: human-selected lexical terms frozen before execution;
- `exhaustive_oracle`: an existence check over exact source evidence, never product behavior.

Both product treatments use the same `EXACT` compiler, 256 KiB budget, 64-candidate cap and five supported document
scopes. No LLM, embedding, translation, query expansion, reranker, network access or post-run relevance judgment is
used. CSV stays `unsupported_format`; the benchmark never converts it into a supported product document.

## Reference result

The binding macOS arm64 run took 241,417,797,959 ns across two fresh workspaces. Every non-timing observation and
identity matched. All selected citations re-resolved to exact CAS/catalog evidence and all five supported formats
ingested successfully.

| Treatment | Full support | Atom recall | Precision | MRR | Source recall | Citations | Abstention | German recall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Direct question | 35.2941% | 32.6087% | 1.1029% | 28.8622% | 50.0000% | 100.0000% | 0.0000% | 0.0000% |
| Operator terms | 82.3529% | 86.9565% | 5.0704% | 78.9661% | 88.8889% | 100.0000% | 0.0000% | 100.0000% |

The direct path fully supported Q02, Q03, Q06, Q13, Q14 and Q19. It failed all six-principle coverage, both German
questions, the multi-source question and the presentation questions. Generic OR terms filled the 64-candidate cap for
nearly every question; both unanswerable questions therefore selected irrelevant context instead of abstaining.

Frozen operator terms substantially improve evidence preparation, but this is manual assistance. Q09 still retrieves
only the Subject Matter Expert atom before the cap, while Q15/Q16 remain unsupported CSV rows. Operator atom recall
86.9565% and source recall 88.8889% narrowly miss their respective 90% conditional thresholds, so the outcome remains
`NOT_READY` rather than relaxing policy after seeing the result.

## What the result means

OpenARDP's local ingestion, immutable storage, exact provenance, citation resolution and offline rich-document pipeline
work on the real corpus. The current lexical context selector does not yet turn that trustworthy evidence into
high-quality semantic question support. Persisting parsed documents is still useful for exact navigation, reuse and
operator-driven evidence work; it is not yet sufficient for a self-directed semantic research assistant.

The evidence supports a separate follow-up feature, in this order:

1. add explicit abstention/minimum-relevance logic so generic overlap cannot flood context;
2. improve lexical ranking/diversity and multi-source allocation before increasing the candidate cap;
3. add a stable CSV ingestion adapter if KEV/tabular use cases are in scope;
4. evaluate a provider-neutral optional semantic/translation retrieval stage against this unchanged benchmark;
5. retain citation verification and source-fitness scoring after any retrieval improvement.

The nineteen-question set is diagnostic, not statistically representative. Source fitness describes suitability for
one frozen claim; it is not a universal credibility score, legal advice or publisher endorsement. F015 `NO-GO`, F020
`CONDITIONALLY_WORTHWHILE` and F024 `REALWORLD_BASELINE_READY` remain historical evidence with different scopes.

## Reproduction

```bash
uv run python scripts/validate_semantic_e2e_benchmark.py --inputs-only
uv run python scripts/validate_semantic_e2e_benchmark.py \
  --result benchmarks/semantic-e2e/v0.1.0/results/reference-macos-arm64
```

Re-running the heavyweight product path additionally requires the exact external F023 PDF bundle. See the F025
quickstart for the explicit command.
