# Research: Minimum Relevance and Explicit Abstention

## Decision 1 - Separate minimum relevance from ranking

**Decision**: F026 makes a binary candidate eligibility decision only. Existing total ordering remains unchanged for
surviving candidates.

**Rationale**: This directly resolves F025's zero-abstention failure while preserving a small, independently measurable
slice. Ranking and source allocation can then use proven relevance facts in F027 without conflating failure causes.

**Alternatives considered**:

- Implement ranking simultaneously: rejected because it makes non-regression failures impossible to attribute.
- Only reduce `max_candidates`: rejected because a smaller irrelevant bundle is still a false positive.

## Decision 2 - Exact weighted coverage with an integer floor

**Decision**: Normalize task and body with NFC plus casefold, extract bounded Unicode word/identifier tokens, remove a
frozen small function-word set, weight exact identifiers/dates/acronyms more heavily, and compare matched weight against
total weight using integer cross-multiplication. Repetition never increases coverage. Volatile-time intent tokens such as
`today`, `live`, `latest` and `current` are conjunctive constraints: every such signal in the task must occur exactly in
the candidate. A standalone four-digit calendar year from 1900 through 2200 is likewise a high-weight volatile
constraint and must occur exactly; this prevents a publisher name alone from satisfying a future-dated claim.

**Rationale**: It is deterministic, explainable and strong on identifiers while rejecting F025's incidental generic
overlap. It adds no linguistic provider and makes no semantic-equivalence claim.

**Alternatives considered**:

- BM25 threshold: rejected because scores are corpus-dependent and not comparable across text/rich candidate sources.
- Floating-point cosine/Jaccard: rejected because integer coverage is simpler to audit and cross-platform reproduce.
- Learned relevance or embeddings: rejected by F026 scope and ADR 0003's optional-provider boundary.

## Decision 3 - Verified decorator instead of changing source ports

**Decision**: Add one adapter decorator that gathers existing candidates, rereads their referenced objects through CAS,
computes relevance and attaches body-free observations. The existing `ContextCandidateSource` port remains unchanged.

**Rationale**: Both text FTS and rich projection candidates receive identical policy without duplicating their discovery
or weakening verification. No second implementation exists to justify a new public provider abstraction.

**Alternatives considered**:

- Add task/body scoring to every candidate source: rejected because policy logic and verification would diverge.
- Change the source port return type: rejected because it needlessly expands the public compatibility surface.

## Decision 4 - Existing extensions carry audit facts

**Decision**: Keep context/receipt versions unchanged. Relevance rejection decisions include one closed JSON object under
an absolute OpenARDP relevance namespace; the injected algorithm identity binds the full policy configuration.

**Rationale**: The experimental contract already provides namespaced extension data exactly for additive facts. Existing
fixtures and old persisted receipts remain valid without silent policy replay.

**Alternatives considered**:

- Add first-class receipt fields and bump the contract: rejected because F026 does not need a breaking decoder boundary.
- Store scores in catalog columns: rejected because relevance is per task, disposable and derivable.

## Decision 5 - Abstention is a successful, explicit zero-selection state

**Decision**: A valid compilation with no discovered candidates, or with all otherwise eligible candidates below the
floor, emits `no_relevant_evidence` notices in bundle and receipt. Trust-only rejection, integrity error, cancellation,
resource exhaustion and budget omission are not relevance abstention.

**Rationale**: This preserves operational truth and prevents a failed or unsafe run from appearing confidently empty.

**Alternatives considered**:

- Treat every empty bundle as abstention: rejected because it hides failures and restrictive trust policy.
- Raise an exception for no evidence: rejected because a genuine negative retrieval result is expected product behavior.

## Decision 6 - Freeze anti-overfitting comparison before implementation

**Decision**: The unchanged F025 IDs and direct questions Q02, Q03, Q06, Q13, Q14, Q19 plus unsupported Q17/Q18 form the
binding F026 slice. Runtime modules may not import benchmark modules or files.

**Rationale**: These rows prove the requested gain and the minimum safe non-regression boundary without changing ground
truth after results are known.

**Alternatives considered**:

- Tune against all support atoms during implementation: rejected as circular benchmark optimization.
- Use synthetic tests only: rejected because F025 exposed the defect on realistic documents.
