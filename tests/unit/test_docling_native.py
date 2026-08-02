"""Pure native-export, projection, coordinate and pointer tests for F007."""

from __future__ import annotations

import copy

import pytest

from openardp.adapters.docling_native import (
    build_text_view,
    normalize_docling_export,
    page_region_from_provenance,
    project_native_document,
    resolve_json_pointer,
)
from openardp.domain.evidence import (
    OpaqueProviderPointerAnchor,
    PageRegionAnchor,
    TableCellAnchor,
)
from openardp.domain.rich_ingestion import RichEvidenceKind, RichParserLimits
from openardp.ports.parser import InvalidRichParserOutput, RichParserResourceLimitExceeded


def _native_document() -> dict[str, object]:
    return {
        "schema_name": "DoclingDocument",
        "version": "1.8.0",
        "name": "synthetic",
        "origin": None,
        "furniture": {"self_ref": "#/furniture", "children": [], "name": "_root_"},
        "body": {"self_ref": "#/body", "children": [], "name": "_root_"},
        "groups": [],
        "texts": [
            {
                "self_ref": "#/texts/0",
                "parent": {"$ref": "#/body"},
                "children": [],
                "label": "section_header",
                "text": "Heading",
                "prov": [],
            },
            {
                "self_ref": "#/texts/1",
                "parent": {"$ref": "#/texts/0"},
                "children": [],
                "label": "text",
                "text": "Paragraph",
                "prov": [
                    {
                        "page_no": 1,
                        "bbox": {
                            "l": 10.0,
                            "t": 180.0,
                            "r": 60.0,
                            "b": 80.0,
                            "coord_origin": "BOTTOMLEFT",
                        },
                    }
                ],
            },
            {
                "self_ref": "#/texts/2",
                "parent": {"$ref": "#/body"},
                "children": [],
                "label": "future_label",
                "text": "Native only",
                "prov": [],
            },
        ],
        "pictures": [
            {
                "self_ref": "#/pictures/0",
                "parent": {"$ref": "#/body"},
                "children": [],
                "label": "picture",
                "prov": [],
            }
        ],
        "tables": [
            {
                "self_ref": "#/tables/0",
                "parent": {"$ref": "#/body"},
                "children": [],
                "label": "table",
                "prov": [],
                "data": {
                    "num_rows": 1,
                    "num_cols": 1,
                    "table_cells": [
                        {
                            "start_row_offset_idx": 0,
                            "end_row_offset_idx": 1,
                            "start_col_offset_idx": 0,
                            "end_col_offset_idx": 1,
                            "row_span": 1,
                            "col_span": 1,
                            "text": "R1C1",
                        }
                    ],
                },
            }
        ],
        "key_value_items": [],
        "form_items": [],
        "pages": {
            "1": {
                "page_no": 1,
                "size": {"width": 100.0, "height": 200.0},
                "image": None,
            }
        },
    }


def test_projection_keeps_complete_native_value_and_emits_thin_ordered_evidence() -> None:
    """Project reviewed thin evidence without mutating or copying native subtrees."""
    native = _native_document()
    frozen = copy.deepcopy(native)

    candidates, warnings = project_native_document(native, limits=RichParserLimits())

    assert native == frozen
    assert [candidate.kind for candidate in candidates] == [
        RichEvidenceKind.HEADING,
        RichEvidenceKind.TEXT,
        RichEvidenceKind.TABLE_CELL,
        RichEvidenceKind.PICTURE,
        RichEvidenceKind.PAGE,
    ]
    assert build_text_view(native) == "Heading\nParagraph"
    assert warnings == ("unknown_text_label",)
    assert candidates[1].parent_ordinal == 0
    assert isinstance(candidates[0].anchor, OpaqueProviderPointerAnchor)
    assert isinstance(candidates[1].anchor, PageRegionAnchor)
    assert candidates[1].anchor.model_dump() == {
        "anchor_type": "page_region",
        "coordinate_system": "normalized_ppm_top_left",
        "page_number": 1,
        "x": 100_000,
        "y": 100_000,
        "width": 500_000,
        "height": 500_000,
    }
    assert isinstance(candidates[2].anchor, TableCellAnchor)
    assert candidates[2].retrieval_text == "R1C1"


