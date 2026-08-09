"""Transactional local SQLite catalog assembled from bounded responsibility mixins."""

from pathlib import Path

from openardp.adapters.sqlite_catalog_core import _SQLiteCatalogCoreMixin
from openardp.adapters.sqlite_catalog_derivations import _SQLiteCatalogDerivationMixin
from openardp.adapters.sqlite_catalog_jobs import _SQLiteCatalogJobMixin
from openardp.adapters.sqlite_catalog_maintenance import _SQLiteCatalogMaintenanceMixin
from openardp.adapters.sqlite_catalog_reconciliation import _SQLiteCatalogReconciliationMixin
from openardp.adapters.sqlite_catalog_representations import _SQLiteCatalogRepresentationMixin
from openardp.adapters.sqlite_catalog_rich import _SQLiteCatalogRichMixin
from openardp.adapters.sqlite_catalog_search import _SQLiteCatalogSearchMixin
from openardp.adapters.sqlite_catalog_visual_context import _SQLiteCatalogVisualContextMixin
from openardp.adapters.sqlite_catalog_watch import _SQLiteCatalogWatchMixin
from openardp.adapters.sqlite_catalog_watch_records import _SQLiteCatalogWatchRecordMixin
from openardp.adapters.sqlite_migrations import MIGRATIONS, Migration


class SQLiteCatalog(
    _SQLiteCatalogCoreMixin,
    _SQLiteCatalogRepresentationMixin,
    _SQLiteCatalogRichMixin,
    _SQLiteCatalogVisualContextMixin,
    _SQLiteCatalogWatchMixin,
    _SQLiteCatalogWatchRecordMixin,
    _SQLiteCatalogJobMixin,
    _SQLiteCatalogReconciliationMixin,
    _SQLiteCatalogDerivationMixin,
    _SQLiteCatalogMaintenanceMixin,
    _SQLiteCatalogSearchMixin,
):
    """SQLite implementation with explicit transactions and checked migrations."""

    def __init__(
        self,
        path: Path,
        *,
        migrations: tuple[Migration, ...] = MIGRATIONS,
        busy_timeout_ms: int = 5000,
    ) -> None:
        """Configure one local catalog file without opening or mutating it."""
        if not migrations:
            raise ValueError("at least one catalog migration is required")
        expected = tuple(range(1, len(migrations) + 1))
        if tuple(migration.version for migration in migrations) != expected:
            raise ValueError("catalog migrations must be contiguous from revision 1")
        if type(busy_timeout_ms) is not int or busy_timeout_ms < 0:
            raise ValueError("busy_timeout_ms must be a non-negative integer")
        self._path = path.expanduser().absolute()
        self._migrations = migrations
        self._migration_by_version = {migration.version: migration for migration in migrations}
        self._busy_timeout_ms = busy_timeout_ms


__all__ = ["SQLiteCatalog"]
