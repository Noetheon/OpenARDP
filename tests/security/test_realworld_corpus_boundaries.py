"""Adversarial filesystem, source, rights and network tests for F024."""

from __future__ import annotations

import json
import os
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


def _copy(tmp_path: Path) -> Path:
    target = tmp_path / "corpus"
    shutil.copytree(CORPUS, target)
    return target


@pytest.mark.parametrize("mutation", ("missing", "extra", "changed"))
def test_closed_tree_rejects_payload_drift(tmp_path: Path, mutation: str) -> None:
    """Reject missing, extra and digest-mismatching payload state."""
    target = _copy(tmp_path)
    payload = target / "sources/cisa-kev-license.txt"
    if mutation == "missing":
        payload.unlink()
    elif mutation == "extra":
        (target / "sources/extra.txt").write_text("extra", encoding="utf-8")
    else:
        payload.write_bytes(payload.read_bytes() + b"x")

    with pytest.raises(CorpusError, match=r"tree_inventory|byte_mismatch"):
        verify_corpus(target)


def test_closed_tree_rejects_symlink(tmp_path: Path) -> None:
    """Never follow a link inside the corpus authority boundary."""
    target = _copy(tmp_path)
    payload = target / "sources/cisa-kev-license.txt"
    payload.unlink()
    try:
        payload.symlink_to(target / "README.md")
    except OSError as error:  # pragma: no cover - Windows policy dependent
        pytest.skip(f"symlink unavailable: {error}")

    with pytest.raises(CorpusError, match="unsafe_tree"):
        verify_corpus(target)


@pytest.mark.parametrize("field", ("rights", "evidence_files"))
def test_lock_rejects_incomplete_review_mapping(tmp_path: Path, field: str) -> None:
    """Do not treat mechanically valid payloads as review-complete."""
    target = _copy(tmp_path)
    path = target / "corpus-lock.json"
    lock = json.loads(path.read_bytes())
    lock[field] = lock[field][:-1]
    path.write_text(json.dumps(lock), encoding="utf-8")

    with pytest.raises(CorpusError, match=r"identity|rights_mapping|evidence_mapping"):
        verify_corpus(target)


def test_lock_rejects_case_colliding_paths(tmp_path: Path) -> None:
    """Prevent a valid lock from becoming ambiguous on case-folding filesystems."""
    target = _copy(tmp_path)
    path = target / "corpus-lock.json"
    lock = json.loads(path.read_bytes())
    duplicate = dict(lock["assets"][0])
    duplicate["path"] = lock["assets"][0]["path"].upper()
    duplicate["key"] = "case-collision"
    lock["assets"].append(duplicate)
    lock["corpus_id"] = corpus_identity(lock)
    path.write_text(json.dumps(lock), encoding="utf-8")

    with pytest.raises(CorpusError, match=r"lock_count|path_collision"):
        verify_corpus(target)


@pytest.mark.parametrize(
    ("final_url", "content_type", "category"),
    (
        ("https://example.invalid/payload", "text/plain", "redirect_host"),
        ("http://raw.githubusercontent.com/payload", "text/plain", "redirect_scheme"),
        (
            "https://raw.githubusercontent.com/cisagov/kev-data/payload",
            "application/octet-stream",
            "response_type",
        ),
    ),
)
def test_reproduction_rejects_unreviewed_response_authority(
    tmp_path: Path,
    final_url: str,
    content_type: str,
    category: str,
) -> None:
    """Keep redirects and response media inside the committed authority set."""
    destination = tmp_path / "rejected"

    with pytest.raises(CorpusError, match=category):
        reproduce_corpus(
            CORPUS,
            destination,
            fetcher=lambda _url: DownloadStream(
                chunks=(b"not accepted",),
                content_type=content_type,
                final_url=final_url,
            ),
        )
    assert not destination.exists()


@pytest.mark.parametrize("mode", ("truncated", "oversize", "transport"))
def test_reproduction_fails_closed_on_stream_errors(tmp_path: Path, mode: str) -> None:
    """Remove staging and publish nothing on every bounded download failure."""
    lock = load_corpus_lock(CORPUS)
    by_url = {item["source_url"]: item for item in lock["assets"]}

    def fetch(url: str) -> DownloadStream:
        if mode == "transport":
            raise OSError("private upstream response body must not escape")
        asset = by_url[url]
        payload = (CORPUS / asset["path"]).read_bytes()
        chunks = (payload[:-1],) if mode == "truncated" else (b"x" * 8_388_609,)
        return DownloadStream(
            chunks=chunks,
            content_type=asset["expected_content_types"][0],
            final_url=url,
        )

    destination = tmp_path / "rejected"
    with pytest.raises((CorpusError, OSError)):
        reproduce_corpus(CORPUS, destination, fetcher=fetch)
    assert not destination.exists()
    assert not tuple(tmp_path.glob(".rejected-stage-*"))


def test_notices_do_not_claim_legal_certainty_or_endorsement() -> None:
    """Keep outward rights statements explicitly bounded."""
    text = (CORPUS / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8").lower()
    assert "not legal advice" in text
    assert "does not imply nasa endorsement" in text
    assert "no cisa endorsement" in text
    assert "legally guaranteed" not in text


def test_validation_does_not_open_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """The ordinary verification path must have no egress capability."""
    monkeypatch.setattr(
        "socket.socket",
        lambda *_args, **_kwargs: pytest.fail("network attempted"),
    )
    assert verify_corpus(CORPUS).payload_count == 6


def test_hard_link_alias_is_rejected_when_supported(tmp_path: Path) -> None:
    """Reject a source that aliases authority outside its declared path."""
    target = _copy(tmp_path)
    payload = target / "sources/cisa-kev-license.txt"
    alias = tmp_path / "outside.txt"
    try:
        os.link(payload, alias)
    except OSError as error:  # pragma: no cover - filesystem dependent
        pytest.skip(f"hard links unavailable: {error}")

    with pytest.raises(CorpusError, match="unsafe_tree"):
        verify_corpus(target)
