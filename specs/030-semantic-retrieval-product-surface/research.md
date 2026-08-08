# Research: Semantic Retrieval Product Surface

## Decision 1 — Extend `context` and `compile_context`

**Decision**: Add an optional retrieval profile to the existing CLI command and MCP tool.

**Rationale**: Context policy, budgets, receipts, citations and untrusted-data envelopes already belong to these surfaces.
A second command/tool would duplicate contracts and invite behavioral drift.

**Alternatives considered**: A new `semantic-search` command was rejected because F029 produces context candidates rather
than a separate authoritative search result. A new MCP tool was rejected because it expands the attack and maintenance
surface without a distinct use case.

## Decision 2 — Authorize models only at local process start

**Decision**: CLI invocations and MCP server startup accept an exact bundle/source-lock pair. MCP tool calls accept only
the enum profile.

**Rationale**: The operator owns local filesystem authority; an MCP client does not. This preserves F009's prohibition on
arbitrary filesystem reach and prevents document/client input from selecting code, paths or model policy.

**Alternatives considered**: Environment/ambient cache discovery was rejected as non-reproducible. Client-supplied paths
were rejected as an authority escalation. A global configuration file was deferred until a second provider justifies it.

## Decision 3 — Resolve compiler profiles behind one narrow factory

**Decision**: Introduce an interface-local retrieval-profile enum and a compiler resolver that chooses the existing
lexical or exact F029 semantic composition. It receives an already constructed provider capability.

**Rationale**: CLI replay and MCP calls need the same fail-closed selection rules. The resolver adds no new provider port
or persisted model and keeps process lifecycle outside the compiler service.

**Alternatives considered**: Teaching `ContextCompilerService` to construct providers would invert dependencies. Adding
provider configuration to domain models or receipts would duplicate the recipe already bound in algorithm identity.

## Decision 4 — Keep one MCP provider alive, one CLI provider per invocation

**Decision**: MCP owns one optional provider across the server session and closes it in `finally`; CLI owns and closes one
provider around a single compile/replay command.

**Rationale**: MCP can realize the existing safe in-memory cache across requests. A normal CLI process has an explicit,
short lifecycle and must not create a background daemon.

**Alternatives considered**: Persistent vector files violate scope and introduce invalidation/storage policy. A hidden
CLI daemon adds lifecycle/security complexity. Rebuilding the MCP provider per request discards the measured benefit.

## Decision 5 — Measure operations separately from retrieval quality

**Decision**: Reuse frozen F024/F025 identities and exact F029 provider policy, but publish a new F030 protocol focused on
verification, cold/warm wall time, cache reuse and peak worker RSS. Preserve raw runs and validate with the stdlib only.

**Rationale**: F029 already owns relevance claims. Mixing new operational thresholds into its quality benchmark would
rewrite historical evidence.

**Alternatives considered**: Reusing F029 result fields was rejected because it cannot distinguish product-surface cost.
Synthetic-only timing was rejected because it cannot measure the 493 MiB runtime boundary.
