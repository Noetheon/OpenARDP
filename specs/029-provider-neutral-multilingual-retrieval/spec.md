# Feature Specification: Provider-Neutral Multilingual Retrieval

**Feature Branch**: `codex/f029-provider-neutral-multilingual-retrieval`

**Created**: 2026-08-03

**Status**: Converged — publication pending

## Clarifications

- “Provider-neutral” means one narrow scoring port whose identity binds provider, model, exact revision, bundle digest,
  tokenizer/inference profile and score policy. OpenARDP evidence and receipts never depend on a vendor-specific vector
  format.
- The first concrete provider is the locally provisioned MIT-licensed `intfloat/multilingual-e5-small` revision
  `f470c6a1a906014160ece1968c484b275f0396de`. It is optional and absent from the default installation.
- The binding adapter performs asymmetric query/passage encoding using the upstream-required prefixes, mean pooling,
  L2 normalization and cosine similarity. It returns fixed-point scores only; embeddings are disposable worker memory.
- Semantic execution is explicit, offline and process-bounded. It never downloads a model, uses ambient caches, accepts
  remote code or sends source text over a network.
- F025 questions, support atoms, source roles and evaluation normalization remain byte-identical. F029 adds a new direct
  treatment and a comparison protocol; it does not rewrite ground truth or claim population-wide accuracy.
- F028 CSV is ingested through the ordinary product path, so Q15/Q16 are measured as product retrieval rather than a
  benchmark-only oracle.
- The exact lexical F027 profile remains the default and the paired baseline. Semantic retrieval is opt-in and cannot
  weaken exact identifier, temporal-signal, citation, trust, freshness, diversity or source-quota controls.
- Binding execution retained three immutable protocol/result generations: v0.1.0 exposed semantic-only source
  starvation, v0.2.0 proved hybrid/source-balanced non-regression but exposed generic-row shadowing, and v0.3.0 fixed
  RichEvidence precedence and passed the unchanged readiness gates. Earlier negative results remain authoritative records
  of their respective frozen protocols.

## User Stories

### US1 — Swap an optional semantic provider without changing evidence contracts (P1)

As a local operator, I can bind one reviewed semantic provider through a stable port while exact source bytes, blocks,
rich projections, citations and context contracts remain provider-independent.

**Independent test**: run two synthetic provider implementations over the same verified corpus and prove that only the
provider recipe/score observations change; source and evidence identities remain exact.

### US2 — Retrieve paraphrases and German questions against English evidence (P1)

As an evaluator, I can submit untouched F025 questions and obtain bounded evidence from a multilingual semantic profile
without manual keywords or hidden translation.

**Independent test**: compare F027 direct and F029 direct treatments over all nineteen frozen questions, including both
German cross-language questions and CSV evidence.

### US3 — Abstain safely and preserve exact evidence (P1)

As a safety-conscious user, low-score results and unmet volatile-time constraints yield explicit no-evidence outcomes,
while every selected semantic hit is reverified from CAS and remains subject to F027 allocation.

**Independent test**: unrelated, future-year and live/current questions produce no selected evidence; corruption,
provider drift, network attempts, malformed output and resource overflow fail closed without body leakage.

### US4 — Reproduce an honest provider comparison (P1)

As a maintainer, I can independently validate a body-free result that compares the unchanged lexical baseline and the
optional provider under frozen thresholds, two fresh workspaces and exact input/model identities.

**Independent test**: a stdlib-only validator recomputes coverage, metrics, gates, decision, hashes and report; changing
any favorable or unfavorable row invalidates the result.

## Functional Requirements

- **FR-001**: Add a narrow semantic-scoring port with exact recipe identity, bounded batch input and fixed-point output.
- **FR-002**: Add at least a deterministic fake/test provider and one real optional local E5 adapter behind that port.
- **FR-003**: Keep core dependencies provider-free; semantic runtime dependencies live in a separately locked extra.
- **FR-004**: Provision model files only by explicit connected command from an exact upstream revision and committed
  hashes; runtime accepts only a complete independently verified offline bundle.
- **FR-005**: The runtime MUST set offline mode, reject remote code and links, deny socket creation before provider import,
  and enforce wall time, text count, text bytes, batch, token, response and process bounds.
- **FR-006**: Candidate enumeration MUST load only exact requested snapshot scopes and reverify each text/rich evidence
  object plus its catalog/native parent before sending text to the provider.
- **FR-007**: Model inputs are untrusted data with fixed `query: ` and `passage: ` prefixes; document content cannot alter
  provider options or initiate tools.
