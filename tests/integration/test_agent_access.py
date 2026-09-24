"""Agent access over a real local workspace: refresh, find, read, outline and verify."""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

import pytest

from openardp.adapters.local_workspace import LocalWorkspace
from openardp.domain.agent_query import MatchLevel
from openardp.domain.agent_results import Freshness, VerifyStatus
from openardp.interfaces.agent_composition import local_agent_access
from openardp.interfaces.cli import main
from openardp.ports.agent import AgentDocumentAmbiguous, AgentDocumentNotFound, AgentRangeInvalid
from openardp.services.agent_access import AgentAccessService

GUIDE = """# Field guide

## Calibration

Calibrate the sensor every morning before the first measurement.
The reference weight is 500 grams.

## Storage

Store the sensor in a dry cabinet between 10 and 25 degrees.
"""
LOG = "id,device,status\n1,sensor-a,calibrated\n2,sensor-b,needs service\n"


class _Store:
    def __init__(self, root: Path, capsys: pytest.CaptureFixture[str]) -> None:
        self.documents = root / "documents"
        (self.documents / "team").mkdir(parents=True)
        (self.documents / "archive").mkdir()
        (self.documents / "guide.md").write_text(GUIDE, encoding="utf-8")
        (self.documents / "log.csv").write_text(LOG, encoding="utf-8")
        (self.documents / "team" / "notes.txt").write_text(
            "Team notes\n\nPublish the calibration log weekly.\n", encoding="utf-8"
        )
        (self.documents / "archive" / "notes.txt").write_text(
            "Archived notes\n\nOld storage rules.\n", encoding="utf-8"
        )
        self.path = root / "store"
        self.capsys = capsys
        self.add()

    def add(self, *paths: Path) -> None:
        targets = [str(path) for path in paths] or [str(self.documents)]
        assert main(["add", *targets, "--store", str(self.path)]) == 0
        self.capsys.readouterr()

    def access(self) -> AgentAccessService:
        return local_agent_access(LocalWorkspace.open(self.path))


