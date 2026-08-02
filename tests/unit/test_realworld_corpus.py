"""Contract tests for the frozen F024 corpus and explicit reproducer."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.realworld_corpus import (
    CorpusError,
    DownloadStream,
    corpus_identity,
    load_corpus_lock,
    reproduce_corpus,
    verify_corpus,
)

ROOT = Path(__file__).parents[2]
CORPUS = ROOT / "corpora/realworld/v0.1.0"


def test_committed_corpus_has_exact_six_format_identity() -> None:
    """Bind the real payload count, byte total, formats and canonical identity."""
    verified = verify_corpus(CORPUS)

    assert verified.corpus_id == (
        "sha256:5e505148c7e9004a9c1ae7bd68c66addfc9ae3377be7e3057a81d7a1996649bd"
    )
    assert verified.payload_count == 6
    assert verified.payload_bytes == 6_634_970
    assert verified.formats == ("csv", "docx", "md", "pdf", "pptx", "txt")
    assert verified.rights_ids == ("cisa-kev-cc0-1.0", "nasa-ntrs-public-use")


def test_identity_covers_metadata_but_excludes_declared_id() -> None:
    """Compute identity from the complete lock projection except its self field."""
    lock = load_corpus_lock(CORPUS)
    assert corpus_identity(lock) == lock["corpus_id"]
    changed = dict(lock)
    changed["aggregate_payload_bytes"] = 1
    assert corpus_identity(changed) != lock["corpus_id"]
    changed["corpus_id"] = "sha256:" + "f" * 64
    assert corpus_identity(changed) == corpus_identity({**changed, "corpus_id": "ignored"})


def test_lock_requires_sorted_unique_closed_assets(tmp_path: Path) -> None:
    """Reject ambiguous ordering before tree access."""
    target = tmp_path / "corpus"
    shutil.copytree(CORPUS, target)
    lock_path = target / "corpus-lock.json"
    lock = json.loads(lock_path.read_bytes())
    lock["assets"] = list(reversed(lock["assets"]))
    lock["corpus_id"] = corpus_identity(lock)
    lock_path.write_text(json.dumps(lock), encoding="utf-8")

    with pytest.raises(CorpusError, match="lock_order"):
        verify_corpus(target)


def test_explicit_reproduction_matches_committed_tree(tmp_path: Path) -> None:
    """Publish exact fetched payloads only after complete validation."""
    lock = load_corpus_lock(CORPUS)
    by_url = {item["source_url"]: item for item in lock["assets"]}

    def fetch(url: str) -> DownloadStream:
        asset = by_url[url]
        payload = (CORPUS / asset["path"]).read_bytes()
        return DownloadStream(
            chunks=(payload[:17], payload[17:]),
            content_type=asset["expected_content_types"][0],
            final_url=url,
        )

    destination = tmp_path / "reproduced"
    result = reproduce_corpus(CORPUS, destination, fetcher=fetch)

    assert result.corpus_id == lock["corpus_id"]
    assert verify_corpus(destination) == result
    assert destination.is_dir()
    assert not tuple(tmp_path.glob(".reproduced-stage-*"))


def test_reproduction_refuses_existing_destination(tmp_path: Path) -> None:
    """Never merge freshly fetched bytes into accepted state."""
    destination = tmp_path / "existing"
    destination.mkdir()

    with pytest.raises(FileExistsError):
        reproduce_corpus(CORPUS, destination, fetcher=lambda _url: pytest.fail())


def test_reproduction_rejects_wrong_content_type_without_publication(tmp_path: Path) -> None:
    """Reject an HTML/error-style response before accepting its bytes."""
    lock = load_corpus_lock(CORPUS)
    first = lock["assets"][0]

    def fetch(url: str) -> DownloadStream:
        asset = next(item for item in lock["assets"] if item["source_url"] == url)
        return DownloadStream(
            chunks=((CORPUS / asset["path"]).read_bytes(),),
            content_type="text/html",
            final_url=url,
        )

    destination = tmp_path / "rejected"
    with pytest.raises(CorpusError, match="response_type"):
        reproduce_corpus(CORPUS, destination, fetcher=fetch)

    assert not destination.exists()
    assert first["expected_content_types"] != ["text/html"]
    assert not tuple(tmp_path.glob(".rejected-stage-*"))
