"""Structural contracts for provider-neutral F010 persistence boundaries."""

from __future__ import annotations

import inspect

from openardp.ports.catalog import (
    CatalogError,
    DerivationConflict,
    DerivationCycleError,
    DerivationDependencyError,
    DerivationIntegrityError,
    ReconciliationConflict,
    ReconciliationDerivationCatalog,
    ReconciliationIntegrityError,
    ReconciliationScopeError,
)


def test_f010_catalog_port_is_narrow_additive_and_runtime_checkable() -> None:
    """Expose only atomic lineage/derivation commits and deterministic body-free reads."""
    assert ReconciliationDerivationCatalog._is_runtime_protocol
    assert set(
        inspect.signature(ReconciliationDerivationCatalog.commit_reconciliation).parameters
    ) == {"self", "plan", "object_is_verified"}
    assert set(
        inspect.signature(ReconciliationDerivationCatalog.publish_derivation).parameters
    ) == {"self", "publication"}
    assert set(inspect.signature(ReconciliationDerivationCatalog.get_lineage).parameters) == {
        "self",
        "block",
    }
    assert set(inspect.signature(ReconciliationDerivationCatalog.get_derivation).parameters) == {
        "self",
        "artifact_id",
    }


def test_f010_failures_are_distinct_sanitized_catalog_categories() -> None:
    """Keep body-free conflict, dependency, cycle and integrity classes stable."""
    error_types = (
        ReconciliationScopeError,
        ReconciliationConflict,
        ReconciliationIntegrityError,
        DerivationDependencyError,
        DerivationCycleError,
        DerivationConflict,
        DerivationIntegrityError,
    )
    assert all(issubclass(error_type, CatalogError) for error_type in error_types)
    assert len(set(error_types)) == len(error_types)
