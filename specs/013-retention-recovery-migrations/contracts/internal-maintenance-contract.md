# Internal Maintenance Contract: F013

This is a provider-neutral runtime contract. It is not a public schema or export format.

## Catalog snapshot and intent

```python
class MaintenanceCatalog(Protocol):
    def retention_snapshot(self, *, observed_at: datetime) -> RetentionSnapshot: ...
    def add_hold(self, hold: RetentionHold) -> RetentionHold: ...
    def release_hold(self, object_id: str, *, now: datetime) -> RetentionHold: ...
    def claim_operation(self, intent: MaintenanceIntent) -> MaintenanceOperation: ...
    def operation(self, operation_id: UUID) -> MaintenanceOperation | None: ...
    def finalize_operation(self, result: MaintenanceResult) -> MaintenanceOperation: ...
```

- Snapshot is one read transaction and returns closed root reasons plus opaque row
  identities covering every F012 object reference.
- Claim transaction revalidates the supplied root/hold digest and persists every exact
  ordered entry before filesystem mutation.
- Ordinary writes fail with stable `maintenance_recovery_required` while one operation
  is active. Maintenance calls prove the exact operation ID.

## Filesystem maintenance

```python
class MaintenanceStore(Protocol):
    def inventory(self, limits: InventoryLimits) -> MaintenanceInventory: ...
    def transition(self, entry: MaintenanceEntry) -> TransitionResult: ...
    def remove(self, entry: MaintenanceEntry) -> RemovalResult: ...
    def capacity(self, required_bytes: int, reserve_bytes: int) -> CapacityReport: ...
```

- This port is not inherited from or exposed through `ObjectStore`.
- Operations accept exact canonical identities, never arbitrary paths.
- Implementations reject unsafe/link/hardlink/cross-device/ambiguous state and never
  overwrite a destination.

## Service

```python
class MaintenanceService:
    def inventory(self, *, policy: RetentionPolicy, now: datetime) -> InventoryReport: ...
    def plan(self, *, policy: RetentionPolicy, now: datetime) -> ReclamationPlan: ...
    def quarantine(self, plan: ReclamationPlan, *, now: datetime) -> QuarantineBatch: ...
    def restore(self, batch_id: UUID, *, now: datetime) -> QuarantineBatch: ...
    def commit(
        self, batch_id: UUID, *, acknowledgement: str, now: datetime
    ) -> QuarantineBatch: ...
    def recover(self, *, now: datetime) -> MaintenanceOperation | None: ...
```

Dry run is read-only and its complete plan value must be supplied to quarantine.
`commit` accepts only the exact closed acknowledgement phrase defined by the CLI
contract. `recover` may replay existing intent but cannot synthesize commit authority.

## Backup, restore and migration

```python
def backup_workspace(source: LocalWorkspace, destination: Path, limits: BackupLimits) -> BackupReport: ...
def restore_workspace(backup: Path, destination: Path, limits: BackupLimits) -> RestoreReport: ...
def migrate_workspace(source: Path, backup: Path, *, now: datetime) -> MigrationReport: ...
```

- Destinations must be absent, disjoint, local and have existing safe parents.
- Backup uses a second SQLite connection's online backup API while a coordinating
  writer reservation fixes roots and blocks ordinary writes.
- Restore verifies all manifest paths/hashes/history before publication and never
  migrates the restored workspace.
- Existing older workspaces migrate only through the explicit migration entrypoint and
  only after verified backup publication.

## Lexical index rebuild

```python
def replace_search_index(entries: Sequence[PreparedSearchEntry]) -> IndexRebuildReport: ...
```

The catalog verifies the complete authoritative corpus and replaces all mapping/FTS
rows in one transaction. No partial scope becomes visible.

## Stable failure categories

- `workspace_missing`, `workspace_incompatible`, `migration_required`;
- `maintenance_busy`, `maintenance_recovery_required`, `stale_plan`;
- `inventory_overflow`, `store_inconsistent`, `object_conflict`;
- `grace_active`, `acknowledgement_required`, `commit_blocked`;
- `path_unsafe`, `path_overlap`, `filesystem_unsupported`, `insufficient_space`;
- `backup_invalid`, `restore_invalid`, `migration_failed`, `index_rebuild_failed`.

No public/persisted error includes paths, filenames, bodies, queries, tokens, raw SQL
or chained provider exception text.
