"""Privacy-canary release evidence coverage."""

from __future__ import annotations

import json
import tarfile
import zipfile
from pathlib import Path

import pytest

from openardp.adapters.release_security import (
    SecurityEvidenceMalformed,
    privacy_checks,
    scan_privacy_canaries,
)
from openardp.domain.release import EvidenceStatus


def test_privacy_canary_scan_is_digest_only(tmp_path: Path) -> None:
    """Detect cleartext in files/archives while retaining only digest and counts."""
    canary = b"PRIVATE-RELEASE-CANARY"
    clean = tmp_path / "clean.json"
    clean.write_text(json.dumps({"status": "passed"}), encoding="utf-8")
    archive = tmp_path / "result.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("nested/result.txt", b"prefix " + canary)
    results = scan_privacy_canaries(
        (clean, archive),
        {"body": canary},
        allowed_occurrences={"body": 0},
    )
    assert results[0].status == "failed"
    assert results[0].observed_occurrences == 1
    assert canary.decode() not in repr(results)
    checks = privacy_checks(results)
    assert checks[0].status is EvidenceStatus.FAILED
    assert checks[0].reason == "privacy-disclosure-detected"


def test_clean_canary_scan_passes_and_symlink_input_is_rejected(tmp_path: Path) -> None:
    """Distinguish a genuine clean scan from an unsafe path that was never scanned."""
    clean = tmp_path / "clean.txt"
    clean.write_bytes(b"body-free evidence")
    results = scan_privacy_canaries((clean,), {"secret": b"ABSENT-CANARY"})
    assert results[0].status == "passed"
    assert privacy_checks(results)[0].status is EvidenceStatus.PASSED
    linked = tmp_path / "linked.txt"
    linked.symlink_to(clean)
    with pytest.raises(SecurityEvidenceMalformed, match="unsafe"):
        scan_privacy_canaries((linked,), {"secret": b"ABSENT-CANARY"})


def test_privacy_scan_rejects_invalid_limits_and_archive_paths(tmp_path: Path) -> None:
    """Fail closed for invalid policy and archive traversal before scanning bytes."""
    clean = tmp_path / "clean.txt"
    clean.write_bytes(b"clean")
    with pytest.raises(SecurityEvidenceMalformed, match="non-empty"):
        scan_privacy_canaries((clean,), {"empty": b""})
    with pytest.raises(SecurityEvidenceMalformed, match="cannot be negative"):
        scan_privacy_canaries(
            (clean,),
            {"secret": b"ABSENT"},
            allowed_occurrences={"secret": -1},
        )

    archive = tmp_path / "traversal.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("../escaped.txt", b"clean")
    with pytest.raises(SecurityEvidenceMalformed, match="path is unsafe"):
        scan_privacy_canaries((archive,), {"secret": b"ABSENT"})


def test_privacy_scan_reads_regular_tar_members_and_rejects_links(tmp_path: Path) -> None:
    """Scan tar payloads without following archive links."""
    canary = b"PRIVATE-TAR-CANARY"
    payload = tmp_path / "payload.txt"
    payload.write_bytes(canary)
    archive = tmp_path / "result.tar"
    with tarfile.open(archive, "w") as handle:
        handle.add(payload, arcname="nested/payload.txt")
    result = scan_privacy_canaries((archive,), {"tar": canary})
    assert result[0].observed_occurrences == 1

    linked_archive = tmp_path / "linked.tar"
    with tarfile.open(linked_archive, "w") as handle:
        info = tarfile.TarInfo("nested/link")
        info.type = tarfile.SYMTYPE
        info.linkname = "../payload.txt"
        handle.addfile(info)
    with pytest.raises(SecurityEvidenceMalformed, match="link is unsafe"):
        scan_privacy_canaries((linked_archive,), {"tar": canary})
