"""Exact Docling conversion, native projection and bounded pointer resolution."""

from __future__ import annotations

import copy
import hashlib
import importlib.metadata
import math
from collections.abc import Mapping
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import cast

from pydantic import JsonValue, ValidationError

from openardp.domain.common import MAX_SAFE_INTEGER, ensure_json_value
from openardp.domain.evidence import (
    OpaqueProviderPointerAnchor,
    PageRegionAnchor,
    ProviderPointer,
    ProviderRecipe,
    TableCellAnchor,
)
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.ingestion import ParserRecipe, RichMediaType
from openardp.domain.rich_ingestion import (
    NATIVE_EXPORT_PROFILE,
    PROJECTION_PROFILE,
    ComponentVersion,
    ModelBundleManifest,
    RichEvidenceCandidate,
    RichEvidenceKind,
    RichParseOutput,
    RichParserLimits,
    RichParserRecipe,
)
from openardp.ports.parser import (
    InvalidRichParserOutput,
    ParserError,
    RichParserDependencyUnavailable,
    RichParserMalformedDocument,
    RichParserModelAssetsInvalid,
    RichParserModelAssetsRequired,
    RichParserNetworkDenied,
    RichParserPartialConversion,
    RichParserResourceLimitExceeded,
)

DOCLING_VERSION = "2.114.0"
PROVIDER_PROFILE = "openardp-docling-native"
PROVIDER_PROFILE_VERSION = "0.1.0"
_MAX_POINTER_LENGTH = 2_048
_MAX_POINTER_DEPTH = 64
_MAX_RESOLVED_BYTES = 8_388_608
_PPM_SCALE = Decimal(1_000_000)
_MAX_PROVIDER_BBOX_OVERSHOOT_PPM = Decimal(100)
_HEADING_LABELS = frozenset({"title", "section_header", "heading"})
_TEXT_LABELS = frozenset(
    {
        "text",
        "paragraph",
        "list_item",
        "caption",
        "footnote",
        "code",
        "formula",
        "page_header",
        "page_footer",
        "checkbox_selected",
        "checkbox_unselected",
        "document_index",
    }
)
_COMPONENT_DISTRIBUTIONS = (
    "docling",
    "docling-core",
    "docling-ibm-models",
    "docling-parse",
    "docling-slim",
)


def build_docling_recipe(
    *,
    limits: RichParserLimits,
    model_bundle_id: str | None = None,
) -> RichParserRecipe:
    """Build the exact aligned recipe for the reviewed offline provider profile."""
    configuration: dict[str, JsonValue] = {
        "provider": "docling",
        "provider_version": DOCLING_VERSION,
        "provider_profile": PROVIDER_PROFILE,
        "provider_profile_version": PROVIDER_PROFILE_VERSION,
        "native_export_profile": NATIVE_EXPORT_PROFILE,
        "projection_profile": PROJECTION_PROFILE,
        "supported_media": [item.value for item in RichMediaType],
        "limits": limits.model_dump(mode="json"),
        "model_bundle_id": model_bundle_id,
        "offline": {
            "allow_external_plugins": False,
            "enable_remote_services": False,
            "ocr": False,
            "picture_classification": False,
            "picture_description": False,
            "chart_extraction": False,
            "code_enrichment": False,
            "formula_enrichment": False,
        },
    }
    config_hash = canonical_sha256(configuration)
    parser = ParserRecipe(
        name="docling",
        version=DOCLING_VERSION,
        profile=PROVIDER_PROFILE,
        config_hash=config_hash,
        normalization_schema_version="0.1.0",
    )
    provider = ProviderRecipe(
        name=parser.name,
        version=parser.version,
        profile=parser.profile,
        profile_version=PROVIDER_PROFILE_VERSION,
        config_hash=config_hash,
    )
    return RichParserRecipe(
        parser=parser,
        provider=provider,
        native_export_profile=NATIVE_EXPORT_PROFILE,
        projection_profile=PROJECTION_PROFILE,
        supported_media=tuple(RichMediaType),
        limits=limits,
        model_bundle_id=model_bundle_id,
    )


