"""Contract tests for F005 search catalog methods and error taxonomy."""

from __future__ import annotations

import inspect

from openardp.ports import catalog as catalog_port
from openardp.ports.catalog import Catalog


def test_search_error_taxonomy_is_exported() -> None:
    """Expose sanitized search errors under the catalog failure hierarchy."""
    assert issubclass(catalog_port.SearchCapabilityUnavailable, catalog_port.CatalogError)
    assert issubclass(catalog_port.SearchIndexIncomplete, catalog_port.CatalogError)
    assert issubclass(catalog_port.SearchIndexDrifted, catalog_port.CatalogError)


def test_catalog_protocol_declares_search_methods() -> None:
    """Keep F005 search methods on the provider-neutral catalog port."""
    source = inspect.getsource(Catalog)
    for method in (
        "search_block_entries",
        "index_coverage",
        "replace_scope_index",
        "list_ready_scopes",
        "list_scope_index_entries",
    ):
        assert f"def {method}" in source
