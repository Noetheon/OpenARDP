# Start here

Use this package instead of the previous ZIP for a new Codex implementation.

## 1. Create the baseline commit

```bash
git init
git add .
git commit -m "chore: add OpenARDP architecture and Spec Kit blueprint"
```

## 2. Initialize GitHub Spec Kit

macOS/Linux:

```bash
bash scripts/bootstrap-speckit.sh
```

Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
./scripts/bootstrap-speckit.ps1
```

## 3. Commit the generated integration

```bash
git status
git add .
git commit -m "chore: initialize Spec Kit for Codex"
```

## 4. Check readiness

Complete [`spec-kit/AFTER_BOOTSTRAP_CHECKLIST.md`](spec-kit/AFTER_BOOTSTRAP_CHECKLIST.md).

## 5. Start Codex

Open Codex from this repository root and paste [`spec-kit/FIRST_CODEX_SESSION.md`](spec-kit/FIRST_CODEX_SESSION.md).

The first feature is `001-repository-baseline`. Do not request the complete platform in one pass.

For all details, read [`docs/13_STEP_BY_STEP_USER_GUIDE.md`](docs/13_STEP_BY_STEP_USER_GUIDE.md).