def test_native_export_stringifies_only_the_exact_unsafe_provider_hash() -> None:
    """Preserve Docling's unsigned 64-bit hash exactly without admitting unsafe JSON."""
    native = _native_document()
    native["origin"] = {
        "binary_hash": 18_446_744_073_709_551_615,
        "filename": "synthetic.docx",
    }
    normalized, warnings = normalize_docling_export(native)

    assert normalized["origin"]["binary_hash"] == "18446744073709551615"  # type: ignore[index]
    assert warnings == ("provider_binary_hash_stringified",)
    with pytest.raises(InvalidRichParserOutput):
        normalize_docling_export({"unsafe_elsewhere": 18_446_744_073_709_551_615})
    with pytest.raises(InvalidRichParserOutput):
        normalize_docling_export([])

    safe, safe_warnings = normalize_docling_export(
        {"origin": {"binary_hash": 42}, "schema_name": "DoclingDocument"}
    )
    assert safe["origin"] == {"binary_hash": 42}
    assert safe_warnings == ()


@pytest.mark.parametrize(
    "provenance",
    (
        {"page_no": 0, "bbox": {"l": 0, "t": 1, "r": 1, "b": 0, "coord_origin": "TOPLEFT"}},
        {
            "page_no": 1,
            "bbox": {"l": float("nan"), "t": 1, "r": 1, "b": 0, "coord_origin": "TOPLEFT"},
        },
        {"page_no": 1, "bbox": {"l": 0, "t": 1, "r": 2, "b": 0, "coord_origin": "UNKNOWN"}},
    ),
)
def test_coordinate_conversion_rejects_invalid_or_ambiguous_values(
    provenance: dict[str, object],
) -> None:
    """Fail closed before unsafe provider coordinates become evidence."""
    with pytest.raises(InvalidRichParserOutput):
        page_region_from_provenance(
            provenance,
            pages={"1": {"page_no": 1, "size": {"width": 100.0, "height": 200.0}}},
        )


def test_top_left_coordinate_conversion_is_exact() -> None:
    """Normalize a valid top-left rectangle using deterministic fixed-point units."""
    anchor = page_region_from_provenance(
        {
            "page_no": 1,
            "bbox": {
                "l": 20,
                "t": 40,
                "r": 80,
                "b": 140,
                "coord_origin": "TOPLEFT",
            },
        },
        pages={"1": {"page_no": 1, "size": {"width": 100, "height": 200}}},
    )
    assert anchor.model_dump() == {
        "anchor_type": "page_region",
        "coordinate_system": "normalized_ppm_top_left",
        "page_number": 1,
        "x": 200_000,
        "y": 200_000,
        "width": 600_000,
        "height": 500_000,
    }


def test_projection_clamps_only_tiny_provider_bbox_rounding_with_warning() -> None:
    """Accept sub-100-ppm Office rounding without hiding the repaired provenance."""
    native = _native_document()
    native["texts"][1]["prov"][0]["bbox"]["t"] = 200.01  # type: ignore[index]

    candidates, warnings = project_native_document(native, limits=RichParserLimits())

    assert "provider_bbox_clamped" in warnings
    assert candidates[1].warning_codes == ("provider_bbox_clamped",)
    assert candidates[1].anchor.model_dump()["y"] == 0

    native["texts"][1]["prov"][0]["bbox"]["t"] = 200.1  # type: ignore[index]
    candidates, warnings = project_native_document(native, limits=RichParserLimits())
    assert "provider_bbox_clipped" in warnings
    assert candidates[1].warning_codes == ("provider_bbox_clipped",)

    native["texts"][1]["prov"][0]["bbox"] = {  # type: ignore[index]
        "l": 101,
        "t": 100,
        "r": 120,
        "b": 80,
        "coord_origin": "TOPLEFT",
    }
    candidates, warnings = project_native_document(native, limits=RichParserLimits())
    assert "provider_bbox_unusable" in warnings
    assert isinstance(candidates[1].anchor, OpaqueProviderPointerAnchor)


def test_projection_falls_back_to_pointer_for_unusable_provider_bbox() -> None:
    """Retain text and exact native provenance without inventing invalid geometry."""
    native = _native_document()
    native["texts"][1]["prov"][0]["bbox"] = {  # type: ignore[index]
        "l": 0,
        "t": 0,
        "r": 0,
        "b": 0,
        "coord_origin": "TOPLEFT",
    }

    candidates, warnings = project_native_document(native, limits=RichParserLimits())

    assert "provider_bbox_unusable" in warnings
    assert candidates[1].warning_codes == ("provider_bbox_unusable",)
    assert isinstance(candidates[1].anchor, OpaqueProviderPointerAnchor)