def validate_model_bundle(root: Path, manifest: ModelBundleManifest) -> Path:
    """Validate every reviewed model file without following links or escaping root."""
    try:
        from openardp.adapters.docling_bundle import verify_model_asset_tree

        return verify_model_asset_tree(root.absolute(), manifest)
    except (OSError, ValueError):
        raise RichParserModelAssetsInvalid("rich parser model assets invalid") from None


def convert_docling_bytes(
    source_bytes: bytes,
    *,
    media_type: RichMediaType,
    limits: RichParserLimits,
    model_root: Path | None = None,
    model_manifest: ModelBundleManifest | None = None,
) -> RichParseOutput:
    """Convert one in-memory rich source with the exact reviewed offline profile."""
    if not isinstance(source_bytes, bytes):
        raise InvalidRichParserOutput("rich parser output invalid")
    if len(source_bytes) > limits.max_source_bytes:
        raise RichParserResourceLimitExceeded("rich parser resource limit exceeded")
    if media_type is RichMediaType.PDF:
        if model_root is None or model_manifest is None:
            raise RichParserModelAssetsRequired("rich parser model assets required")
        validated_model_root = validate_model_bundle(model_root, model_manifest)
    else:
        validated_model_root = None
        if model_root is not None or model_manifest is not None:
            raise RichParserModelAssetsInvalid("rich parser model assets invalid")

    _verify_component_version("docling", DOCLING_VERSION)
    try:
        from docling.datamodel.base_models import InputFormat
    except (ImportError, ModuleNotFoundError):
        raise RichParserDependencyUnavailable("rich parser dependency unavailable") from None

    format_by_media = {
        RichMediaType.PDF: InputFormat.PDF,
        RichMediaType.DOCX: InputFormat.DOCX,
        RichMediaType.PPTX: InputFormat.PPTX,
    }
    extension_by_media = {
        RichMediaType.PDF: "pdf",
        RichMediaType.DOCX: "docx",
        RichMediaType.PPTX: "pptx",
    }
    input_format = format_by_media[media_type]
    name = (
        f"source-{hashlib.sha256(source_bytes).hexdigest()[:16]}.{extension_by_media[media_type]}"
    )
    if media_type in {RichMediaType.DOCX, RichMediaType.PPTX}:
        try:
            from docling.backend.abstract_backend import (
                AbstractDocumentBackend,
                DeclarativeDocumentBackend,
            )
            from docling.backend.mspowerpoint_backend import (
                MsPowerpointDocumentBackend,
            )
            from docling.backend.msword_backend import MsWordDocumentBackend
            from docling.datamodel.document import InputDocument
            from docling.datamodel.settings import DocumentLimits

            backend_by_media: dict[
                RichMediaType,
                type[AbstractDocumentBackend],
            ] = {
                RichMediaType.DOCX: MsWordDocumentBackend,
                RichMediaType.PPTX: MsPowerpointDocumentBackend,
            }
            input_document = InputDocument(
                BytesIO(source_bytes),
                format=input_format,
                backend=backend_by_media[media_type],
                filename=name,
                limits=DocumentLimits(
                    max_num_pages=limits.max_pages,
                    max_file_size=limits.max_source_bytes,
                    page_range=(1, limits.max_pages),
                ),
            )
            if not input_document.valid:
                if input_document.page_count > limits.max_pages:
                    raise RichParserResourceLimitExceeded("rich parser page limit exceeded")
                raise RichParserMalformedDocument("rich parser document malformed")
            backend = cast(
                "DeclarativeDocumentBackend",
                input_document._backend,
            )
            try:
                document = backend.convert()
            finally:
                backend.unload()  # type: ignore[no-untyped-call]
        except ParserError:
            raise
        except RuntimeError as error:
            if "network access disabled" in str(error):
                raise RichParserNetworkDenied("rich parser network denied") from None
            raise RichParserMalformedDocument("rich parser document malformed") from None
        except (ImportError, ModuleNotFoundError):
            raise RichParserDependencyUnavailable("rich parser dependency unavailable") from None
        except Exception:
            raise RichParserMalformedDocument("rich parser document malformed") from None
    else:
        try:
            from docling.datamodel.accelerator_options import (
                AcceleratorDevice,
                AcceleratorOptions,
            )
            from docling.datamodel.base_models import ConversionStatus
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import (
                DocumentConverter,
                PdfFormatOption,
            )
            from docling_core.types.io import DocumentStream

            pdf_options = PdfPipelineOptions(
                accelerator_options=AcceleratorOptions(
                    num_threads=1,
                    device=AcceleratorDevice.CPU,
                ),
                enable_remote_services=False,
                allow_external_plugins=False,
                artifacts_path=validated_model_root,
                do_picture_classification=False,
                do_picture_description=False,
                do_chart_extraction=False,
                generate_page_images=False,
                generate_picture_images=False,
                do_table_structure=True,
                do_ocr=False,
                do_code_enrichment=False,
                do_formula_enrichment=False,
                generate_table_images=False,
                generate_parsed_pages=False,
                ocr_batch_size=1,
                layout_batch_size=1,
                table_batch_size=1,
                queue_max_size=4,
            )
            converter = DocumentConverter(
                allowed_formats=[input_format],
                format_options={input_format: PdfFormatOption(pipeline_options=pdf_options)},
            )
            result = converter.convert(
                DocumentStream(name=name, stream=BytesIO(source_bytes)),
                raises_on_error=False,
                max_num_pages=limits.max_pages,
                max_file_size=limits.max_source_bytes,
            )
        except RuntimeError as error:
            if "network access disabled" in str(error):
                raise RichParserNetworkDenied("rich parser network denied") from None
            raise RichParserMalformedDocument("rich parser document malformed") from None
        except (ImportError, ModuleNotFoundError):
            raise RichParserDependencyUnavailable("rich parser dependency unavailable") from None
        except Exception:
            raise RichParserMalformedDocument("rich parser document malformed") from None
        if result.status is ConversionStatus.PARTIAL_SUCCESS:
            raise RichParserPartialConversion("rich parser partial conversion")
        if result.status is not ConversionStatus.SUCCESS:
            raise RichParserMalformedDocument("rich parser document malformed")
        document = result.document

    try:
        exported = document.export_to_dict(
            mode="json",
            by_alias=True,
            exclude_none=False,
            coord_precision=None,
            confid_precision=None,
        )
        native_document, normalization_warnings = normalize_docling_export(exported)
        native_bytes = canonical_json_bytes(native_document)
    except (TypeError, ValueError, ValidationError):
        raise InvalidRichParserOutput("rich parser output invalid") from None
    if len(native_bytes) > limits.max_native_bytes:
        raise RichParserResourceLimitExceeded("rich parser native output limit exceeded")

    candidates, projection_warnings = project_native_document(
        native_document,
        limits=limits,
    )
    warnings = tuple(sorted(set(normalization_warnings) | set(projection_warnings)))
    return RichParseOutput(
        media_type=media_type,
        native_document=native_document,
        candidates=candidates,
        component_versions=_component_versions(),
        warning_codes=warnings,
    )


