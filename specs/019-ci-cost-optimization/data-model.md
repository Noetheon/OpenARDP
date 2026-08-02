# Data Model: CI Cost and Latency Optimization

F019 adds no product-domain or persisted runtime entity. These developer-operation records are JSON-compatible and
version controlled.

## CI Policy

- `schema_version`: semantic version of the policy document.
- `supported_platforms`: exact runner labels for Linux, macOS and Windows.
- `coverage_owner`: the one runner responsible for branch coverage.
- `required_checks`: stable branch-protection context names.
- `governance_only`: exact files and directory prefixes eligible for reduced execution.
- `release_owned`: exact files, prefixes and glob-like workflow path entries that authorize release reproduction.
- `workflow_invariants`: exact security, dependency, cache, trigger and command constraints audited in repository state.

**Invariants**:

- Supported platforms are exactly three and coverage owner belongs to that set.
- Required checks map one-to-one to Preflight plus all supported platform lanes.
- Governance paths are relative, normalized, non-overlapping and do not include executable, workflow, dependency,
  source, test, schema, benchmark/release or quality-policy roots.
- Any missing/invalid policy field fails validation rather than falling back.

## Change Classification

- `scope`: `governance` or `full`.
- `paths`: normalized sorted unique repository-relative paths.
- `reasons`: deterministic body-free reason codes.

**Transitions**:

```text
unread input -> invalid/empty -> full
            -> every path allowlisted -> governance
            -> any path unknown/unsafe -> full
```

`full` is absorbing for a change set: later allowlisted paths cannot downgrade it.

## Quality Lane

- `check_name`: stable branch-protection display name.
- `platform`: GitHub runner label.
- `condition`: event, draft state and classification predicate.
- `test_inventory`: `complete` for all three final platform lanes.
- `coverage`: authoritative or disabled.
- `platform_independent_gates`: owned only by authoritative Linux lane.

## Release Boundary

- `event`: manual dispatch, version tag or pull request.
- `draft_allowed`: false for pull requests, true/not-applicable otherwise.
- `path_scope`: release-owned paths for pull requests, unrestricted for manual/tag.
- `evidence_platforms`: Linux, macOS and Windows.
- `aggregate_required`: true after all platform jobs succeed.

## Cost Evidence Snapshot

- `observed_date`: UTC date for the captured inventory.
- `captured_at`: RFC 3339 time when aggregates were computed.
- `source`: repository and GitHub Actions API query boundary without run identifiers.
- `runner_prices`: dated USD/minute snapshot per runner family.
- `rounded_minutes`: aggregate billable minutes per runner family.
- `job_count`, `run_count`: observed topology counts.
- `gross_cost`: deterministic sum of rounded minutes multiplied by dated prices.
- `model`: explicit before/after assumptions, projected range and limitations.

The snapshot is immutable historical evidence. A later price or usage sample requires a new dated file, never mutation
that hides the original comparison.
