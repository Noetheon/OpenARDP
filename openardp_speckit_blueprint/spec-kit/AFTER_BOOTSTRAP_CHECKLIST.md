# After-bootstrap checklist

Complete this before asking Codex to implement anything.

- [ ] The new package was extracted into its own project folder.
- [ ] A Git repository was initialized and the untouched blueprint committed.
- [ ] `bash scripts/bootstrap-speckit.sh` or the PowerShell equivalent completed successfully.
- [ ] `specify version` reports the pinned version from `spec-kit/PINNED_VERSION.txt`.
- [ ] `specify integration status` has no error.
- [ ] `.agents/skills/` contains the Codex Spec Kit skills.
- [ ] `.specify/memory/constitution.md` matches `spec-kit/CONSTITUTION_SOURCE.md`.
- [ ] `.specify/OPENARDP_OVERLAY_APPLIED` exists.
- [ ] Generated Spec Kit files were reviewed with `git status` and committed separately.
- [ ] Codex was opened from the repository root.
- [ ] The first session uses `spec-kit/FIRST_CODEX_SESSION.md`.
- [ ] The first feature is `001-repository-baseline`, not the entire platform.
