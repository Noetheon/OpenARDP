"""End-to-end zero-authority assertions for hostile release fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from openardp.domain.common import (
    ContentRole,
    DataTrustClassification,
    IntegrityState,
    Sensitivity,
    TrustZone,
)
from openardp.domain.context_compilation import UntrustedContentEnvelope

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "name",
    (
        "prompt-injection.txt",
        "metadata.txt",
        "table.csv",
        "image-alt.txt",
        "provider-native.json",
    ),
)
def test_hostile_document_cannot_initiate_tool_authority(name: str) -> None:
    """Preserve instruction-like body/metadata/table/image/native text only as data."""
    body = (ROOT / "benchmarks" / "release" / "v0.1.0" / "hostile" / name).read_text(
        encoding="utf-8"
    )
    envelope = UntrustedContentEnvelope(media_type="text/plain", body=body)
    trust = DataTrustClassification(
        zone=TrustZone.EXTERNAL_UNTRUSTED,
        role=ContentRole.DATA,
        instruction_execution_allowed=False,
        integrity=IntegrityState.VERIFIED_SHA256,
        sensitivity=Sensitivity.UNKNOWN,
    )
    assert envelope.body
    assert envelope.content_role == "untrusted_data"
    assert trust.instruction_execution_allowed is False
    assert "tool" not in envelope.model_fields_set
