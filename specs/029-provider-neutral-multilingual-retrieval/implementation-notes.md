# Implementation Notes: Provider-Neutral Multilingual Retrieval

## Acceptance criteria restatement

- Keep the provider optional, offline, model-specific and absent from default composition.
- Reverify exact text, CSV and accepted RichEvidence snapshot objects before provider scoring or selection.
- Bind every inference/admission/allocation fact to deterministic identities; persist neither vectors nor universal model
  claims.
- Retain F027 lexical evidence as a non-regressing higher-priority tier, then diversify eligible semantic candidates before
  the global Top-K and reapply F027 deduplication/quotas.
- Ingest all six F024 formats through product services, run unchanged F025 direct questions twice in fresh workspaces and
  independently validate body-free results.
- Require complete citations, unsupported abstention, deterministic rows, overall support/source non-regression and a
  strict improvement for each German question.
- Preserve negative evidence and disclose runtime, memory, cache and remaining claim limits.

## Delivered behavior

The implementation follows the domain/port/adapter/service boundary in the plan. `IsolatedE5SemanticProvider` owns the
optional Transformers/Torch runtime and disposable cache. `SemanticContextCandidateSource` performs Rich-first exact
enumeration and provider scoring; `HybridRetrievalCandidateSource` preserves minimum-relevant lexical candidates before
semantic additions. Receipt extensions expose only fixed-point score/policy/cache facts.

The first v0.1 binding result was negative because global semantic Top-128 preceded source diversity. v0.2 froze and
measured hybrid tiering plus pre-Top-K document balance, resolving all overall regressions. It remained negative because
the adapter preferred generic rows over accepted rich projections. A direct adapter diagnostic showed the unchanged Q04
and Q08 oracle projections ranked first within their documents at 0.817784 and 0.838364. v0.3 froze Rich-first precedence
without changing model, floor, questions or gates and passed every readiness condition. All three results remain committed
and independently valid.

## Exact binding outcome

- Decision: `PROVIDER_RETRIEVAL_READY`
- Full support: 7/17 F027 to 9/17 F029
- Atom recall: 8/23 F027 to 1/2 F029
- Source recall: 4/9 F027 to 13/18 F029
- Q04 and Q08: 0/1 to 1/1 atom recall and full support each
- Citation integrity and unsupported abstention: 1/1
- Semantic fresh-run projection: identical
- Provider requests/passages/cache hits: 19 / 60,914 / 57,708
- Peak worker RSS: 1,233,502,208 bytes
- F027/F029 summed query wall time: 65.79 / 174.41 seconds

## Tradeoffs and residual risks

The provider adds a 492.8 MB external model bundle, roughly 1.23 GB peak worker RSS and about 2.65x query wall time in
this cold-workspace comparison. Cache reuse makes repeated queries materially cheaper than first-time passage encoding,
but no persisted vector index exists. The benchmark is deliberately small, provider-specific and evidence-retrieval-only;
it does not validate answer generation, broad domains or production latency. The lexical default remains the appropriate
cheap path for exact identifiers and unsupported provider environments.

## Convergence evidence

- `uv run ruff check .`: passed
- `uv run ruff format --check .`: 369 files formatted
- `uv run mypy src`: 106 source files, no issues
- `uv run pre-commit run --all-files`: all hooks passed, including no-network pytest and 85.24% branch coverage
- `uv run python scripts/validate_repository.py .`: passed
- Independent v0.1.0/v0.2.0/v0.3.0 validators: passed with the two negative and one ready decisions preserved
- Release evidence, 125-component SBOM/review, wheel and sdist: regenerated and independently validated
- Exact external E5 bundle: 6 files, 492,794,646 bytes; opt-in offline integration passed
