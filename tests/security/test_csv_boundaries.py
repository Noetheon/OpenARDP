"""Security boundaries for stable local CSV ingestion."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from openardp.adapters.local_workspace import LocalWorkspace
from openardp.domain.ingestion import TextMediaType
from openardp.interfaces.ingestion_composition import local_text_ingestion
from openardp.ports.parser import MalformedCsv

NOW = datetime(2026, 8, 3, 3, 0, tzinfo=UTC)


def test_malformed_csv_fails_without_source_mutation_or_ready_evidence(tmp_path: Path) -> None:
    """Fail closed after snapshotting while preserving the authoritative source."""
    workspace = LocalWorkspace.initialize(tmp_path / "workspace", now=NOW)
    source = tmp_path / "malformed.csv"
    source.write_bytes(b'header\n"secret-unclosed')
    before = source.stat()
    ingestion = local_text_ingestion(workspace, TextMediaType.CSV)

    with pytest.raises(MalformedCsv, match="malformed csv") as error:
        ingestion.ingest(source)

    after = source.stat()
    assert "secret-unclosed" not in str(error.value)
    assert source.read_bytes() == b'header\n"secret-unclosed'
    assert (after.st_size, after.st_mtime_ns, after.st_mode) == (
        before.st_size,
        before.st_mtime_ns,
        before.st_mode,
    )
    assert workspace.catalog.list_ready_scopes() == ()


def test_formula_like_csv_data_cannot_create_a_requested_side_effect(tmp_path: Path) -> None:
    """Keep spreadsheet-looking instructions inert inside the isolated data path."""
    workspace = LocalWorkspace.initialize(tmp_path / "workspace", now=NOW)
    target = tmp_path / "must-not-exist"
    source = tmp_path / "formula.csv"
    source.write_text(
        f'kind,value\nformula,"=HYPERLINK(""file://{target}"",""open"")"\n',
        encoding="utf-8",
    )

    result = local_text_ingestion(workspace, TextMediaType.CSV).ingest(source)

    assert result.block_count == 2
    assert not target.exists()
