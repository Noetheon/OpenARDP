"""Actual offline Docling 2.114 smoke conversions over deterministic fixtures."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from openardp.adapters.isolated_docling import IsolatedDoclingAdapter
from openardp.domain.rich_ingestion import RichMediaType, RichParserLimits
from openardp.ports.parser import (
    RichParserModelAssetsRequired,
    RichParserResourceLimitExceeded,
)

FIXTURES = Path(__file__).parents[1] / "fixtures" / "rich"


def test_fixture_generation_is_byte_reproducible(tmp_path: Path) -> None:
    """Regenerate redistributable inputs and match every reviewed byte digest."""
    subprocess.run(  # noqa: S603 -- current interpreter executes a repository fixture tool
        [
            sys.executable,
            str(FIXTURES / "generate_fixtures.py"),
            "--output",
            str(tmp_path),
        ],
        check=True,
    )
    manifest = json.loads((FIXTURES / "fixture-manifest.json").read_text(encoding="utf-8"))
    for record in manifest["records"]:
        expected = (FIXTURES / record["name"]).read_bytes()
        regenerated = (tmp_path / record["name"]).read_bytes()
        assert regenerated == expected
        assert hashlib.sha256(regenerated).hexdigest() == record["sha256"]


@pytest.mark.parametrize(
    ("name", "media_type", "text_count", "page_count"),
    (
        ("synthetic.docx", RichMediaType.DOCX, 2, 0),
        ("synthetic.pptx", RichMediaType.PPTX, 3, 2),
    ),
)
def test_actual_docling_conversion_is_complete_offline_and_provider_neutral(
    name: str,
    media_type: RichMediaType,
    text_count: int,
    page_count: int,
    without_subprocess_coverage: None,
) -> None:
    """Convert in-memory OOXML without URLs, local source paths or remote services."""
    adapter = IsolatedDoclingAdapter(limits=RichParserLimits(timeout_seconds=30.0))
    output = adapter.parse(
        ((FIXTURES / name).read_bytes(),),
        media_type=media_type.value,
    )

    assert output.media_type is media_type
    assert output.native_document["schema_name"] == "DoclingDocument"
    assert len(output.native_document["texts"]) == text_count
    assert len(output.native_document["pages"]) == page_count
    assert output.candidates
    assert output.component_versions[0].name == "docling"
    assert output.component_versions[0].version == "2.114.0"
    assert str(FIXTURES) not in output.canonical_native_bytes.decode("utf-8")


def test_pdf_requires_reviewed_local_model_assets_before_provider_conversion() -> None:
    """Never let a default PDF conversion trigger first-use model downloads."""
    with pytest.raises(RichParserModelAssetsRequired, match="model assets required"):
        IsolatedDoclingAdapter().parse(
            ((FIXTURES / "synthetic.pdf").read_bytes(),),
            media_type=RichMediaType.PDF.value,
        )


def test_pptx_page_limit_fails_instead_of_silently_truncating(
    without_subprocess_coverage: None,
) -> None:
    """Reject a two-slide source when the reviewed execution permits only one page."""
    adapter = IsolatedDoclingAdapter(limits=RichParserLimits(max_pages=1, timeout_seconds=30.0))
    with pytest.raises(RichParserResourceLimitExceeded, match="resource limit"):
        adapter.parse(
            ((FIXTURES / "synthetic.pptx").read_bytes(),),
            media_type=RichMediaType.PPTX.value,
        )
