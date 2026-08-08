# Maintainer Contract: Repository Hygiene Audit

## Invocation

```bash
uv run python scripts/audit_repository_hygiene.py --root .
```

`--root` defaults to the current directory, must identify a Git worktree, and is resolved before inspection. The command
does not accept a deletion or repair flag.

## Success

For a clean repository:

```text
repository hygiene audit passed
```

Exit status is `0`.

## Findings

Each finding is one deterministic line:

```text
<kind>: <scope>:<candidate> [canonical=<canonical>] [candidate_size=<n>] [canonical_size=<n>] [candidate_sha256=<hex>] [canonical_sha256=<hex>]
```

Findings are sorted lexicographically by scope, candidate and kind. Optional facts are emitted in the order shown. Exit
status is `1` when one or more findings exist.

## Invalid invocation or unavailable repository

```text
repository hygiene audit failed: <stable classification>
```

Exit status is `2`. Diagnostics never include file bodies, arbitrary Git stderr or unresolved absolute paths.

## Safety invariants

- Read-only: no unlink, rename, write, checkout, reset, clean or index mutation.
- Candidate selection begins with Git's tracked/untracked inventory.
- Tracked numbered names and unrelated untracked files are ignored.
- Symlinks and non-regular files are not followed or hashed.
- Hashing uses SHA-256 and bounded chunks.
- The resolved Git directory must belong to the admitted worktree; linked-worktree metadata is handled explicitly.
- Unit tests require no network and use isolated synthetic repositories.

## Repository validator composition

`scripts/validate_repository.py` invokes the audit in-process before declaring repository validation successful. A hygiene
finding produces a stable validation failure. CI checkouts remain clean and therefore incur no content hashing.
