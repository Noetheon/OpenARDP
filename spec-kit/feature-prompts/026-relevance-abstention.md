# Feature prompt: 026 Relevance and abstention

Implement the first remediation selected from F025: add a frozen minimum-relevance policy to bounded context discovery
and make zero-supported-evidence outcomes an explicit abstention. The policy must be deterministic, explainable,
provider-free, independent of benchmark ground truth and compatible with existing exact evidence verification. It must
eliminate the two F025 unsupported-question false positives without regressing questions already fully supported by the
direct treatment. Ranking diversification, source quotas, CSV ingestion, query translation, embeddings and other
semantic providers remain separate follow-up features.
