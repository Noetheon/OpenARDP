# Storage amplification and revision 11

**Status:** Implemented and measured in Feature 022.

F020 measured approximately 37.9 times logical workspace amplification for the frozen 10,000- and 100,000-block text
workloads. F022 reduces that cost without deleting history, weakening body verification or changing content identities.

## Operator workflow

A revision-10 workspace is never changed by ordinary open. Create the verified migration backup and advance explicitly,
then optimize eligible derived blocks:

```bash
uv run openardp workspace-migrate --store WORKSPACE --backup-destination REVISION10_BACKUP
uv run openardp storage-optimize --store WORKSPACE --json
```

Retrying `storage-optimize` is safe. It verifies every present form, converges a valid crash duplicate and retains the
ordinary form when compaction is not smaller. Any corrupt peer, active maintenance operation or unsupported catalog fails
closed. The optimizer records a restart-persistent exclusive maintenance operation before changing physical forms;
ordinary catalog writes remain fenced until success, and retrying `storage-optimize` explicitly resumes an interrupted
run. If CAS-first source publication collides with an eligible compact block during that window, the blocked ingest retry
retains the verified ordinary source and removes only its exact compact peer after the catalog commit. Rollback means
restoring the verified revision-10 backup to a fresh disjoint destination.

## Evidence

The versioned offline benchmark runs fresh reference, real revision-10 migration/reference and fresh scale scenarios.
It reports regular-file logical bytes, filesystem-allocated bytes, counts and a closed category inventory. The committed
macOS arm64 result is `PASS`:

| Scenario | Logical amplification | Allocated amplification | Logical reduction vs F020 |
|---|---:|---:|---:|
| Fresh reference | 13.3471x | 51.6411x | 64.77% |
| Migrated reference | 13.3454x | 51.6411x | 64.77% |
| Fresh scale | 13.2002x | 51.4846x | 65.21% |

Allocation uses `st_blocks * 512` on the binding APFS environment and remains filesystem-dependent. The still-high
physical factor reflects one independently addressable file per block; the result does not claim universal disk usage.
Reproduce and independently validate with the commands in
[`benchmarks/storage/v0.1.0/README.md`](../benchmarks/storage/v0.1.0/README.md).