def normalize_docling_export(
    exported: object,
) -> tuple[dict[str, JsonValue], tuple[str, ...]]:
    """Normalize Docling's unsigned 64-bit binary hash losslessly for I-JSON/JCS."""
    if not isinstance(exported, dict):
        raise InvalidRichParserOutput("rich parser output invalid")
    normalized = copy.deepcopy(exported)
    origin = normalized.get("origin")
    warnings: tuple[str, ...] = ()
    if isinstance(origin, dict):
        binary_hash = origin.get("binary_hash")
        if type(binary_hash) is int and not -MAX_SAFE_INTEGER <= binary_hash <= MAX_SAFE_INTEGER:
            origin["binary_hash"] = str(binary_hash)
            warnings = ("provider_binary_hash_stringified",)
    try:
        ensure_json_value(normalized, path="$.native_document")
    except (TypeError, ValueError):
        raise InvalidRichParserOutput("rich parser output invalid") from None
    return cast("dict[str, JsonValue]", normalized), warnings


def _verify_component_version(distribution: str, expected: str) -> None:
    try:
        actual = importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        raise RichParserDependencyUnavailable("rich parser dependency unavailable") from None
    if actual != expected:
        raise RichParserDependencyUnavailable("rich parser dependency unavailable")


def _component_versions() -> tuple[ComponentVersion, ...]:
    versions = []
    for distribution in _COMPONENT_DISTRIBUTIONS:
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            continue
        versions.append(ComponentVersion(name=distribution, version=version))
    return tuple(sorted(versions, key=lambda item: (item.name, item.version)))