- **FR-008**: Passage embeddings remain an in-memory disposable cache keyed by exact evidence object and provider recipe;
  no universal vector, catalog column, public schema or authoritative embedding artifact is introduced.
- **FR-009**: Convert cosine similarity to bounded integer millionths using a documented quantizer and deterministic total
  order; raw tensors/vectors never enter results or receipts.
- **FR-010**: Apply a frozen minimum semantic score and exact volatile-time-signal guard before selection; empty eligible
  results MUST emit explicit semantic abstention.
- **FR-011**: Reuse F027 exact-body deduplication, ranked prefix, source quota and fair round-robin after semantic scoring.
- **FR-012**: Selected bodies/citations MUST still resolve through existing exact CAS/catalog product services.
- **FR-013**: The default CLI/compiler profile remains F027 lexical. Semantic execution requires explicit provider/bundle
  configuration and replay rejects a missing or mismatched provider identity.
- **FR-014**: Historical F025/F026/F027 result identities and validators remain byte-compatible and green.
- **FR-015**: Ingest all supported F024 assets including CSV through F028 for the F029 run; the PDF still requires the
  exact F023 offline bundle.
- **FR-016**: Freeze a new comparison protocol before the binding run while reusing F025 corpus, question-set and support
  ground truth byte-for-byte.
- **FR-017**: Evaluate F027 direct and F029 direct under the same question text, corpus, budget, candidate/decision limits,
  evidence evaluator and source-fitness rules; no operator query may count as F029 semantic success.
- **FR-018**: Report all nineteen questions, language/stratum/format slices, answer-support recall, full support, precision,
  MRR, source recall, citation integrity, unsupported abstention, runtime, peak RSS and cache reuse.
- **FR-019**: A decision MUST require complete citation integrity, correct unsupported abstention, deterministic semantic
  projections and non-regression of overall support/source recall; multilingual improvement is reported separately.
- **FR-020**: Binding execution MUST run twice in fresh workspaces with the same verified provider bundle and retain every
  negative row, failure and capability gap.
- **FR-021**: Results are body-free and exclude paths, usernames, hostnames, queries, answers, evidence text, vectors,
  secrets, raw exceptions and model tracebacks.
- **FR-022**: The independent validator uses only the standard library and imports neither provider nor producer.
- **FR-023**: Unit/contract/security tests remain small and offline; CI never downloads or executes the 493 MiB model.
- **FR-024**: Update ADR, docs, licenses, lockfile, repository governance and changelog; run full convergence and all gates.

## Edge Cases

- Empty query, too many or oversized passages, duplicate evidence/object IDs and malformed provider response.
- Score at, immediately below and immediately above the frozen floor; quantization and negative cosine values.
- Same score across several documents; duplicate bodies; source quota and ranked-prefix boundaries.
- German question versus English passage, Unicode normalization and non-Latin supported model input.
- Identifier/date query where semantically similar content omits the exact volatile year or “today/live/latest” signal.
- Model directory link, missing/extra/changed asset, ambient Hugging Face cache, offline network attempt or remote-code flag.
- Worker timeout/crash, oversized IPC payload, cache-key collision and provider recipe drift on replay.
- Text, canonical JSON CSV records and rich projection bodies in the same exact snapshot.

## Success Criteria

- **SC-001**: Synthetic ports, security boundaries and fake providers cover 100% of score/limit/failure contracts without
  network or model assets.
- **SC-002**: The exact six-file F024 corpus, including all 1,656 CSV records, ingests in each fresh F029 workspace with
  unchanged corpus/question/protocol identities and exact citations.
- **SC-003**: Both unsupported questions abstain with zero selected items and an explicit semantic no-evidence notice.
- **SC-004**: Both German questions improve atom recall or full support over F027 direct, and no German supported row
  regresses relative to the lexical baseline.
- **SC-005**: Overall answer-support recall, full-support rate, source recall and citation integrity do not regress from
  F027 direct; every regression remains visible if the decision is negative.
- **SC-006**: Two fresh semantic projections are byte-identical after excluding descriptive timing/resource facts.
- **SC-007**: Model bundle verification is exact, runtime is offline, and selected evidence contains no vector/body leak.
- **SC-008**: Full repository quality remains at least 85% coverage and Linux/macOS/Windows checks pass.

## Compatibility

This feature is additive. It changes no source, block, evidence, context schema, catalog revision, default provider,
persisted identifier algorithm or cloud policy. Existing lexical receipts replay with their historical algorithm identity.
Semantic receipts bind the exact optional provider recipe and fail closed when that runtime is unavailable.
