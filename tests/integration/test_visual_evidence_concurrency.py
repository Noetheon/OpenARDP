"""Independent-connection convergence for identical F011 materializations."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.visual_policy import LocalOnlyVisualPolicy
from openardp.services.visual_evidence import VisualEvidenceService
from tests.integration.test_rich_catalog import NOW
from tests.integration.visual_service_support import (
    CountingVisualRenderer,
    prepared_visual_service,
)


def test_twenty_independent_catalog_clients_converge_on_one_complete_record(
    tmp_path: Path,
) -> None:
    """Exercise concurrent CAS-first publication through independent SQLite clients."""
    catalog, _, rich = prepared_visual_service(tmp_path)
    projection_id = rich.bundle.projections[0].evidence_projection_id

    def materialize(_: int) -> str:
        independent = SQLiteCatalog(catalog.path)
        store = FilesystemObjectStore(tmp_path / "cas")
        service = VisualEvidenceService(
            store,
            independent,
            CountingVisualRenderer(),
            LocalOnlyVisualPolicy(),
        )
        return service.materialize(
            rich.bundle.scope,
            projection_id,
            created_at=NOW + timedelta(seconds=2),
        ).visual_evidence_id

    with ThreadPoolExecutor(max_workers=10) as executor:
        identities = tuple(executor.map(materialize, range(20)))
    assert len(set(identities)) == 1
    assert len(catalog.list_visual_evidence(rich.bundle.scope)) == 1