def build_text_view(native_document: dict[str, JsonValue]) -> str:
    """Return the deterministic reviewed Unicode text view."""
    texts = _array(native_document, "texts")
    values: list[str] = []
    for item in texts:
        label = item.get("label")
        text = item.get("text")
        if (
            isinstance(label, str)
            and label in _HEADING_LABELS | _TEXT_LABELS
            and isinstance(text, str)
            and text
        ):
            values.append(text)
    return "\n".join(values)


def project_native_document(
    native_document: dict[str, JsonValue],
    *,
    limits: RichParserLimits,
) -> tuple[tuple[RichEvidenceCandidate, ...], tuple[str, ...]]:
    """Project deterministic thin evidence from one complete DoclingDocument value."""
    try:
        ensure_json_value(native_document, path="$.native_document")
        if native_document.get("schema_name") != "DoclingDocument":
            raise ValueError
        pages = _object(native_document, "pages")
        node_collections = _native_node_collections(native_document)
        _validate_node_graph(node_collections)
    except (TypeError, ValueError):
        raise InvalidRichParserOutput("rich parser output invalid") from None

    candidates: list[RichEvidenceCandidate] = []
    warnings: set[str] = set()
    ordinal_by_pointer: dict[str, int] = {}

    for item in node_collections[0]:
        pointer = _node_pointer(item)
        label = item.get("label")
        text = item.get("text")
        if not isinstance(label, str) or label not in _HEADING_LABELS | _TEXT_LABELS:
            warnings.add("unknown_text_label")
            continue
        if not isinstance(text, str) or not text:
            warnings.add("empty_text_ignored")
            continue
        parent_ordinal = _parent_ordinal(item, ordinal_by_pointer)
        native_pointer = _provider_pointer(pointer)
        kind = RichEvidenceKind.HEADING if label in _HEADING_LABELS else RichEvidenceKind.TEXT
        anchor, anchor_warnings = _candidate_anchor(item, native_pointer, pages, warnings)
        candidate = RichEvidenceCandidate(
            ordinal=len(candidates),
            parent_ordinal=parent_ordinal,
            kind=kind,
            anchor=anchor,
            retrieval_media_type="text/plain",
            retrieval_text=text,
            native_pointer=native_pointer,
            warning_codes=anchor_warnings,
        )
        _append_bounded(candidates, candidate, limits)
        ordinal_by_pointer[pointer] = candidate.ordinal

    for table_index, table in enumerate(node_collections[1]):
        table_pointer_text = _node_pointer(table)
        table_pointer = _provider_pointer(table_pointer_text)
        data = table.get("data")
        if not isinstance(data, dict):
            raise InvalidRichParserOutput("rich parser output invalid")
        cells = data.get("table_cells")
        if not isinstance(cells, list):
            raise InvalidRichParserOutput("rich parser output invalid")
        ordered_cells = sorted(
            enumerate(cells),
            key=lambda pair: _cell_order(pair[1], pair[0]),
        )
        for cell_index, cell in ordered_cells:
            if not isinstance(cell, dict):
                raise InvalidRichParserOutput("rich parser output invalid")
            text = cell.get("text")
            if not isinstance(text, str) or not text:
                continue
            pointer = f"#/tables/{table_index}/data/table_cells/{cell_index}"
            native_pointer = _provider_pointer(pointer)
            try:
                row = _strict_non_negative_int(cell.get("start_row_offset_idx"))
                column = _strict_non_negative_int(cell.get("start_col_offset_idx"))
                row_span = _strict_positive_int(cell.get("row_span", 1))
                column_span = _strict_positive_int(cell.get("col_span", 1))
                cell_anchor = TableCellAnchor(
                    anchor_type="table_cell",
                    table=table_pointer,
                    row_index=row,
                    column_index=column,
                    row_span=row_span,
                    column_span=column_span,
                )
            except (TypeError, ValueError, ValidationError):
                raise InvalidRichParserOutput("rich parser output invalid") from None
            candidate = RichEvidenceCandidate(
                ordinal=len(candidates),
                kind=RichEvidenceKind.TABLE_CELL,
                anchor=cell_anchor,
                retrieval_media_type="text/plain",
                retrieval_text=text,
                native_pointer=native_pointer,
            )
            _append_bounded(candidates, candidate, limits)

    for picture_index, picture in enumerate(node_collections[2]):
        pointer = _node_pointer(picture)
        native_pointer = _provider_pointer(pointer)
        retrieval = canonical_json_bytes(
            {"kind": "picture", "pointer": f"#/pictures/{picture_index}"}
        ).decode("utf-8")
        anchor, anchor_warnings = _candidate_anchor(picture, native_pointer, pages, warnings)
        candidate = RichEvidenceCandidate(
            ordinal=len(candidates),
            parent_ordinal=_parent_ordinal(picture, ordinal_by_pointer),
            kind=RichEvidenceKind.PICTURE,
            anchor=anchor,
            retrieval_media_type="application/json",
            retrieval_text=retrieval,
            native_pointer=native_pointer,
            warning_codes=anchor_warnings,
        )
        _append_bounded(candidates, candidate, limits)
        ordinal_by_pointer[pointer] = candidate.ordinal

    for page_key, page in sorted(pages.items(), key=_page_order):
        if not isinstance(page, dict):
            raise InvalidRichParserOutput("rich parser output invalid")
        page_number = _strict_positive_int(page.get("page_no"))
        pointer_text = f"#/pages/{_escape_pointer_segment(page_key)}"
        native_pointer = _provider_pointer(pointer_text)
        retrieval = canonical_json_bytes(
            {"kind": "page", "page_number": page_number, "pointer": pointer_text}
        ).decode("utf-8")
        candidate = RichEvidenceCandidate(
            ordinal=len(candidates),
            kind=RichEvidenceKind.PAGE,
            anchor=PageRegionAnchor(
                anchor_type="page_region",
                coordinate_system="normalized_ppm_top_left",
                page_number=page_number,
                x=0,
                y=0,
                width=1_000_000,
                height=1_000_000,
            ),
            retrieval_media_type="application/json",
            retrieval_text=retrieval,
            native_pointer=native_pointer,
        )
        _append_bounded(candidates, candidate, limits)

    native_size = len(canonical_json_bytes(native_document))
    if native_size > limits.max_native_bytes:
        raise RichParserResourceLimitExceeded("rich parser native output limit exceeded")
    return tuple(candidates), tuple(sorted(warnings))


