# First Codex session prompt

> **Historical onboarding artifact.** This prompt records the completed Feature 001 bootstrap and must not be used to
> select current work. Use [`FEATURE_MAP.md`](FEATURE_MAP.md) and the active feature prompt instead.

Paste the text below into Codex from the repository root after running the bootstrap script.

```text
You are onboarding the OpenARDP repository into GitHub Spec Kit.

Before doing any implementation:
1. Read AGENTS.md.
2. Read .specify/memory/constitution.md.
3. Read README.md, docs/00_EXECUTIVE_BRIEF.md, docs/01_PRODUCT_REQUIREMENTS.md,
   docs/02_ARCHITECTURE.md, docs/06_SECURITY_THREAT_MODEL.md,
   docs/07_TEST_AND_BENCHMARK_STRATEGY.md, docs/09_CODEX_EXECUTION_PLAN.md,
   spec-kit/FEATURE_MAP.md and all accepted ADRs.
4. Inspect the repository, current tests and generated Spec Kit integration files.
5. Report contradictions, missing prerequisites or accidental duplicate sources of truth.

Use the installed Codex Spec Kit skills. Work only on feature `001-repository-baseline` using the prompt in
`spec-kit/feature-prompts/001-repository-baseline.md`.

Run the full lifecycle through specification, clarification, planning, checklist generation, task generation and analysis.
Do not start implementation until the resulting spec, plan and tasks have no unresolved critical contradictions and you
have shown me a concise readiness report.

Binding constraints:
- Do not edit or weaken the constitution, AGENTS.md, security boundaries, public schemas or accepted ADRs merely to make
  implementation easier.
- Do not include any later OpenARDP product feature in this first slice.
- Tests, linting, strict typing and least-privilege CI are mandatory.
- Existing blueprint documents are project context, not disposable drafts.
```
