# GitHub Spec Kit integration for OpenARDP

This directory turns the architecture blueprint into a controlled Codex implementation workflow.

## What Spec Kit does here

Spec Kit does not replace the OpenARDP architecture. It provides the execution lifecycle:

```text
project principles → feature requirements → clarification → plan → checklist → tasks → consistency analysis
→ implementation → convergence
```

Project-wide truth remains in `AGENTS.md`, `docs/`, ADRs, schemas and the OpenARDP constitution. Feature-specific artifacts
are generated under `specs/`.

## Pinned tool version

The bootstrap scripts pin `specify-cli` to the version in `PINNED_VERSION.txt`. Upgrade only through a reviewed maintenance
change because Spec Kit templates and integrations evolve quickly.

## Automated bootstrap

### macOS or Linux

```bash
bash scripts/bootstrap-speckit.sh
```

### Windows PowerShell

```powershell
Set-ExecutionPolicy -Scope Process Bypass
./scripts/bootstrap-speckit.ps1
```

The script:

1. verifies `uv`;
2. installs the pinned Specify CLI;
3. initializes Spec Kit in the non-empty repository for Codex;
4. restores the authoritative OpenARDP constitution after initialization;
5. verifies the Spec Kit and Codex integration state;
6. leaves all original blueprint files untouched.

## Manual bootstrap

```bash
uv tool install specify-cli==0.13.3 --force
specify init --here --force --integration codex
python scripts/apply-speckit-overlay.py
specify version
specify integration status
```

Commit the repository before initialization so every generated or changed file is reviewable.

## First Codex session

Open Codex from the repository root and paste the contents of `FIRST_CODEX_SESSION.md`. Codex should:

1. inspect the repository;
2. verify Spec Kit skills are available;
3. compare the generated constitution with `CONSTITUTION_SOURCE.md`;
4. create only feature `001-repository-baseline`;
5. stop after specification/clarification/plan/checklist/tasks/analyze unless explicitly instructed to implement.

## Do not do this

```text
$speckit-specify Build the whole OpenARDP platform
$speckit-implement
```

That creates an oversized, hard-to-review change and defeats the bounded work-package design.