@pytest.fixture
def store(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> _Store:
    """Prepare Markdown, CSV and two same-named text files."""
    return _Store(tmp_path, capsys)


def test_refresh_is_incremental_and_documents_report_size_and_freshness(store: _Store) -> None:
    """Index every READY head once and report stable sizes, ids and freshness."""
    access = store.access()
    assert access.refresh().rebuilt == ()
    listing = access.documents()
    assert [entry.label for entry in listing.documents] == [
        "guide.md",
        "log.csv",
        "notes.txt",
        "notes.txt",
    ]
    assert all(entry.freshness is Freshness.CURRENT for entry in listing.documents)
    guide = listing.documents[0]
    assert guide.line_count == 10 and guide.heading_count == 3 and guide.token_estimate > 0
    assert len(guide.short_id) == 8 and guide.document_id.replace("-", "").endswith(guide.short_id)
    assert listing.total_tokens == sum(entry.token_estimate for entry in listing.documents)


def test_changed_and_missing_sources_are_reported(store: _Store) -> None:
    """Detect edits after import by metadata then exact hashing, and missing files."""
    guide = store.documents / "guide.md"
    guide.write_text(GUIDE + "\nNew line.\n", encoding="utf-8")
    (store.documents / "log.csv").unlink()
    access = store.access()
    states = {entry.label: entry.freshness for entry in access.documents().documents}
    assert states["guide.md"] is Freshness.CHANGED
    assert states["log.csv"] is Freshness.MISSING
    found = access.find("reference weight")
    assert found.changed_sources == ("guide.md",)
    # Touching without changing bytes still hashes to the imported version.
    guide.write_text(GUIDE, encoding="utf-8")
    later = time.time() + 5
    os.utime(guide, (later, later))
    assert {entry.label: entry.freshness for entry in access.documents().documents}[
        "guide.md"
    ] is Freshness.CURRENT


def test_references_resolve_by_id_suffix_name_path_and_substring(store: _Store) -> None:
    """Resolve documents flexibly and refuse ambiguous or unknown references."""
    access = store.access()
    guide = access.resolve("guide.md")
    assert access.resolve(guide.document_id).document_id == guide.document_id
    assert access.resolve(guide.document_id[-8:]).document_id == guide.document_id
    assert access.resolve("#" + guide.document_id[-6:]).document_id == guide.document_id
    assert access.resolve("GUIDE").document_id == guide.document_id
    assert access.resolve("team/notes.txt").label == "notes.txt"
    with pytest.raises(AgentDocumentAmbiguous) as ambiguous:
        access.resolve("notes.txt")
    assert len(ambiguous.value.candidates) == 2
    with pytest.raises(AgentDocumentNotFound):
        access.resolve("missing.pdf")
    with pytest.raises(AgentDocumentNotFound):
        access.resolve("   ")


def test_find_ranks_located_passages_across_formats(store: _Store) -> None:
    """Rank the best passage first and search CSV rows under their header."""
    access = store.access()
    found = access.find("How often must the sensor be calibrated?")
    assert found.hits[0].document.label == "guide.md"
    assert (found.hits[0].line_start, found.hits[0].line_end) == (5, 6)
    assert found.hits[0].heading == "Field guide > Calibration"
    rows = access.find("needs service")
    assert rows.hits[0].document.label == "log.csv"
    assert rows.hits[0].heading == "columns: id,device,status"
    scoped = access.find("calibration", document="team/notes.txt", limit=100)
    assert {hit.document.label for hit in scoped.hits} == {"notes.txt"}
    assert access.find("the of and").query_terms == ("the", "of", "and")
    assert access.find("?!").hits == ()


def test_read_selects_lines_sections_and_respects_the_token_bound(store: _Store) -> None:
    """Read by line range, open range or section and report truncation precisely."""
    access = store.access()
    assert access.read("guide.md", lines="5-6").text.startswith("Calibrate the sensor")
    assert access.read("guide.md", lines="8").line_start == 8
    assert access.read("guide.md", lines="8-").line_end == 10
    section = access.read("guide.md", section="storage")
    assert (section.line_start, section.line_end) == (8, 10)
    bounded = access.read("guide.md", max_tokens=50)
    assert bounded.line_start == 1 and bounded.token_estimate <= 60
    long_line = store.documents / "long.txt"
    long_line.write_text("x" * 5_000 + "\nsecond\n", encoding="utf-8")
    store.add(long_line)
    clipped = store.access().read("long.txt", max_tokens=100)
    assert clipped.truncated and clipped.next_line == 2 and "line truncated" in clipped.text


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"page": "1"}, "no pages"),
        ({"lines": "99"}, "beyond"),
        ({"lines": "4-2"}, "empty"),
        ({"lines": "x"}, "must look like"),
        ({"section": "Nope"}, "no heading"),
        ({"lines": "1", "section": "Storage"}, "only one"),
    ],
)
def test_read_rejects_impossible_ranges(
    store: _Store,
    arguments: dict[str, str],
    message: str,
) -> None:
    """Explain invalid selections so an agent can correct them."""
    with pytest.raises(AgentRangeInvalid, match=message):
        store.access().read("guide.md", **arguments)


def test_outline_lists_headings_with_section_sizes(store: _Store) -> None:
    """Return headings with line numbers and token sizes, or nothing for flat text."""
    access = store.access()
    outline = access.outline("guide.md")
    assert [(entry.line, entry.level, entry.text) for entry in outline.entries] == [
        (1, 1, "Field guide"),
        (3, 2, "Calibration"),
        (8, 2, "Storage"),
    ]
    assert outline.entries[0].token_estimate >= outline.entries[1].token_estimate
    assert access.outline("log.csv").entries == ()
    assert access.outline("guide.md", max_entries=1).truncated


