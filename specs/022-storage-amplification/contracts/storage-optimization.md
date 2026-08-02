# Internal Contract: Storage Optimization

## Compact object capability

An optional object-store capability accepts one bounded canonical derived-block payload and returns ordinary
`StoredObject` metadata. The provider either publishes and verifies a smaller versioned compact form or delegates to the
ordinary exact-byte publication. Callers cannot request compaction for arbitrary source/native streams through the product
interface.

All ordinary object-store reads, chunk iteration, verification and inventory remain logical-byte operations. A consumer
does not receive encoding names or physical paths.

After a source or provider-native object becomes catalog-authoritative, an optional ordinary-authority capability verifies
its ordinary bytes and removes only an exact compact peer. This post-commit ordering makes the catalog fence close the
concurrent identity-collision race: an optimizer cannot still own the object once the non-block reference commits.

## Existing-object optimization

`optimize(object_id, expected_length)` is available only to the explicit storage-optimization service. It:

1. validates identity and eligibility supplied by the catalog;
2. verifies every present physical form;
3. returns `already_compact` for compact-only;
4. returns `ordinary_smaller` without mutation when the complete compact form is not smaller;
5. publishes and synchronizes compact before removing ordinary;
6. on retry with two valid forms, removes ordinary and returns `duplicate_converged`;
7. never removes or repairs corrupt/unsafe data.

Fault points after compact publication and before/after ordinary removal are required. Public errors are sanitized.

## Catalog revision 11

Migration creates normalized scopes, rebuilds block projections with stable existing search row IDs where present, moves
search metadata onto block rows, validates row/count/coverage equivalence, then removes the legacy mapping/table/indexes in
one exclusive checksummed transaction. Missing disposable coverage remains explicitly uncovered and rebuildable.

The catalog exposes a deterministic eligible-block inventory that excludes every object used as a source/native or other
non-block authoritative reference. A restart-persistent exclusive operation fences ordinary catalog writes throughout
physical optimization; retry resumes that exact intent. The catalog never returns document bodies or physical locations.

## CLI

```text
openardp storage-optimize --store WORKSPACE [--json]
```

- Requires a current revision-11 workspace and no active maintenance operation.
- Does not accept source paths, encoding profiles or deletion flags.
- Human output is one body-free summary line; JSON uses the repository envelope and deterministic item ordering.
- Exit 0 means every eligible object is converged or safely retained ordinary; a nonzero bounded persistence/integrity
  classification means no failed item was silently ignored.

Workspace migration remains the existing explicit backup-first command/API. Revision-10 rollback uses the published backup,
not an in-place downgrade.

## Search and rebuild

Search joins FTS row IDs directly to compact block projections. It checks complete nullable metadata and exact ordinal
coverage inside the same read transaction. Returned text, trust and provenance are loaded from and cross-checked against
the logical block object. `reindex` clears/replaces only FTS rows and nullable search fields.

## Maintenance and backup

Inventory scans the ordinary and compact active/quarantine namespaces under the same entry/byte bounds. One valid logical
identity is counted once. Valid duplicate forms are reported as recoverable optimization residue and block maintenance
planning until optimized; any corrupt duplicate is inconsistent.

Transition and removal require exactly one verified physical form and preserve that form across active/quarantine.
Backups copy exact physical files, bind their relative paths and physical hashes, and retain one sorted logical ID inventory.
Restore verifies the complete closed file inventory plus decoded logical roots before publishing.

## Benchmark contract

`benchmarks/storage/v0.1.0/protocol.json` pins F020 input/result hashes, three scenarios, resource limits, byte semantics and
thresholds. Producer output is exactly `decision.json`, `observations.json`, `report.md`, `run-manifest.json` and
`summary.json`. The validator rejects extra/missing files, paths, bodies, noncanonical JSON, input drift, arithmetic drift,
category mismatch, unsupported allocation claims or report mismatch.
