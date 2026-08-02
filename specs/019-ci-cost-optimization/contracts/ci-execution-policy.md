# Contract: CI Execution Policy 1.0.0

## Classification interface

```text
python scripts/audit_ci.py classify --paths-file PATH [--github-output PATH]
```

- `PATH` is a newline-delimited Git path list produced by a bounded `git diff --name-only` command.
- Standard output is one canonical JSON object with `scope`, sorted unique `paths` and deterministic `reasons`.
- When `--github-output` is supplied, the script atomically appends `scope=<value>` to the designated GitHub output
  file after successful classification.
- Empty, unreadable, absolute, parent-traversing, control-bearing or unknown paths return `scope=full`; malformed policy
  or I/O errors exit non-zero.
- File contents are never opened or emitted.

## Audit interface

```text
python scripts/audit_ci.py audit
python scripts/audit_ci.py estimate
```

- `audit` loads `quality/ci-policy.json`, `.github/workflows/ci.yml` and
  `.github/workflows/release-evidence.yml`, checks every declared invariant and emits canonical JSON.
- Violations exit non-zero with sorted body-free diagnostics naming only invariant and repository path.
- `estimate` validates `quality/ci-cost-baseline-2026-08-01.json`, recomputes gross cost and projected range from
  explicit inputs, and emits canonical JSON. Stored arithmetic drift exits non-zero.
- Repeated commands over unchanged files produce byte-identical standard output.

## Core event contract

| Event/state | Classification | Preflight | Linux full + coverage | macOS full/no-cov | Windows full/no-cov |
|---|---|---:|---:|---:|---:|
| Pull request, draft | any | Yes | Skip | Skip | Skip |
| Pull request, ready | governance | Yes | Skip | Skip | Skip |
| Pull request, ready | full | Yes | Yes | Yes | Yes |
| Push to `main` | any | Yes | Skip | Skip | Skip |

The core workflow MUST NOT use PR-level `paths`/`paths-ignore` or `pull_request_target`. Job-level skip semantics ensure
required contexts conclude successfully rather than remaining pending.

## Release event contract

| Event/state | Release-owned path required? | Three-platform evidence | Aggregate gate |
|---|---:|---:|---:|
| Manual dispatch | No | Yes | Yes |
| `v*` tag push | No | Yes | Yes |
| Pull request, draft | Yes | Skip | Skip |
| Pull request, ready | Yes | Yes | Yes |
| Ordinary main push | N/A | No workflow | No workflow |

## Security and reproducibility invariants

- Workflow and job permissions are read-only; checkout credentials are not persisted.
- Every third-party action reference is a reviewed 40-character commit SHA.
- All jobs have explicit timeouts and same-workflow/ref concurrency cancels superseded work.
- All installs are locked; cache restoration cannot replace synchronization.
- Unit/integration tests retain global socket denial.
- Release evidence content, aggregate `NO-GO` assertion and retention remain unchanged.
- Workflow edits, policy edits and classifier edits always classify full.

## Branch protection contract

After F019 merges, `main` requires an up-to-date pull request and the stable contexts `Preflight`,
`Quality (ubuntu-latest)`, `Quality (macos-latest)` and `Quality (windows-latest)`. Administrator enforcement and
conversation resolution are enabled; required approval count is zero; force pushes and deletion are disabled.