def _append_bounded(
    candidates: list[RichEvidenceCandidate],
    candidate: RichEvidenceCandidate,
    limits: RichParserLimits,
) -> None:
    if len(candidates) >= limits.max_projections:
        raise RichParserResourceLimitExceeded("rich parser projection limit exceeded")
    body_length = len(candidate.retrieval_bytes)
    if body_length > limits.max_retrieval_body_bytes:
        raise RichParserResourceLimitExceeded("rich parser retrieval limit exceeded")
    total = sum(len(item.retrieval_bytes) for item in candidates) + body_length
    if total > limits.max_total_retrieval_bytes:
        raise RichParserResourceLimitExceeded("rich parser retrieval limit exceeded")
    candidates.append(candidate)


def _validate_node_graph(collections: list[list[dict[str, JsonValue]]]) -> None:
    parent_by_pointer: dict[str, str | None] = {}
    for collection in collections:
        for item in collection:
            pointer = _node_pointer(item)
            if pointer in parent_by_pointer:
                raise ValueError("duplicate node pointer")
            parent_by_pointer[pointer] = _parent_pointer(item)
    for pointer in parent_by_pointer:
        seen: set[str] = set()
        current: str | None = pointer
        while current is not None and current in parent_by_pointer:
            if current in seen:
                raise ValueError("native node graph contains a cycle")
            seen.add(current)
            current = parent_by_pointer[current]


