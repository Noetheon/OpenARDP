# Data Model: Semantic End-to-End Source Evaluation

## SemanticQuestionSet

- `schema_version`: closed contract revision.
- `benchmark_version`: exact F025 protocol version.
- `corpus_id`: pinned F024 identity.
- `questions`: sorted non-empty `SemanticQuestion` records.
- `question_set_id`: RFC 8785/SHA-256 identity over all preceding semantic fields.

## SemanticQuestion

- `question_id`: stable `QNN` identifier.
- `language`: `en` or `de`.
- `stratum`: direct, paraphrase, multi-source, source-discrimination, cross-language or unsupported.
- `question`: public natural-language task.
- `operator_query`: pre-run human lexical terms, empty only for intentionally unsupported/current tasks where applicable.
- `reference_answer`: concise public source-backed answer or explicit unsupported rationale.
- `answerable`: boolean.
- `temporal_scope`: frozen snapshot, historical document or current/live.
- `required_formats`: exact format coverage.
- `required_sources`: source asset keys necessary for full support.
- `acceptable_sources`: any additional source that may validly support the answer.
- `support_atoms`: sorted `SupportAtom` records; empty exactly when `answerable=false`.
- `source_fitness`: question-specific dimensions for declared relevant sources.

## SupportAtom

- `atom_id`: unique within the question.
- `source_key`: one exact F024 asset.
- `variants`: one or more exact normalized source substrings.
- `required`: always true in v0.1.0; field is explicit for auditability.

An atom is covered when any one variant occurs in one selected evidence body from the declared source after NFC,
case-fold and whitespace-collapse normalization.

## SourceFitness

- `source_key`: F024 asset key.
- `publisher_authority`, `directness`, `temporal_fit`, `integrity`, `reuse_basis`: integer 0–2.
- `rationale`: short factual explanation retained only in ground truth, not raw result rows.

Fitness is evaluated only for evidence already relevant to the question. It cannot convert irrelevant official material
into support.

## SemanticObservation

- `observation_id`: canonical identity over every semantic field except measured duration.
- `question_id`, `treatment`: closed coverage key.
- `outcome`: pass, unsupported-format or failed.
- `failure_category`: stable body-free code or null.
- `selected`: ordered `SelectedEvidenceObservation` records.
- `required_atom_count`, `covered_atom_ids`, `required_source_count`, `covered_source_keys`.
- `full_support`, `abstained`, `citation_integrity_complete`.
- exact numerators/denominators for relevance, rank and source fitness.
- `wall_ns`, `cpu_ns`, `peak_rss_bytes`: descriptive environment-bounded measurements excluded from semantic identity.

## SelectedEvidenceObservation

- `order`: final context order.
- `evidence_id`: stable block or projection identity.
- `source_key`: mapped F024 asset.
- `representation`: exact text, rich projection or visual handle.
- `anchor_type`: body-free anchor class.
- `covered_atom_ids`: exact matching atoms.
- `relevant`, `citation_valid`: booleans.
- `source_fitness_score`, `source_fitness_max`: integers for relevant expected sources, otherwise zero.

## SemanticSummary

- corpus/question/result identities and closed coverage facts.
- per-treatment and per-stratum integer metric counts plus deterministic ratio projections.
- format/language coverage and explicit capability gaps.
- deterministic/non-timing agreement across two executions.

## SemanticDecision

- `decision`: READY, CONDITIONALLY_READY or NOT_READY enum.
- `failures`: hard integrity/coverage/oracle/network failures.
- `blockers`: threshold or capability gaps.
- `satisfied`: proven policy facts.

## RunManifest

- benchmark/question/corpus/model identities.
- body-free environment buckets and total duration.
- exact hashes/lengths of observations, summary, decision and report.
- canonical `run_id` over all preceding fields.
