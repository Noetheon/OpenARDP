# Semantic end-to-end benchmark v0.1.0

This frozen diagnostic benchmark measures whether the delivered local OpenARDP evidence layer can ingest the exact F024
corpus, retrieve useful evidence for nineteen realistic questions, preserve citations and identify source fitness. It
does not generate prose answers and it does not claim population-wide semantic accuracy.

`openardp_direct` passes the untouched question. `openardp_operator` passes human-selected terms frozen before execution
and therefore measures manual lexical assistance, not semantic retrieval. `exhaustive_oracle` only proves that declared
answer atoms exist in the locked bytes; it is not product behavior.

CSV is intentionally retained as `unsupported_format`: OpenARDP has no stable CSV ingestion adapter. The benchmark does
not convert CSV to text or inject its rows into the product workspace. German, unanswerable, current/live and irrelevant-
selection failures remain decision inputs. Results contain identifiers, counts and booleans, never source bodies.

See `docs/24_SEMANTIC_E2E_EVALUATION.md` for exact offline execution and validation commands.
