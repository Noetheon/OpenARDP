"""Provider-free listing, retrieval, native access and pointer resolution tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from openardp.domain.evidence import ProviderPointer
from openardp.ports.catalog import RepresentationIntegrityError
from openardp.ports.parser import InvalidRichParserOutput, RichParserResourceLimitExceeded
from openardp.services.rich_evidence import RichEvidenceService
from tests.integration.test_rich_ingestion import (
    _Clock,
    _Parser,
    _service,
    _TamperingStore,
)


def test_rich_evidence_listing_retrieval_native_and_resolution_are_exact(
    tmp_path: Path,
) -> None:
    """Consume accepted F006 evidence without invoking or exposing provider runtime types."""
    source = tmp_path / "source.docx"
    source.write_bytes(b"source-v1")
    parser = _Parser()
    ingestion, store, catalog = _service(tmp_path, parser, clock=_Clock())
    result = ingestion.ingest(source)
    evidence = RichEvidenceService(
        store,
        catalog,
        representation_verifier=ingestion.verify_ready_representation,
    )

    projections = evidence.list(result.scope.document_id)
    retrieved = evidence.get(
        projections[0].evidence_projection_id,
        document_id=result.scope.document_id,
    )
    native = evidence.native(result.scope.document_id)
    pointer = ProviderPointer(
        provider_profile="openardp-docling-native",
        provider_profile_version="0.1.0",
        pointer_format="rfc6901-json-pointer",
        pointer="#/texts/0/text",
    )

    assert len(projections) == 1
    assert retrieved.body == "synthetic"
    assert retrieved.projection == projections[0]
    assert native["schema_name"] == "DoclingDocument"
    assert evidence.resolve(result.scope.document_id, pointer) == "synthetic"
    assert parser.calls == 1


def test_rich_pointer_profile_missing_target_and_bounds_fail_closed(
    tmp_path: Path,
) -> None:
    """Reject profile confusion, missing targets and oversized resolved values."""
    source = tmp_path / "source.docx"
    source.write_bytes(b"source-v1")
    parser = _Parser()
    ingestion, store, catalog = _service(tmp_path, parser, clock=_Clock())
    result = ingestion.ingest(source)
    evidence = RichEvidenceService(
        store,
        catalog,
        representation_verifier=ingestion.verify_ready_representation,
    )
    wrong_profile = ProviderPointer(
        provider_profile="other-provider",
        provider_profile_version="0.1.0",
        pointer_format="rfc6901-json-pointer",
        pointer="#/texts/0",
    )
    missing = ProviderPointer(
        provider_profile="openardp-docling-native",
        provider_profile_version="0.1.0",
        pointer_format="rfc6901-json-pointer",
        pointer="#/texts/99",
    )
    valid = missing.model_copy(update={"pointer": "#/texts/0"})

    with pytest.raises(ValueError, match="profile"):
        evidence.resolve(result.scope.document_id, wrong_profile)
    with pytest.raises(InvalidRichParserOutput, match="missing"):
        evidence.resolve(result.scope.document_id, missing)
    with pytest.raises(RichParserResourceLimitExceeded, match="limit"):
        evidence.resolve(
            result.scope.document_id,
            valid,
            max_resolved_bytes=1,
        )


def test_exact_retrieval_tamper_is_rejected_before_body_return(
    tmp_path: Path,
) -> None:
    """Digest-verify the explicitly selected body after aggregate verification."""
    source = tmp_path / "source.docx"
    source.write_bytes(b"source-v1")
    parser = _Parser()
    ingestion, store, catalog = _service(tmp_path, parser, clock=_Clock())
    result = ingestion.ingest(source)
    artifacts = catalog.load_rich_representation(result.scope)
    assert artifacts is not None
    record = artifacts.bundle.records[0]
    evidence = RichEvidenceService(
        _TamperingStore(store, record.retrieval_object.object_id),
        catalog,
        representation_verifier=lambda _artifacts: None,
    )

    with pytest.raises(RepresentationIntegrityError, match="invalid"):
        evidence.get(
            record.projection.evidence_projection_id,
            document_id=result.scope.document_id,
        )