def _node_pointer(item: dict[str, JsonValue]) -> str:
    value = item.get("self_ref")
    if not isinstance(value, str):
        raise ValueError("native node lacks pointer")
    _pointer_segments(value)
    return value


def _parent_pointer(item: dict[str, JsonValue]) -> str | None:
    parent = item.get("parent")
    if parent is None:
        return None
    if not isinstance(parent, dict):
        raise ValueError("native parent is invalid")
    value = parent.get("$ref")
    if not isinstance(value, str):
        raise ValueError("native parent pointer is invalid")
    _pointer_segments(value)
    return value


def _parent_ordinal(
    item: dict[str, JsonValue],
    ordinal_by_pointer: dict[str, int],
) -> int | None:
    pointer = _parent_pointer(item)
    return ordinal_by_pointer.get(pointer) if pointer is not None else None


def _anchor_for_item(
    item: dict[str, JsonValue],
    pointer: ProviderPointer,
    pages: dict[str, JsonValue],
) -> tuple[OpaqueProviderPointerAnchor | PageRegionAnchor, tuple[str, ...]]:
    provenance = item.get("prov")
    if isinstance(provenance, list) and provenance:
        first = provenance[0]
        if not isinstance(first, dict):
            raise InvalidRichParserOutput("rich parser output invalid")
        try:
            anchor, repair_warning = _page_region_and_clamped(first, pages=pages)
        except InvalidRichParserOutput:
            return (
                OpaqueProviderPointerAnchor(anchor_type="provider_pointer", target=pointer),
                ("provider_bbox_unusable",),
            )
        warnings = (repair_warning,) if repair_warning is not None else ()
        return anchor, warnings
    return OpaqueProviderPointerAnchor(anchor_type="provider_pointer", target=pointer), ()


def _candidate_anchor(
    item: dict[str, JsonValue],
    pointer: ProviderPointer,
    pages: dict[str, JsonValue],
    warnings: set[str],
) -> tuple[OpaqueProviderPointerAnchor | PageRegionAnchor, tuple[str, ...]]:
    """Resolve one candidate anchor and retain any bounded repair warning."""
    anchor, anchor_warnings = _anchor_for_item(item, pointer, pages)
    warnings.update(anchor_warnings)
    return anchor, anchor_warnings


def page_region_from_provenance(
    provenance: Mapping[str, object],
    *,
    pages: Mapping[str, object],
) -> PageRegionAnchor:
    """Convert one finite Docling rectangle to fixed-point top-left coordinates."""
    anchor, _repair_warning = _page_region_and_clamped(provenance, pages=pages)
    return anchor


