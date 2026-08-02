# Feature 025 prompt — Semantic end-to-end source evaluation

## Authoritative request

Evaluate whether the delivered OpenARDP document-intelligence layer can turn realistic natural-language questions into
answer-supporting, source-grounded evidence over the exact F024 corpus, and report the result honestly even when current
lexical retrieval, format coverage or source-quality discrimination is insufficient.

## Frozen scope

- Pin F024 corpus identity `sha256:5e505148c7e9004a9c1ae7bd68c66addfc9ae3377be7e3057a81d7a1996649bd` and the
  validated F023 PDF model bundle; never substitute live or synthetic document bodies in the binding run.
- Freeze a redistributable, human-reviewed question and ground-truth set before execution. Cover direct facts,
  paraphrases, multi-source synthesis, source discrimination, unsupported questions and German cross-language prompts.
- Exercise the actual offline product path: exact source ingestion, provider-native rich evidence, verified lexical
  candidate discovery, bounded context compilation, provenance/anchor retrieval and replay.
- Compare natural-language questions used directly with an explicitly labelled frozen operator-keyword treatment and an
  exhaustive ground-truth oracle. Never describe manual query formulation as semantic retrieval.
- Evaluate answer-support coverage, evidence precision/rank, citation integrity, expected-source coverage, unsupported-
  question abstention and question-specific source fitness with deterministic, independently reproducible judgments.
- Treat CSV as an explicit product-coverage test. The F024 benchmark-only CSV probe is not silently promoted into a
  stable OpenARDP ingestion or retrieval API.
- Retain all unfavorable results. Do not add embeddings, an LLM answer generator, cloud calls or thresholds after seeing
  the binding measurements merely to obtain a favorable decision.

## Completion boundary

Complete the full Spec Kit lifecycle, tests-first benchmark and independent validator, one real offline run, frozen raw
evidence, full local gates and a private pull request. A GitHub Actions runner-allocation failure caused solely by the
documented account billing state remains external evidence and must not be misreported as a code failure or bypassed by
weakening repository protection.
