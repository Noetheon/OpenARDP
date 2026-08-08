# Feature Specification: Semantic Retrieval Product Surface

**Feature Branch**: `codex/f030-semantic-retrieval-product-surface`

**Created**: 2026-08-08

**Status**: Converged — publication pending

## User Stories

### US1 — Use semantic context explicitly from the CLI (P1)

As a local operator, I can opt into the validated multilingual hybrid retrieval profile for a bounded context request
while the existing lexical command remains the default and produces unchanged results.

**Independent test**: compile the same local corpus through the default and explicit semantic profiles, prove the
default receipt retains the F027 algorithm identity, and prove the semantic receipt binds the exact F029 provider recipe.

### US2 — Offer semantic retrieval safely to a local MCP client (P1)

As a local MCP operator, I can authorize one verified semantic capability when starting the server and let a client
select it per context request without granting that client filesystem, model-configuration or network authority.

**Independent test**: inspect the advertised tool contract and run lexical and semantic requests through one session;
semantic requests fail closed when the server lacks the capability, while no request accepts a path or provider option.

### US3 — Replay and fail closed across provider drift (P1)

As an auditor, I can replay a semantic receipt only with a provider whose complete recipe identity matches the original
selection, and receive a stable body-free failure when the bundle, source lock, runtime recipe or requested profile differs.

**Independent test**: replay a persisted semantic receipt with the matching fake provider and with drifted recipes,
missing configuration and explicit lexical selection; only the exact match succeeds.

### US4 — Understand operational cost before enabling the profile (P1)

As a maintainer, I can independently validate body-free measurements for cold and warm semantic compilation, provider
cache reuse, peak worker memory and latency on the frozen redistributable workload.

**Independent test**: validate two fresh runs against a frozen protocol and recompute all measurements, identities,
limits and claims without importing the product or model runtime.

## Functional Requirements

- **FR-001**: The existing context command MUST expose an explicit lexical or semantic retrieval-profile choice and MUST
  continue to select lexical retrieval when the choice is omitted.
- **FR-002**: Semantic CLI compilation MUST require an explicit local model-bundle path and exact source-lock path; the
  two values MUST be supplied together and MUST NOT be read from ambient model caches or environment defaults.
- **FR-003**: Semantic composition MUST use the exact F029 hybrid, source-balanced, Rich-first retrieval policy without
  changing its score floor, limits, allocation, abstention or evidence-verification behavior.
- **FR-004**: Every semantic compile MUST verify the complete offline bundle before provider construction and bind the
  receipt to the exact provider recipe and algorithm identity.
- **FR-005**: CLI semantic replay MUST infer or validate the persisted retrieval profile, require an explicitly configured
  semantic provider, and reject every provider recipe or algorithm mismatch before returning replayed evidence.
- **FR-006**: Lexical compilation and lexical replay MUST reject semantic-only configuration so configuration mistakes
  cannot silently change the requested behavior.
- **FR-007**: MCP server startup MAY authorize one semantic capability through local process arguments supplied as an
  all-or-none bundle/source-lock pair; the default server remains provider-free.
- **FR-008**: The MCP `compile_context` request MAY select `lexical` or `semantic`, defaults to `lexical`, and MUST NOT
  accept filesystem paths, provider names, model identifiers, score policies or resource-limit overrides.
- **FR-009**: An MCP semantic request without an authorized capability MUST fail with the existing stable body-free
  invalid-parameter category and MUST NOT fall back to lexical retrieval.
- **FR-010**: One configured MCP session MUST retain a single provider lifecycle across requests for safe in-memory cache
  reuse and MUST close the provider worker when the session exits or startup/serving fails.
- **FR-011**: CLI and MCP result projections MUST remain handle-first, bounded and body-free unless the existing explicit
  bundle opt-in is used; task text, evidence bodies, local paths, host facts and raw provider failures MUST not leak.
- **FR-012**: The MCP interface contract version MUST evolve additively and its committed canonical tool-list fixture MUST
  describe the optional retrieval-profile choice and unchanged path-free authority boundary.
