# Step-by-step guide: from ZIP to the first Codex implementation

This guide assumes the user has not yet sent the project to Codex.

## Stage 1 — Extract the correct package

Use the Spec-Kit-integrated package, not the older blueprint, for a new implementation. Extract it into a dedicated folder.
Do not combine it with another active code repository yet.

## Stage 2 — Create the initial Git history

From the project root:

```bash
git init
git add .
git commit -m "chore: add OpenARDP architecture and Spec Kit blueprint"
```

This first commit is the untouched, reviewable source baseline.

## Stage 3 — Verify prerequisites

Required:

- Git;
- Python 3.12 for the OpenARDP project;
- `uv`;
- Codex CLI or another Codex environment that can use repository skills.

Check:

```bash
git --version
uv --version
python3 --version
```

## Stage 4 — Bootstrap GitHub Spec Kit

### macOS/Linux

```bash
bash scripts/bootstrap-speckit.sh
```

### Windows PowerShell

```powershell
Set-ExecutionPolicy -Scope Process Bypass
./scripts/bootstrap-speckit.ps1
```

The bootstrap pins the Spec Kit version, initializes the Codex skills and restores the OpenARDP constitution.

## Stage 5 — Review and commit generated files

```bash
git status
git diff -- . ':!uv.lock'
git add .
git commit -m "chore: initialize Spec Kit for Codex"
```

Check `spec-kit/AFTER_BOOTSTRAP_CHECKLIST.md` before continuing.

## Stage 6 — Open Codex from the repository root

Codex must see:

- `AGENTS.md`;
- `.specify/memory/constitution.md`;
- `.agents/skills/`;
- `docs/`;
- `spec-kit/`;
- `schemas/` and existing tests.

Paste `spec-kit/FIRST_CODEX_SESSION.md`.

## Stage 7 — Prepare feature 001, but do not rush into coding

Codex should use `spec-kit/feature-prompts/001-repository-baseline.md` with `$speckit-specify`, then run:

```text
$speckit-clarify
$speckit-plan
$speckit-checklist
$speckit-tasks
$speckit-analyze
```

Review the readiness report. Correct critical contradictions in the source artifact before implementation.

## Stage 8 — Implement feature 001

Only after the specification artifacts are clean:

```text
$speckit-implement
```

For a large task list, tell Codex to implement only the next phase or a bounded task group. Require the checks in
`AGENTS.md` after each coherent slice.

Then run:

```text
$speckit-converge
```

Repeat implement/converge until the feature is complete.

## Stage 9 — Commit and review

```bash
git status
git diff
git add .
git commit -m "build: establish OpenARDP repository baseline"
```

Do not start feature 002 until feature 001 has converged and all checks pass.

## Stage 10 — Continue feature by feature

Use `spec-kit/FEATURE_MAP.md` and the matching prompt in `spec-kit/feature-prompts/`. Each feature follows the same full
quality loop.

## What not to send Codex

Do not send only the old master prompt and ask for the complete system in one pass. Do not ask it to invent missing
architecture. Do not let it combine several work packages merely because they share files.
