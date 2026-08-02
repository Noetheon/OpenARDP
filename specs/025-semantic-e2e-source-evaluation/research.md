# Research: Semantic End-to-End Source Evaluation

## Decision 1 — Evaluate the delivered evidence layer, not an answer-generating model

**Decision**: The binding use case ends with deterministic answer-support and citation/source-fitness judgments over a
bounded `ContextBundle`. Reference answers make the task understandable but are never compared with generated prose.

**Rationale**: OpenARDP's delivered purpose is exact local evidence preparation. Introducing a cloud or arbitrary local
LLM would measure model/prompt behavior, add nondeterminism and violate the provider/default-network boundary.

**Rejected**: OpenAI/API grading, local unpinned generative models, exact string comparison of generated answers and
human scoring performed only after seeing output.

## Decision 2 — Freeze three clearly separated treatments

1. `exhaustive_oracle`: confirms every declared support atom exists in its locked source and sets the attainable upper
   bound. It is benchmark infrastructure, not product behavior.
2. `openardp_direct`: passes the untouched natural-language question to the delivered context compiler.
3. `openardp_operator`: passes only the question's pre-frozen human-selected lexical terms under identical product
   limits. It measures assisted evidence preparation and is never called semantic retrieval.

There is no post-run translation, query expansion, stemming, synonym injection, reranker or threshold tuning.

## Decision 3 — Nineteen questions cover realistic successes and failure modes

| ID | Language/stratum | Expected source(s) | Frozen intent |
|---|---|---|---|
| Q01 | EN direct | NASA ethical-AI PDF | Name the six initial ethical-AI principles. |
| Q02 | EN paraphrase | NASA ethical-AI PDF | Identify who retains control over AI for the foreseeable future. |
| Q03 | EN source discrimination | NASA ethical-AI PDF | Identify the external baseline framework and why it was selected. |
| Q04 | DE cross-language | NASA ethical-AI PDF | Find the additional NASA-specific robustness principle. |
| Q05 | EN direct | NASA strategic-planning DOCX | Name the five best workshop test cases. |
| Q06 | EN paraphrase | NASA strategic-planning DOCX | Identify the common capability across most top-rated cases. |
| Q07 | EN direct | NASA strategic-planning DOCX | Name the four classification criteria. |
| Q08 | DE cross-language | NASA strategic-planning DOCX | Explain how ten key challenges were formed from seven plus three. |
| Q09 | EN direct | NASA open-science PPTX | Name the three “team sport” roles. |
| Q10 | EN paraphrase | NASA open-science PPTX | Identify the key knowledge-management problem. |
| Q11 | EN direct | NASA open-science PPTX | Name the three highlighted open-science focus concepts. |
| Q12 | EN multi-source | ethical-AI PDF + open-science PPTX | Combine human oversight/documentation with systematic capture/reuse. |
| Q13 | EN temporal/source | CISA KEV README | State update timing relative to the canonical KEV source. |
| Q14 | EN source discrimination | CISA CC0 text | Determine whether CC0 waives trademarks or warrants accuracy. |
| Q15 | EN direct/coverage | CISA KEV CSV | Give Log4Shell required action and due date. |
| Q16 | EN direct/coverage | CISA KEV CSV | Give PAN-OS ransomware-use status and due date. |
| Q17 | EN unsupported | none | Ask for a nonexistent NASA 2027 AGI deployment budget. |
| Q18 | EN unsupported/current | none | Ask for today's most recently added live KEV item from a frozen corpus. |
| Q19 | EN source discrimination | CISA KEV README | Determine whether additions/deletions belong in repository PRs. |

This set intentionally favors diagnosability over statistical representativeness. It covers all six F024 formats, but
nineteen questions cannot establish population-wide semantic accuracy.

## Decision 4 — Ground truth is exact, minimal and reviewable

Each answerable question declares minimal support atoms. Each atom has one expected asset and one or more accepted exact
normalized variants. Full support requires every required atom; multi-source full support additionally requires every
required source. Unsupported questions declare no atoms and reward abstention.

Normalization is limited to Unicode NFC, case-folding and whitespace collapse. It does not remove punctuation, stem,
translate or infer synonyms. The exact reference answer is documentation; support atoms are authoritative evaluation
inputs.

Observed source facts used to freeze atoms include:

- PDF: six principles include Fair; Explainable and Transparent; Accountable; Secure and Safe; Human-Centric and
  Societally Beneficial; and Scientifically and Ethically/Technically Robust. Gartner was selected because it generalized
  well, avoided overlap and mapped succinctly to NASA. Humans must remain in charge for the foreseeable future.
- DOCX: five best cases cover Decadal Survey priorities, new science topics, keyword assignment, observation capability
  and expertise discovery. NLP is common to most top-rated cases. Four criteria are technical feasibility, data
  availability/sufficiency, explainability and value to customer. Seven selected challenges plus three organizer-added
  challenges produced ten.
- PPTX: the “team sport” roles are Data Engineers, ML Engineers and Subject Matter Experts. The key takeaway identifies
  ad-hoc information sprawl and calls for systematic explicit process/artifact capture. Focus concepts are Open
  Participation, Accessibility and Reproducibility.
- CISA README: GitHub is updated shortly after the canonical source, typically on weekdays during US Eastern business
  hours when entries change, with synchronization expected within minutes; additions/deletions are not repository PRs.
- CC0 text: trademark rights are not waived and the work is supplied as-is without accuracy warranties.
- CSV snapshot: CVE-2021-44228 requires updates or removal from agency networks and is due 2021-12-24;
  CVE-2024-3400 has known ransomware use and due date 2024-04-19.

## Decision 5 — Question-specific source fitness is bounded fact, not universal credibility

For sources declared acceptable for a question, the fixture records:

- `publisher_authority`: official publisher evidence retained by F024;
- `directness`: underlying data/document versus general repository/license context;
- `temporal_fit`: fit for the historical snapshot or explicit lack of fit for a current/live claim;
- `integrity`: exact source/provenance verification; and
- `reuse_basis`: reviewed redistribution evidence.

Each dimension is an integer 0–2 and the total is descriptive. A source is relevant only when it contains a required
support atom for the question. High institutional authority cannot turn irrelevant content into relevant evidence.

## Decision 6 — Metrics and policy are frozen before execution

Per treatment and stratum:

- answer-support recall = covered required atoms / required atoms;
- full-support rate = fully supported answerable questions / answerable questions;
- evidence precision = relevant selected items / selected items;
- reciprocal rank = reciprocal position of first relevant item, zero when absent;
- expected-source recall = required expected sources with relevant evidence / required expected sources;
- citation integrity = exactly reverified selected citations / selected citations;
- abstention correctness = unsupported questions with zero selected evidence or explicit missing evidence / unsupported;
- source-fitness ratio = selected relevant-source score / maximum declared relevant-source score;
- coverage = exact rows for questions, treatments, formats, languages and strata.

The thresholds are exactly SC-006–SC-008 in `spec.md`. Aggregate ratios use exact integer numerators/denominators and
six-decimal half-even projections; the decision uses integer cross multiplication, not rounded floats.

## Decision 7 — Body-free raw evidence with independent recomputation

Rows retain question/treatment IDs, source asset keys, selected evidence IDs/order, atom IDs, boolean judgments, counts,
stable failure codes and bounded timings. They do not retain question text, reference answers or selected bodies; those
remain only in the public ground-truth fixture and committed source corpus.

The independent validator is stdlib-only, loads the frozen fixture/protocol itself and duplicates closed validation and
evaluation logic. It does not import the producer or pure evaluator.

## Decision 8 — Real execution is explicit; CI stays small and offline

The binding run uses the exact external F023 bundle and can parse the real PDF once per fresh run. Ordinary tests use
miniature generated text/rich observations and never need model weights, network or the binding execution. The committed
result makes semantic regression visible without making CI repeatedly pay the heavyweight parse cost.

## Decision 9 — Expected product limitation is not a benchmark defect

The current context compiler is exact lexical OR discovery with exact case-folded rescoring. It has no translation,
semantic embeddings, synonym model or explicit source-authority ranker. F025 is allowed—and expected—to return a
conditional or negative decision. Any follow-up capability must be a separate provider-neutral feature with its own
contracts; F025 does not implement it covertly.

## Decision 10 — GitHub billing remains an external publication boundary

PR #31 proved the exact F024 implementation SHA on Linux, macOS and Windows. Subsequent GitHub jobs were rejected before
runner allocation because of the account billing state. F025 local quality remains mandatory. Remote status is reported
exactly and branch protection is not weakened to fabricate green evidence.