def _page_region_and_clamped(
    provenance: Mapping[str, object],
    *,
    pages: Mapping[str, object],
) -> tuple[PageRegionAnchor, str | None]:
    """Normalize one rectangle and report bounded provider rounding repair."""
    try:
        page_number = _strict_positive_int(provenance.get("page_no"))
        page = pages[str(page_number)]
        if not isinstance(page, dict):
            raise ValueError
        size = page.get("size")
        bbox = provenance.get("bbox")
        if not isinstance(size, dict) or not isinstance(bbox, dict):
            raise ValueError
        page_width = _positive_decimal(size.get("width"))
        page_height = _positive_decimal(size.get("height"))
        left = _finite_decimal(bbox.get("l"))
        top = _finite_decimal(bbox.get("t"))
        right = _finite_decimal(bbox.get("r"))
        bottom = _finite_decimal(bbox.get("b"))
        origin = bbox.get("coord_origin")
        if origin == "BOTTOMLEFT":
            x = left
            y = page_height - top
            width = right - left
            height = top - bottom
        elif origin == "TOPLEFT":
            x = left
            y = top
            width = right - left
            height = bottom - top
        else:
            raise ValueError
        if width <= 0 or height <= 0:
            raise ValueError
        x_end = x + width
        y_end = y + height
        x_tolerance = page_width * _MAX_PROVIDER_BBOX_OVERSHOOT_PPM / _PPM_SCALE
        y_tolerance = page_height * _MAX_PROVIDER_BBOX_OVERSHOOT_PPM / _PPM_SCALE
        if x >= page_width or y >= page_height or x_end <= 0 or y_end <= 0:
            raise ValueError
        bounded_x = min(max(x, Decimal(0)), page_width)
        bounded_y = min(max(y, Decimal(0)), page_height)
        bounded_x_end = min(max(x_end, Decimal(0)), page_width)
        bounded_y_end = min(max(y_end, Decimal(0)), page_height)
        if bounded_x_end <= bounded_x or bounded_y_end <= bounded_y:
            raise ValueError
        x_ppm = _normalized_ppm(bounded_x, page_width)
        y_ppm = _normalized_ppm(bounded_y, page_height)
        x_end_ppm = _normalized_ppm(bounded_x_end, page_width)
        y_end_ppm = _normalized_ppm(bounded_y_end, page_height)
        anchor = PageRegionAnchor(
            anchor_type="page_region",
            coordinate_system="normalized_ppm_top_left",
            page_number=page_number,
            x=x_ppm,
            y=y_ppm,
            width=x_end_ppm - x_ppm,
            height=y_end_ppm - y_ppm,
        )
        changed = (bounded_x, bounded_y, bounded_x_end, bounded_y_end) != (
            x,
            y,
            x_end,
            y_end,
        )
        if not changed:
            return anchor, None
        tiny_rounding = (
            x >= -x_tolerance
            and y >= -y_tolerance
            and x_end <= page_width + x_tolerance
            and y_end <= page_height + y_tolerance
        )
        return anchor, "provider_bbox_clamped" if tiny_rounding else "provider_bbox_clipped"
    except (KeyError, TypeError, ValueError, InvalidOperation, ValidationError):
        raise InvalidRichParserOutput("rich parser output invalid") from None


def _normalized_ppm(value: Decimal, extent: Decimal) -> int:
    return int(((value / extent) * _PPM_SCALE).to_integral_value(rounding=ROUND_HALF_EVEN))


