# After-bootstrap checklist

Completed on 2026-07-22 before feature 001 implementation.

- [x] The new package was extracted into its own project folder.
- [x] A Git repository was initialized and the untouched blueprint committed.
- [x] `bash scripts/bootstrap-speckit.sh` or the PowerShell equivalent completed successfully.
- [x] `specify version` reports the pinned version from `spec-kit/PINNED_VERSION.txt`.
- [x] `specify integration status` has no error.
- [x] `.agents/skills/` contains the Codex Spec Kit skills.
- [x] `.specify/memory/constitution.md` matches `spec-kit/CONSTITUTION_SOURCE.md`.
- [x] `.specify/OPENARDP_OVERLAY_APPLIED` exists.
- [x] Generated Spec Kit files were reviewed with `git status` and committed separately.
- [x] Codex was opened from the repository root.
- [x] The first session uses `spec-kit/FIRST_CODEX_SESSION.md`.
- [x] The first feature is `001-repository-baseline`, not the entire platform.

Evidence: bootstrap integration commit `acf8aea`; feature artifacts are under `specs/001-repository-baseline/`.
