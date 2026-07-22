# Revision notes — Spec Kit integrated blueprint

This package supersedes the previous OpenARDP blueprint for new Codex implementation work.

## Added

- GitHub Spec Kit 0.13.3 pin and bootstrap scripts;
- OpenARDP project constitution;
- bounded feature map for all work packages;
- fourteen ready-to-use feature specification prompts;
- Codex first-session prompt;
- Spec Kit operating procedure and setup checklist;
- step-by-step macOS/Linux and Windows guidance;
- migration guidance for the previous ZIP;
- explicit project/feature source-of-truth hierarchy;
- analyze and convergence completion gates.

## Changed

- `README.md` now starts with Git, Spec Kit and Codex onboarding;
- `AGENTS.md` requires the full Spec Kit lifecycle;
- the Codex master prompt delegates workflow control to installed Spec Kit skills;
- the work-package execution plan maps directly to bounded Spec Kit features;
- validation documents the attempted but network-blocked end-to-end bootstrap.

## Unchanged core decisions

- originals remain authoritative;
- derived data is disposable and reproducible;
- embeddings are optional model-specific retrieval caches;
- the MVP is local-first, provider-neutral and read-only through MCP;
- Docling is used through an adapter rather than reimplementing document parsing;
- context is progressively disclosed and original evidence remains available;
- Microsoft Graph remains a later design spike, not an MVP dependency.