- **FR-013**: Model-free fake-provider tests MUST cover CLI/MCP selection, lifecycle, exact replay, drift, missing assets,
  invalid combinations, lexical non-regression, semantic abstention, cancellation and sanitized errors without network.
- **FR-014**: A frozen operational protocol MUST measure exact-bundle verification, cold first compilation, warm repeated
  compilation, provider cache reuse, peak worker RSS and wall time against a redistributable corpus.
- **FR-015**: The measurement producer MUST run twice from fresh workspace state, preserve both raw body-free runs and
  publish a deterministic summary whose identity excludes only explicitly descriptive timing/resource observations.
- **FR-016**: An independent standard-library-only validator MUST recompute protocol/result identities, aggregation,
  privacy constraints and decision gates without importing OpenARDP, optional provider libraries or producer code.
- **FR-017**: The reference decision MUST disclose the exact external bundle size, peak memory, cold/warm latency ratio,
  cache reuse, unsupported platforms and the fact that the workload does not validate answer generation or production SLOs.
- **FR-018**: No embedding, vector or model-native state may be added to public evidence schemas, SQLite, CAS or receipts;
  provider memory remains disposable and process-local.
- **FR-019**: The feature MUST add no network-enabled runtime, cloud dependency, mandatory semantic extra, answer
  generation, vector database, persisted embedding cache or new retrieval policy.
- **FR-020**: Documentation, changelog, module inventory, public CLI/MCP contracts and repository validators MUST be
  updated, and all three-platform quality/release gates MUST remain green.

## Edge Cases

- Only one of bundle or source-lock is supplied; semantic flags accompany lexical compilation; replay profile disagrees
  with the persisted algorithm; the bundle changes after verification; optional runtime packages are absent.
- MCP client requests semantic retrieval from a provider-free server, supplies an unknown profile, repeats a request,
  cancels during model startup or disconnects while the provider worker is active.
- Empty or oversized task text, too many documents, tiny context budget, no above-floor semantic evidence, corrupt CAS
  content, changed source snapshot, provider timeout/crash and malformed score response.
- Measurement interruption between runs, tampered raw observation, reordered rows, leaked query/path/body, unavailable
  peak-RSS measurement and a warm run slower than the cold run.

## Assumptions

- The first productized semantic provider remains the exact optional F029 E5 adapter and bundle recipe.
- CLI and MCP are single-owner local interfaces; semantic authorization is a trusted process-start decision.
- MCP adds semantic selection to `compile_context` rather than adding a second tool, preserving progressive disclosure.
- Operational evidence uses the F024/F025 corpus identities while evaluating product-surface cost, not retrieval quality.

## Success Criteria

- **SC-001**: Omitting the profile yields byte-equivalent lexical receipt and selection projections across all existing
  CLI and MCP context tests.
- **SC-002**: Every invalid configuration/profile/replay combination fails closed with no body, path, query, model trace
  or provider exception in stdout, stderr, MCP response or audit record.
- **SC-003**: A configured CLI request and two requests in one configured MCP session produce exact semantic receipts;
  an unconfigured MCP session rejects semantic selection and continues to serve lexical requests.
- **SC-004**: Matching semantic replay reproduces the original selected evidence and receipt facts; all drifted provider
  recipes and profile mismatches are rejected before a replay result is returned.
- **SC-005**: Two fresh reference runs produce identical non-timing projections, at least 90% passage-cache reuse on the
  warm workload, warm semantic wall time no greater than cold semantic wall time, and peak worker RSS no greater than
  1.5 GiB on the declared reference platform.
- **SC-006**: The result validator rejects any modified protocol, identity, raw observation, favorable or unfavorable
  metric, decision, privacy-forbidden key or extra file.
- **SC-007**: Default installation and unit tests perform zero network access and require neither the semantic extra nor
  the 493 MiB external model bundle.
- **SC-008**: Full repository lint, formatting, strict typing, tests with at least 85% branch coverage, build, validators,
  Linux, macOS and Windows checks all pass.

## Compatibility

This feature is additive. The lexical context profile, persisted identifiers, evidence/context schemas, catalog schema,
default dependencies and default CLI/MCP behavior remain unchanged. MCP advertises a new optional input property under a
new experimental interface minor version; clients that omit it retain the previous behavior.
