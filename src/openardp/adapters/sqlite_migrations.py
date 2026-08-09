"""Public ordered SQLite migration registry for the local catalog."""

from openardp.adapters.sqlite_migration import Migration
from openardp.adapters.sqlite_migrations_evidence import MIGRATION_6, MIGRATION_7, MIGRATION_8
from openardp.adapters.sqlite_migrations_foundation import (
    MIGRATION_1,
    MIGRATION_2,
    MIGRATION_3,
    MIGRATION_4,
    MIGRATION_5,
)
from openardp.adapters.sqlite_migrations_operations import (
    MIGRATION_9,
    MIGRATION_10,
    MIGRATION_11,
)

MIGRATIONS = (
    MIGRATION_1,
    MIGRATION_2,
    MIGRATION_3,
    MIGRATION_4,
    MIGRATION_5,
    MIGRATION_6,
    MIGRATION_7,
    MIGRATION_8,
    MIGRATION_9,
    MIGRATION_10,
    MIGRATION_11,
)
CURRENT_SCHEMA_VERSION = MIGRATIONS[-1].version

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "MIGRATIONS",
    "MIGRATION_1",
    "MIGRATION_2",
    "MIGRATION_3",
    "MIGRATION_4",
    "MIGRATION_5",
    "MIGRATION_6",
    "MIGRATION_7",
    "MIGRATION_8",
    "MIGRATION_9",
    "MIGRATION_10",
    "MIGRATION_11",
    "Migration",
]
