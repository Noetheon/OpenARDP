"""Malformed parser input boundaries for release evidence."""

from __future__ import annotations

from pathlib import Path

import pytest

from openardp.adapters.release_benchmarks import (
    BenchmarkCase,
    BenchmarkTreatmentUnavailable,
    RawReparseTreatment,
)


def test_malformed_archive_is_bounded_and_body_free(tmp_path: Path) -> None:
    """Map corrupt native input to one stable category without leaking bytes or paths."""
    hostile = b"TOP-SECRET-CANARY-not-a-zip"
    source = tmp_path / "hostile.docx"
    source.write_bytes(hostile)
    case = BenchmarkCase("hostile-docx", "hostile-docx", source, ("query",), ("query",))
    with pytest.raises(BenchmarkTreatmentUnavailable) as captured:
        RawReparseTreatment().execute(case)
    assert str(captured.value) == "archive-malformed"
    assert hostile.decode() not in str(captured.value)
    assert str(tmp_path) not in str(captured.value)