def test_projection_rejects_duplicate_pointer_cycle_and_resource_overflow() -> None:
    """Reject ambiguous graphs and enforce candidate/retrieval bounds."""
    duplicate = _native_document()
    duplicate["texts"][1]["self_ref"] = "#/texts/0"  # type: ignore[index]
    with pytest.raises(InvalidRichParserOutput, match="invalid"):
        project_native_document(duplicate, limits=RichParserLimits())

    cycle = _native_document()
    cycle["texts"][0]["parent"] = {"$ref": "#/texts/1"}  # type: ignore[index]
    with pytest.raises(InvalidRichParserOutput, match="invalid"):
        project_native_document(cycle, limits=RichParserLimits())

    with pytest.raises(RichParserResourceLimitExceeded, match="limit"):
        project_native_document(
            _native_document(),
            limits=RichParserLimits(max_projections=1),
        )
    with pytest.raises(RichParserResourceLimitExceeded, match="limit"):
        project_native_document(
            _native_document(),
            limits=RichParserLimits(max_retrieval_body_bytes=2),
        )
    with pytest.raises(RichParserResourceLimitExceeded, match="limit"):
        project_native_document(
            _native_document(),
            limits=RichParserLimits(
                max_retrieval_body_bytes=10,
                max_total_retrieval_bytes=10,
            ),
        )
    with pytest.raises(RichParserResourceLimitExceeded, match="limit"):
        project_native_document(
            _native_document(),
            limits=RichParserLimits(max_native_bytes=1),
        )


@pytest.mark.parametrize(
    "mutation",
    (
        "wrong_schema",
        "missing_pages",
        "non_array_texts",
        "invalid_provenance",
        "invalid_table_data",
        "invalid_table_cells",
        "invalid_table_cell",
        "invalid_table_span",
        "invalid_page",
    ),
)
def test_projection_rejects_malformed_native_shapes(mutation: str) -> None:
    """Reject malformed native nodes before any ambiguous evidence is published."""
    native = _native_document()
    if mutation == "wrong_schema":
        native["schema_name"] = "OtherDocument"
    elif mutation == "missing_pages":
        native.pop("pages")
    elif mutation == "non_array_texts":
        native["texts"] = {}
    elif mutation == "invalid_provenance":
        native["texts"][1]["prov"] = ["invalid"]  # type: ignore[index]
    elif mutation == "invalid_table_data":
        native["tables"][0]["data"] = []  # type: ignore[index]
    elif mutation == "invalid_table_cells":
        native["tables"][0]["data"]["table_cells"] = {}  # type: ignore[index]
    elif mutation == "invalid_table_cell":
        native["tables"][0]["data"]["table_cells"] = ["invalid"]  # type: ignore[index]
    elif mutation == "invalid_table_span":
        native["tables"][0]["data"]["table_cells"][0]["row_span"] = 0  # type: ignore[index]
    elif mutation == "invalid_page":
        native["pages"]["1"] = []  # type: ignore[index]

    with pytest.raises(InvalidRichParserOutput):
        project_native_document(native, limits=RichParserLimits())


def test_projection_ignores_empty_text_and_empty_table_cells_with_warnings() -> None:
    """Skip empty retrieval bodies while retaining a machine-readable text warning."""
    native = _native_document()
    native["texts"][0]["text"] = ""  # type: ignore[index]
    native["tables"][0]["data"]["table_cells"][0]["text"] = ""  # type: ignore[index]

    candidates, warnings = project_native_document(native, limits=RichParserLimits())

    assert "empty_text_ignored" in warnings
    assert all(candidate.retrieval_text not in {"", "Heading", "R1C1"} for candidate in candidates)


def test_rfc6901_resolution_is_exact_bounded_and_non_mutating() -> None:
    """Resolve only adapter-issued local JSON references."""
    native = _native_document()
    resolved = resolve_json_pointer(native, "#/tables/0/data/table_cells/0")
    assert resolved["text"] == "R1C1"  # type: ignore[index]
    resolved["text"] = "changed"  # type: ignore[index]
    assert native["tables"][0]["data"]["table_cells"][0]["text"] == "R1C1"  # type: ignore[index]

    assert resolve_json_pointer({"a/b": {"~key": 7}}, "#/a~1b/~0key") == 7
    for pointer in ("", "#", "/texts/0", "http://example.test", "#/../x", "#/a//b", "#/~2"):
        with pytest.raises(InvalidRichParserOutput):
            resolve_json_pointer(native, pointer)
    with pytest.raises(InvalidRichParserOutput, match="missing"):
        resolve_json_pointer(native, "#/texts/99")
    with pytest.raises(InvalidRichParserOutput, match="missing"):
        resolve_json_pointer(native, "#/texts/00")
    with pytest.raises(InvalidRichParserOutput, match="missing"):
        resolve_json_pointer(native, "#/texts/not-an-index")
    with pytest.raises(InvalidRichParserOutput, match="missing"):
        resolve_json_pointer(native, "#/schema_name/value")
    with pytest.raises(RichParserResourceLimitExceeded, match="limit"):
        resolve_json_pointer(native, "#/texts", max_resolved_bytes=1)
