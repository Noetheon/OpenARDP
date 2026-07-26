"""Executable contract tests for experimental evidence records."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from openardp.domain.common import IntegrityState, Sensitivity, TrustZone
from openardp.domain.evidence import (
    EvidenceProjection,
    EvidenceReference,
    NativeRepresentation,
    OpaqueProviderPointerAnchor,
    PageRegionAnchor,
    ProjectionProvenance,
    ProviderPointer,
    ProviderRecipe,
    RetrievalHandle,
    TableCellAnchor,
    TextSpanAnchor,
    TrustClassification,
    validate_evidence_records,
)
from openardp.domain.identity import (
    evidence_projection_id,
    evidence_reference_id,
    native_representation_id,
)

SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
NOW = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)


def provider() -> ProviderRecipe:
    """Return one synthetic provider recipe."""
    return ProviderRecipe(
        name="synthetic-rich-parser",
        version="1.2.3",
        profile="portable",
        profile_version="0.4.0",
        config_hash=SHA_C,
    )


def native(**changes: object) -> NativeRepresentation:
    """Build one valid native record with a recomputed identity."""
    values: dict[str, object] = {
        "contract_version": "0.1.0",
        "stability": "experimental",
        "source_version_id": SHA_A,
        "native_artifact_id": SHA_B,
        "native_artifact_media_type": "application/json",
        "native_artifact_byte_length": 123,
        "provider": provider(),
        "created_at": NOW,
        "extensions": {},
    }
    values.update(changes)
    recipe = values["provider"]
    assert isinstance(recipe, ProviderRecipe)
    values["native_representation_id"] = native_representation_id(
        source_version_id=str(values["source_version_id"]),
        native_artifact_id=str(values["native_artifact_id"]),
        native_artifact_media_type=str(values["native_artifact_media_type"]),
        provider_name=recipe.name,
        provider_version=recipe.version,
        provider_profile=recipe.profile,
        provider_profile_version=recipe.profile_version,
        provider_config_hash=recipe.config_hash,
    )
    return NativeRepresentation.model_validate(values)


def text_anchor() -> TextSpanAnchor:
    """Return one bounded source text span."""
    return TextSpanAnchor(
        anchor_type="text_span",
        coordinate_system="unicode_code_points",
        start=5,
        end=12,
        text_length=20,
    )


def reference(
    anchor: object | None = None,
    **changes: object,
) -> EvidenceReference:
    """Build one valid evidence reference."""
    values: dict[str, object] = {
        "contract_version": "0.1.0",
        "stability": "experimental",
        "source_version_id": SHA_A,
        "native_representation_id": native().native_representation_id,
        "anchor": text_anchor() if anchor is None else anchor,
        "extensions": {},
    }
    values.update(changes)
    anchor_value = values["anchor"]
    assert isinstance(
        anchor_value,
        (TextSpanAnchor, PageRegionAnchor, TableCellAnchor, OpaqueProviderPointerAnchor),
    )
    values["evidence_reference_id"] = evidence_reference_id(
        source_version_id=str(values["source_version_id"]),
        native_representation_id=str(values["native_representation_id"]),
        anchor=anchor_value.model_dump(mode="json"),
    )
    return EvidenceReference.model_validate(values)


def trust(**changes: object) -> TrustClassification:
    """Build one valid untrusted-data classification."""
    values: dict[str, object] = {
        "contract_version": "0.1.0",
        "stability": "experimental",
        "origin_zone": "external_untrusted",
        "effective_zone": "external_untrusted",
        "role": "data",
        "instruction_execution_allowed": False,
        "integrity": "verified_sha256",
        "sensitivity": "internal",
        "extensions": {},
    }
    values.update(changes)
    if isinstance(values["origin_zone"], str):
        values["origin_zone"] = TrustZone(values["origin_zone"])
    if isinstance(values["effective_zone"], str):
        values["effective_zone"] = TrustZone(values["effective_zone"])
    if isinstance(values["integrity"], str):
        values["integrity"] = IntegrityState(values["integrity"])
    if isinstance(values["sensitivity"], str):
        values["sensitivity"] = Sensitivity(values["sensitivity"])
    return TrustClassification.model_validate(values)


def projection(**changes: object) -> EvidenceProjection:
    """Build one valid thin evidence projection."""
    item_reference = reference()
    provenance = ProjectionProvenance(
        generator_name="synthetic-projector",
        generator_version="1.0.0",
        generator_config_hash=SHA_D,
        created_at=NOW,
    )
    retrieval = RetrievalHandle(
        artifact_id=SHA_C,
        media_type="text/plain",
        byte_length=42,
    )
    values: dict[str, object] = {
        "contract_version": "0.1.0",
        "stability": "experimental",
        "source_version_id": SHA_A,
        "native_representation_id": native().native_representation_id,
        "reference": item_reference,
        "retrieval": retrieval,
        "parent_projection_id": None,
        "ordinal": 0,
        "trust": trust(),
        "provenance": provenance,
        "extensions": {},
    }
    values.update(changes)
    current_reference = values["reference"]
    current_retrieval = values["retrieval"]
    current_provenance = values["provenance"]
    assert isinstance(current_reference, EvidenceReference)
    assert isinstance(current_retrieval, RetrievalHandle)
    assert isinstance(current_provenance, ProjectionProvenance)
    values["evidence_projection_id"] = evidence_projection_id(
        source_version_id=str(values["source_version_id"]),
        native_representation_id=str(values["native_representation_id"]),
        evidence_reference_id=current_reference.evidence_reference_id,
        retrieval_artifact_id=current_retrieval.artifact_id,
        retrieval_media_type=current_retrieval.media_type,
        parent_projection_id=(
            str(values["parent_projection_id"])
            if values["parent_projection_id"] is not None
            else None
        ),
        ordinal=int(values["ordinal"]),
        generator_name=current_provenance.generator_name,
        generator_version=current_provenance.generator_version,
        generator_config_hash=current_provenance.generator_config_hash,
    )
    return EvidenceProjection.model_validate(values)


@pytest.mark.parametrize(
    ("version", "message"),
    (
        ("invalid", "semantic version"),
        ("0.2.0", "not installed"),
        ("1.0.0", "unsupported contract major"),
    ),
)
def test_contract_version_failure_categories(version: str, message: str) -> None:
    """Keep compatibility failures distinguishable."""
    with pytest.raises(ValidationError, match=message):
        trust(contract_version=version)


def test_extensions_require_absolute_namespace_and_preserve_json() -> None:
    """Preserve only namespaced interoperable JSON extension values."""
    extension = {"https://example.test/evidence/quality": {"score": 1}}
    record = trust(extensions=extension)
    assert record.extensions == extension
    with pytest.raises(ValidationError, match="absolute URI"):
        trust(extensions={"quality": 1})


def test_native_identity_excludes_observations_but_includes_recipe() -> None:
    """Keep time/length out and exact provider recipe in native identity."""
    first = native()
    later = native(
        native_artifact_byte_length=999,
        created_at=datetime(2026, 7, 26, 13, 0, tzinfo=UTC),
    )
    changed = native(
        provider=provider().model_copy(update={"profile_version": "0.4.1"}),
    )
    assert first.native_representation_id == later.native_representation_id
    assert first.native_representation_id != changed.native_representation_id


@pytest.mark.parametrize(
    "values",
    (
        {"start": 3, "end": 3},
        {"start": 4, "end": 3},
        {"start": 2, "end": 9, "text_length": 8},
    ),
)
def test_text_span_rejects_empty_reversed_or_out_of_extent(values: dict[str, int]) -> None:
    """Enforce bounded half-open text offsets."""
    with pytest.raises(ValidationError):
        TextSpanAnchor(
            anchor_type="text_span",
            coordinate_system="unicode_code_points",
            **values,
        )


def test_fixed_point_page_region_accepts_bounds_and_rejects_overflow() -> None:
    """Use exact integer page geometry with positive in-page area."""
    valid = PageRegionAnchor(
        anchor_type="page_region",
        coordinate_system="normalized_ppm_top_left",
        page_number=1,
        x=250_000,
        y=100_000,
        width=500_000,
        height=900_000,
    )
    assert valid.x + valid.width == 750_000
    with pytest.raises(ValidationError, match="page bounds"):
        valid.model_copy(update={"width": 800_000}).model_validate(
            {
                **valid.model_dump(mode="json"),
                "width": 800_000,
            }
        )


def test_table_and_opaque_pointers_are_profile_scoped_and_bounded() -> None:
    """Validate cells while keeping provider targets uninterpreted."""
    pointer = ProviderPointer(
        provider_profile="portable",
        provider_profile_version="0.4.0",
        pointer_format="synthetic-node-id",
        pointer="tables/7",
    )
    cell = TableCellAnchor(
        anchor_type="table_cell",
        table=pointer,
        row_index=0,
        column_index=2,
        row_span=2,
        column_span=1,
    )
    assert reference(cell).anchor == cell
    assert reference(OpaqueProviderPointerAnchor(anchor_type="provider_pointer", target=pointer))
    with pytest.raises(ValidationError, match="control"):
        pointer.model_copy(update={"pointer": "bad\npointer"}).model_validate(
            {**pointer.model_dump(mode="json"), "pointer": "bad\npointer"}
        )


def test_reference_declared_identity_and_scope_are_enforced() -> None:
    """Reject drifted identities and stale source/native bindings."""
    item = reference()
    with pytest.raises(ValidationError, match="evidence_reference_id"):
        EvidenceReference.model_validate(
            {**item.model_dump(mode="json"), "evidence_reference_id": SHA_D}
        )
    with pytest.raises(ValueError, match="expected source version"):
        validate_evidence_records(native(), [item], [], expected_source_version_id=SHA_B)


@pytest.mark.parametrize(
    ("origin", "effective"),
    (
        ("local_trusted", "local_trusted"),
        ("local_trusted", "organization_trusted"),
        ("local_trusted", "external_untrusted"),
        ("local_trusted", "model_derived"),
        ("organization_trusted", "organization_trusted"),
        ("organization_trusted", "external_untrusted"),
        ("organization_trusted", "model_derived"),
        ("external_untrusted", "external_untrusted"),
        ("external_untrusted", "model_derived"),
        ("model_derived", "model_derived"),
    ),
)
def test_allowed_trust_transitions(origin: str, effective: str) -> None:
    """Allow equality, conservative downgrade, and derived classification."""
    assert trust(origin_zone=origin, effective_zone=effective).effective_zone == effective


@pytest.mark.parametrize(
    ("origin", "effective"),
    (
        ("organization_trusted", "local_trusted"),
        ("external_untrusted", "organization_trusted"),
        ("external_untrusted", "local_trusted"),
        ("model_derived", "organization_trusted"),
        ("model_derived", "local_trusted"),
        ("model_derived", "external_untrusted"),
    ),
)
def test_trust_promotion_is_rejected(origin: str, effective: str) -> None:
    """Reject evidence authority escalation."""
    with pytest.raises(ValidationError, match="trust promotion"):
        trust(origin_zone=origin, effective_zone=effective)


def test_projection_is_thin_source_bound_and_identity_checked() -> None:
    """Bind navigation/retrieval records without a complete provider tree."""
    item = projection()
    assert item.retrieval.artifact_id == SHA_C
    assert not hasattr(item, "content")
    with pytest.raises(ValidationError, match="reference source"):
        EvidenceProjection.model_validate(
            {
                "contract_version": item.contract_version,
                "stability": item.stability,
                "evidence_projection_id": item.evidence_projection_id,
                "source_version_id": SHA_B,
                "native_representation_id": item.native_representation_id,
                "reference": item.reference,
                "retrieval": item.retrieval,
                "parent_projection_id": item.parent_projection_id,
                "ordinal": item.ordinal,
                "trust": item.trust,
                "provenance": item.provenance,
                "extensions": item.extensions,
            }
        )


def test_aggregate_accepts_coherent_records_and_rejects_native_mismatch() -> None:
    """Validate a complete in-memory evidence set without I/O."""
    native_record = native()
    item_reference = reference()
    item_projection = projection(reference=item_reference)
    validate_evidence_records(native_record, [item_reference], [item_projection])
    with pytest.raises(ValueError, match="native representation"):
        validate_evidence_records(
            native(native_artifact_id=SHA_D),
            [item_reference],
            [item_projection],
        )


def test_aggregate_rejects_duplicate_identifier_semantic_collision() -> None:
    """Reject one identifier reused with different non-identity metadata."""
    item_reference = reference()
    conflicting = item_reference.model_copy(
        update={"extensions": {"https://example.test/conflict": True}}
    )
    with pytest.raises(ValueError, match="non-identical"):
        validate_evidence_records(native(), [item_reference, conflicting], [])


def test_table_index_span_arithmetic_stays_in_safe_range() -> None:
    """Reject otherwise valid integers whose cell extent is not interoperable."""
    pointer = ProviderPointer(
        provider_profile="portable",
        provider_profile_version="0.4.0",
        pointer_format="synthetic-node-id",
        pointer="tables/7",
    )
    with pytest.raises(ValidationError, match="safe integer range"):
        TableCellAnchor(
            anchor_type="table_cell",
            table=pointer,
            row_index=9_007_199_254_740_990,
            column_index=0,
            row_span=2,
            column_span=1,
        )
