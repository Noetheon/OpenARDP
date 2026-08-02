"""Integration tests for producer/validator independence and lifecycle."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from scripts.realworld_corpus import DownloadStream, load_corpus_lock, reproduce_corpus

ROOT = Path(__file__).parents[2]
CORPUS = ROOT / "corpora/realworld/v0.1.0"


def _validate(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed local interpreter and script.
        [sys.executable, str(ROOT / "scripts/validate_realworld_corpus.py"), "--corpus", str(path)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_independent_validator_accepts_committed_corpus() -> None:
    """Validate real bytes without importing the producer implementation."""
    result = _validate(CORPUS)
    assert result.returncode == 0
    assert "payloads=6" in result.stdout
    assert "bytes=6634970" in result.stdout
    assert "Traceback" not in result.stderr


def test_independent_validator_rejects_producer_visible_tamper(tmp_path: Path) -> None:
    """Ensure agreement is based on bytes rather than shared validation code."""
    target = tmp_path / "corpus"
    shutil.copytree(CORPUS, target)
    (target / "evidence/cisa-kev-revision.json").write_text("{}\n", encoding="utf-8")

    result = _validate(target)
    assert result.returncode == 6
    assert result.stdout.strip() == "corpus_invalid"
    assert "Traceback" not in result.stderr


def test_reproduced_tree_passes_independent_validator(tmp_path: Path) -> None:
    """Cover staging, publication and independent use as one lifecycle."""
    lock = load_corpus_lock(CORPUS)
    by_url = {item["source_url"]: item for item in lock["assets"]}

    def fetch(url: str) -> DownloadStream:
        asset = by_url[url]
        return DownloadStream(
            chunks=((CORPUS / asset["path"]).read_bytes(),),
            content_type=asset["expected_content_types"][0],
            final_url=url,
        )

    destination = tmp_path / "published"
    reproduce_corpus(CORPUS, destination, fetcher=fetch)

    result = _validate(destination)
    assert result.returncode == 0
    assert lock["corpus_id"] in result.stdout
