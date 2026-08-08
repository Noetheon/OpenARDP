# Data Model: Repository Hygiene Audit

F031 adds no persisted product entity or schema. The following maintainer-only immutable values define the audit.

## `FindingKind`

Closed string enumeration:

- `identical`: candidate and canonical tracked file have the same SHA-256 and byte length.
- `divergent`: both are regular files but their SHA-256 or length differs.
- `missing_canonical`: candidate pattern resolves to no tracked canonical counterpart.
- `unsafe`: candidate or canonical is a symlink, directory, unreadable object or escapes the admitted scope.
- `git_metadata_copy`: explicitly recognized inactive Git index or loose-ref conflict copy.

Only `identical` is evidence that a worktree candidate is redundant. All kinds remain findings; the audit itself never
authorizes or performs deletion.

## `HygieneFinding`

| Field | Type | Constraint |
|---|---|---|
| `kind` | `FindingKind` | closed value |
| `scope` | `worktree` or `git_metadata` | closed value |
| `candidate` | normalized POSIX relative path | never absolute; no `.` or `..` |
| `canonical` | normalized relative path or `None` | present only when safely derived |
| `candidate_size` | non-negative integer or `None` | metadata only |
| `canonical_size` | non-negative integer or `None` | metadata only |
| `candidate_sha256` | lowercase 64-hex or `None` | only for safely read regular files |
| `canonical_sha256` | lowercase 64-hex or `None` | only for safely read regular files |

No body, arbitrary exception text, absolute host path, username or document content is retained.

## `HygieneReport`

| Field | Type | Constraint |
|---|---|---|
| `version` | integer | exactly `1` |
| `checked_scopes` | ordered tuple | deterministic fixed order |
| `findings` | ordered tuple of `HygieneFinding` | sorted by scope, candidate and kind |
| `passed` | boolean | true iff `findings` is empty |

## State transitions

```text
filesystem candidate
  -> Git ownership check
  -> tracked: ignored as intentional
  -> untracked + pattern mismatch: ignored as unrelated
  -> untracked + pattern match
      -> unsafe/missing canonical: finding, preserve
      -> safe pair -> SHA-256 compare -> identical/divergent finding, preserve
```

The separate, manually reviewed cleanup operation may remove only candidates whose time-specific evidence is `identical`
or whose divergence has been independently proven to be an older superseded artifact. That operation is not a model
transition and is intentionally absent from the audit API.