def _finite_decimal(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError
    decimal = Decimal(str(value))
    if not decimal.is_finite():
        raise ValueError
    return decimal


def _positive_decimal(value: object) -> Decimal:
    decimal = _finite_decimal(value)
    if decimal <= 0:
        raise ValueError
    return decimal


def _strict_non_negative_int(value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError
    return value


def _strict_positive_int(value: object) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError
    return value


def _cell_order(value: JsonValue, fallback: int) -> tuple[int, int, int]:
    if not isinstance(value, dict):
        raise InvalidRichParserOutput("rich parser output invalid")
    return (
        _strict_non_negative_int(value.get("start_row_offset_idx")),
        _strict_non_negative_int(value.get("start_col_offset_idx")),
        fallback,
    )


def _page_order(item: tuple[str, JsonValue]) -> tuple[int, str]:
    key, page = item
    if not isinstance(page, dict):
        raise InvalidRichParserOutput("rich parser output invalid")
    return _strict_positive_int(page.get("page_no")), key


def _array(document: dict[str, JsonValue], key: str) -> list[dict[str, JsonValue]]:
    value = document.get(key)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError(f"{key} must be an array of objects")
    return cast("list[dict[str, JsonValue]]", value)


def _native_node_collections(
    document: dict[str, JsonValue],
) -> list[list[dict[str, JsonValue]]]:
    """Return the three ordered native collections projected as evidence."""
    return [_array(document, key) for key in ("texts", "tables", "pictures")]


def _object(document: dict[str, JsonValue], key: str) -> dict[str, JsonValue]:
    value = document.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value


def _provider_pointer(pointer: str) -> ProviderPointer:
    return ProviderPointer(
        provider_profile=PROVIDER_PROFILE,
        provider_profile_version=PROVIDER_PROFILE_VERSION,
        pointer_format="rfc6901-json-pointer",
        pointer=pointer,
    )


def _escape_pointer_segment(segment: str) -> str:
    return segment.replace("~", "~0").replace("/", "~1")


def _pointer_segments(pointer: str) -> tuple[str, ...]:
    if (
        not isinstance(pointer, str)
        or len(pointer) > _MAX_POINTER_LENGTH
        or not pointer.startswith("#/")
    ):
        raise ValueError("pointer grammar invalid")
    raw_segments = pointer[2:].split("/")
    if (
        not raw_segments
        or len(raw_segments) > _MAX_POINTER_DEPTH
        or any(not segment for segment in raw_segments)
    ):
        raise ValueError("pointer grammar invalid")
    segments = []
    for raw in raw_segments:
        index = 0
        decoded = []
        while index < len(raw):
            character = raw[index]
            if character == "~":
                if index + 1 >= len(raw) or raw[index + 1] not in {"0", "1"}:
                    raise ValueError("pointer escape invalid")
                decoded.append("~" if raw[index + 1] == "0" else "/")
                index += 2
                continue
            if ord(character) < 32 or ord(character) == 127:
                raise ValueError("pointer control invalid")
            decoded.append(character)
            index += 1
        segment = "".join(decoded)
        if segment in {".", ".."}:
            raise ValueError("pointer path token invalid")
        segments.append(segment)
    return tuple(segments)


def resolve_json_pointer(
    native_document: dict[str, JsonValue],
    pointer: str,
    *,
    max_resolved_bytes: int = _MAX_RESOLVED_BYTES,
) -> JsonValue:
    """Resolve and copy one bounded adapter-issued RFC 6901 local reference."""
    try:
        segments = _pointer_segments(pointer)
        current: JsonValue = native_document
        for segment in segments:
            if isinstance(current, dict):
                if segment not in current:
                    raise KeyError
                current = current[segment]
            elif isinstance(current, list):
                if not segment.isascii() or not segment.isdigit():
                    raise KeyError
                if len(segment) > 1 and segment.startswith("0"):
                    raise KeyError
                index = int(segment)
                current = current[index]
            else:
                raise KeyError
        ensure_json_value(current, path="$.resolved")
        if len(canonical_json_bytes(current)) > max_resolved_bytes:
            raise RichParserResourceLimitExceeded("rich parser retrieval limit exceeded")
        return copy.deepcopy(current)
    except RichParserResourceLimitExceeded:
        raise
    except (IndexError, KeyError):
        raise InvalidRichParserOutput("rich parser pointer missing") from None
    except (TypeError, ValueError):
        raise InvalidRichParserOutput("rich parser pointer invalid") from None


__all__ = [
    "DOCLING_VERSION",
    "PROVIDER_PROFILE",
    "PROVIDER_PROFILE_VERSION",
    "build_docling_recipe",
    "build_text_view",
    "convert_docling_bytes",
    "normalize_docling_export",
    "page_region_from_provenance",
    "project_native_document",
    "resolve_json_pointer",
    "validate_model_bundle",
]
