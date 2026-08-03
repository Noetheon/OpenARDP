# Feature prompt 027: lexical ranking and diversity

Implement deterministic provider-free ranking after F026 relevance filtering. Rank stronger lexical evidence first,
deduplicate exact evidence bodies, interleave eligible documents fairly and enforce a declared per-document quota. Preserve
explicit abstention, source truth, reproducibility and historical F026 replay. Evaluate against the unchanged F025 corpus,
questions, oracle and protocol. Do not add CSV ingestion, translation, embeddings, rerankers or network providers.