def test_verify_quotes_exactly_normalized_or_reports_the_closest_passage(store: _Store) -> None:
    """Verify against exact source text and never accept altered quotes."""
    access = store.access()
    exact = access.verify("The reference weight is 500 grams.")
    assert exact.status is VerifyStatus.VERIFIED
    match = exact.matches[0]
    assert (match.document.label, match.line_start, match.level) == (
        "guide.md",
        6,
        MatchLevel.EXACT,
    )
    assert match.freshness is Freshness.CURRENT
    loose = access.verify("calibrate the SENSOR every morning", document="guide.md")
    assert loose.matches[0].level is MatchLevel.NORMALIZED
    altered = access.verify("The reference weight is 5 kilograms.")
    assert altered.status is VerifyStatus.NOT_FOUND
    assert altered.closest is not None and altered.closest.document.label == "guide.md"
    with pytest.raises(AgentRangeInvalid):
        access.verify("   ")
    with pytest.raises(AgentRangeInvalid):
        access.verify("x" * 5_000)


def test_verify_detects_quotes_that_only_exist_in_an_earlier_version(store: _Store) -> None:
    """Report an outdated citation when a cited version still holds the quote."""
    access = store.access()
    original = access.resolve("guide.md").version_id
    guide = store.documents / "guide.md"
    guide.write_text(GUIDE.replace("500 grams", "750 grams"), encoding="utf-8")
    store.add(guide)
    access = store.access()
    current = access.verify("The reference weight is 500 grams.", document="guide.md")
    assert current.status is VerifyStatus.NOT_FOUND
    outdated = access.verify(
        "The reference weight is 500 grams.",
        document="guide.md",
        version=original[:15],
    )
    assert outdated.status is VerifyStatus.ONLY_IN_OTHER_VERSION
    assert outdated.matches[0].document.version_id == original
    assert not outdated.matches[0].current_version
    with pytest.raises(AgentRangeInvalid):
        access.verify("anything", document="guide.md", version="not-a-version")


def _forge(store: _Store, *statements: str) -> None:
    """Alter the disposable agent index the way corruption or tampering would."""
    with sqlite3.connect(store.path / "agent-cache" / "agent-index.sqlite3") as connection:
        for statement in statements:
            connection.execute(statement)


def test_returned_text_comes_from_authoritative_sources_not_the_index(store: _Store) -> None:
    """Search may use a forged index, but returned text is verified and the entry healed."""
    store.access().refresh()
    _forge(
        store,
        "UPDATE documents SET text = replace(text, '500 grams', '900 grams')",
        "UPDATE passages SET text = replace(text, '500 grams', '900 grams')",
    )
    access = store.access()
    found = access.find("reference weight grams")
    assert found.hits and "500 grams" in found.hits[0].snippet
    assert all("900" not in hit.snippet for hit in found.hits)
    assert "500 grams" in access.read("guide.md", section="Calibration").text
    forged = access.verify("The reference weight is 900 grams.")
    assert forged.status is VerifyStatus.NOT_FOUND
    with sqlite3.connect(store.path / "agent-cache" / "agent-index.sqlite3") as connection:
        remaining = connection.execute(
            "SELECT (SELECT count(*) FROM documents WHERE text LIKE '%900 grams%')"
            " + (SELECT count(*) FROM passages WHERE text LIKE '%900 grams%')"
        ).fetchone()[0]
    assert remaining == 0


def test_a_forged_index_cannot_verify_an_invented_quote(store: _Store) -> None:
    """Confirm positive verification against CAS text, never against cached text."""
    store.access().refresh()
    _forge(
        store,
        "UPDATE documents SET text = text || char(10) || 'Sensors may be submerged.'",
    )
    access = store.access()
    assert access.verify("Sensors may be submerged.").status is VerifyStatus.NOT_FOUND
    assert access.verify("Sensors may be submerged.", document="guide.md").matches == ()


def test_forged_identity_metadata_is_replaced_from_the_catalog(store: _Store) -> None:
    """Rebuild an entry whose recorded path no longer matches the catalog."""
    access = store.access()
    guide = access.resolve("guide.md")
    _forge(
        store,
        "UPDATE documents SET facts = json_set(facts, '$.locator', '/elsewhere/other.md')",
    )
    access = store.access()
    assert "guide.md" in access.refresh().rebuilt
    assert access.resolve("guide.md").locator == guide.locator
