"""Synthetic rich parent and deterministic fake renderer for F011 service tests."""

from __future__ import annotations

import hashlib
import io
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from threading import Lock
from uuid import UUID

from PIL import Image, ImageDraw

from openardp.adapters.docling_native import build_docling_recipe
from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.visual_pdfium import PdfiumVisualRenderer, canonical_visual_recipe
from openardp.domain.common import ParserDescriptor
from openardp.domain.evidence import PageRegionAnchor, ProviderPointer
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.ingestion import (
    IngestionDisposition,
    ReadyRepresentationCommit,
    RepresentationAcquireDisposition,
    RepresentationScope,
)
from openardp.domain.manifest import (
    DocumentManifest,
    ManifestState,
    SchemaVersions,
    SourceDescriptor,
)
from openardp.domain.rich_ingestion import (
    ComponentVersion,
    ReadyRichRepresentationCommit,
    RichAttemptOutcome,
    RichEvidenceCandidate,
    RichEvidenceKind,
    RichMediaType,
    RichParseOutput,
    RichParserLimits,
)
from openardp.domain.storage import SourceKey, SourceVersionCommit, StoredObject
from openardp.domain.visual import VisualRenderRecipe
from openardp.ports.visual import RenderedVisualCrop, RenderedVisualPage, VisualCancelled
from openardp.services.rich_ingestion import prepare_rich_attempt
from tests.integration.test_rich_catalog import (
    ATTEMPT_A,
    FENCING_CAPABILITY,
    NOW,
    _setup,
)

HEAD_FENCING_CAPABILITY = "visual-head-capability-000000000001"


class CountingVisualRenderer:
    """Deterministic in-process renderer for orchestration/caching tests."""

    def __init__(self, recipe: VisualRenderRecipe | None = None) -> None:
        """Initialize canonical recipe and thread-safe invocation counters."""
        self._recipe = recipe or canonical_visual_recipe()
        self._lock = Lock()
        self.render_count = 0
        self.crop_count = 0

    @property
    def recipe(self):
        """Return the exact canonical visual recipe."""
        return self._recipe

    def supports(self, media_type: str) -> bool:
        """Accept the synthetic DOCX parent used by these provider-free tests."""
        return media_type == RichMediaType.DOCX.value

    def render_page(
        self,
        source: bytes,
        *,
        media_type: str,
        page_number: int,
        cancellation_check: Callable[[], bool] | None = None,
    ) -> RenderedVisualPage:
        """Return a stable 200 by 400 RGB page."""
        if cancellation_check is not None and cancellation_check():
            raise VisualCancelled("visual operation cancelled")
        assert source == b"synthetic rich source"
        assert media_type == RichMediaType.DOCX.value
        assert page_number == 1
        with self._lock:
            self.render_count += 1
        image = Image.new("RGB", (200, 400), (255, 255, 255))
        ImageDraw.Draw(image).rectangle((20, 40, 179, 319), fill=(12, 34, 56))
        target = io.BytesIO()
        image.save(target, format="PNG", optimize=False, compress_level=9)
        return RenderedVisualPage(
            png_bytes=target.getvalue(),
            page_count=1,
            source_width_mpt=100_000,
            source_height_mpt=200_000,
            source_rotation=0,
            applied_rotation=0,
            pixel_width=200,
            pixel_height=400,
        )

    def crop_page(
        self,
        page_png: bytes,
        *,
        bounds: tuple[int, int, int, int],
        cancellation_check: Callable[[], bool] | None = None,
    ) -> RenderedVisualCrop:
        """Delegate exact crop canonicalization while counting calls."""
        if cancellation_check is not None and cancellation_check():
            raise VisualCancelled("visual operation cancelled")
        with self._lock:
            self.crop_count += 1
        return PdfiumVisualRenderer(recipe=self._recipe).crop_page(
            page_png,
            bounds=bounds,
            cancellation_check=cancellation_check,
        )


def _anchor(*, x: int, y: int) -> PageRegionAnchor:
    return PageRegionAnchor(
        anchor_type="page_region",
        coordinate_system="normalized_ppm_top_left",
        page_number=1,
        x=x,
        y=y,
        width=200_000,
        height=200_000,
    )


def prepared_visual_service(tmp_path: Path):
    """Return catalog/store plus two accepted exact page-region projections."""
    catalog, store, base, _ = _setup(tmp_path)
    recipe = build_docling_recipe(limits=RichParserLimits(timeout_seconds=30.0))
    candidates = []
    texts = []
    for ordinal, (x, y) in enumerate(((100_000, 100_000), (500_000, 500_000))):
        pointer = ProviderPointer(
            provider_profile=recipe.provider.profile,
            provider_profile_version=recipe.provider.profile_version,
            pointer_format="rfc6901-json-pointer",
            pointer=f"#/texts/{ordinal}",
        )
        texts.append({"self_ref": pointer.pointer, "text": f"region {ordinal}"})
        candidates.append(
            RichEvidenceCandidate(
                ordinal=ordinal,
                kind=RichEvidenceKind.PICTURE,
                anchor=_anchor(x=x, y=y),
                retrieval_media_type="application/json",
                retrieval_text=f'{{"region":{ordinal}}}',
                native_pointer=pointer,
            )
        )
    output = RichParseOutput(
        media_type=RichMediaType.DOCX,
        native_document={
            "schema_name": "DoclingDocument",
            "pages": {"1": {"page_no": 1, "size": {"width": 100, "height": 200}}},
            "texts": texts,
        },
        candidates=tuple(candidates),
        component_versions=(ComponentVersion(name="docling", version="2.114.0"),),
    )
    acquired = catalog.acquire_representation(
        base.scope,
        base.recipe,
        owner_id="rich-worker",
        lease_token=FENCING_CAPABILITY,
        now=NOW,
        lease_until=NOW + timedelta(minutes=5),
    )
    assert acquired.disposition is RepresentationAcquireDisposition.CLAIMED
    rich = prepare_rich_attempt(
        scope=base.scope,
        recipe=recipe,
        output=output,
        object_store=store,
        attempt_id=ATTEMPT_A,
        outcome=RichAttemptOutcome.CANONICAL,
        created_at=NOW + timedelta(seconds=1),
    )
    result = catalog.commit_ready_rich_representation(
        ReadyRichRepresentationCommit(base=base, rich=rich),
        owner_id="rich-worker",
        lease_token=FENCING_CAPABILITY,
        expected_revision=acquired.representation.revision,
        disposition=IngestionDisposition.COMMITTED,
    )
    return catalog, store, result.artifacts


def prepared_pdf_visual_service(tmp_path: Path):
    """Return a real synthetic PDF source with one accepted page-region projection."""
    source_bytes = (Path(__file__).parents[1] / "fixtures/rich/synthetic.pdf").read_bytes()
    store = FilesystemObjectStore(tmp_path / "cas")
    source = store.put_chunks((source_bytes,))
    recipe = build_docling_recipe(limits=RichParserLimits(timeout_seconds=30.0))
    scope = RepresentationScope(
        document_id=_pdf_document_id(),
        version_id=source.object_id,
        representation_id=recipe.parser.representation_id_for(source.object_id),
    )
    catalog = SQLiteCatalog(tmp_path / "catalog.sqlite3")
    catalog.initialize(now=NOW)
    catalog.register_document(
        SourceKey(connector="local", locator="/synthetic/source.pdf"),
        document_id=scope.document_id,
        now=NOW,
    )
    catalog.commit_source_version(
        SourceVersionCommit(
            document_id=scope.document_id,
            version_id=source.object_id,
            source=source,
            media_type=RichMediaType.PDF.value,
            committed_at=NOW,
        )
    )
    manifest = DocumentManifest(
        spec_version="0.1.0",
        document_id=scope.document_id,
        version_id=source.object_id,
        representation_id=scope.representation_id,
        title="source.pdf",
        state=ManifestState.READY,
        created_at=NOW,
        source=SourceDescriptor(
            connector="local",
            locator="/synthetic/source.pdf",
            media_type=RichMediaType.PDF.value,
            byte_length=source.byte_length,
            sha256=source.object_id.removeprefix("sha256:"),
        ),
        parser=ParserDescriptor(
            name=recipe.parser.name,
            version=recipe.parser.version,
            profile=recipe.parser.profile,
            config_hash=recipe.parser.config_hash,
        ),
        schema_versions=SchemaVersions(
            block=recipe.parser.normalization_schema_version,
            derivation="0.1.0",
            relation="0.1.0",
        ),
    )
    manifest_payload = canonical_json_bytes(manifest.model_dump(mode="json"))
    manifest_object = StoredObject(
        object_id="sha256:" + hashlib.sha256(manifest_payload).hexdigest(),
        byte_length=len(manifest_payload),
    )
    assert store.put_chunks((manifest_payload,)) == manifest_object
    base = ReadyRepresentationCommit(
        scope=scope,
        recipe=recipe.parser,
        manifest=manifest,
        manifest_object=manifest_object,
        native_object=source,
        blocks=(),
        warning_codes=(),
        source_observed_at=NOW,
        ready_at=NOW + timedelta(seconds=1),
    )
    pointer = ProviderPointer(
        provider_profile=recipe.provider.profile,
        provider_profile_version=recipe.provider.profile_version,
        pointer_format="rfc6901-json-pointer",
        pointer="#/pictures/0",
    )
    output = RichParseOutput(
        media_type=RichMediaType.PDF,
        native_document={
            "schema_name": "DoclingDocument",
            "pages": {"1": {"page_no": 1, "size": {"width": 612, "height": 792}}},
            "pictures": [{"self_ref": pointer.pointer}],
        },
        candidates=(
            RichEvidenceCandidate(
                ordinal=0,
                kind=RichEvidenceKind.PICTURE,
                anchor=_anchor(x=100_000, y=100_000),
                retrieval_media_type="application/json",
                retrieval_text='{"region":0}',
                native_pointer=pointer,
            ),
        ),
        component_versions=(ComponentVersion(name="docling", version="2.114.0"),),
    )
    acquired = catalog.acquire_representation(
        base.scope,
        base.recipe,
        owner_id="rich-worker",
        lease_token=FENCING_CAPABILITY,
        now=NOW,
        lease_until=NOW + timedelta(minutes=5),
    )
    assert acquired.disposition is RepresentationAcquireDisposition.CLAIMED
    rich = prepare_rich_attempt(
        scope=base.scope,
        recipe=recipe,
        output=output,
        object_store=store,
        attempt_id=ATTEMPT_A,
        outcome=RichAttemptOutcome.CANONICAL,
        created_at=NOW + timedelta(seconds=1),
    )
    result = catalog.commit_ready_rich_representation(
        ReadyRichRepresentationCommit(base=base, rich=rich),
        owner_id="rich-worker",
        lease_token=FENCING_CAPABILITY,
        expected_revision=acquired.representation.revision,
        disposition=IngestionDisposition.COMMITTED,
    )
    return catalog, store, result.artifacts


def _pdf_document_id() -> UUID:
    """Return one stable UUID without coupling the fixture to production identity logic."""
    return UUID("018f1000-0000-7000-8000-000000000099")


def advance_visual_document_head(catalog, store, rich):
    """Commit a newer READY base representation for visual freshness tests."""
    source = store.put_chunks((b"synthetic rich source version two",))
    recipe = build_docling_recipe(limits=RichParserLimits(timeout_seconds=30.0))
    scope = RepresentationScope(
        document_id=rich.bundle.scope.document_id,
        version_id=source.object_id,
        representation_id=recipe.parser.representation_id_for(source.object_id),
    )
    catalog.commit_source_version(
        SourceVersionCommit(
            document_id=scope.document_id,
            version_id=source.object_id,
            source=source,
            media_type=RichMediaType.DOCX.value,
            committed_at=NOW + timedelta(minutes=1),
        )
    )
    manifest = DocumentManifest(
        spec_version="0.1.0",
        document_id=scope.document_id,
        version_id=source.object_id,
        representation_id=scope.representation_id,
        title="source-v2.docx",
        state=ManifestState.READY,
        created_at=NOW + timedelta(minutes=1),
        source=SourceDescriptor(
            connector="local",
            locator="/synthetic/source.docx",
            media_type=RichMediaType.DOCX.value,
            byte_length=source.byte_length,
            sha256=source.object_id.removeprefix("sha256:"),
        ),
        parser=ParserDescriptor(
            name=recipe.parser.name,
            version=recipe.parser.version,
            profile=recipe.parser.profile,
            config_hash=recipe.parser.config_hash,
        ),
        schema_versions=SchemaVersions(
            block=recipe.parser.normalization_schema_version,
            derivation="0.1.0",
            relation="0.1.0",
        ),
    )
    payload = canonical_json_bytes(manifest.model_dump(mode="json"))
    manifest_object = store.put_chunks((payload,))
    base = ReadyRepresentationCommit(
        scope=scope,
        recipe=recipe.parser,
        manifest=manifest,
        manifest_object=manifest_object,
        native_object=source,
        blocks=(),
        warning_codes=(),
        source_observed_at=NOW + timedelta(minutes=1),
        ready_at=NOW + timedelta(minutes=1, seconds=1),
    )
    acquired = catalog.acquire_representation(
        scope,
        recipe.parser,
        owner_id="head-worker",
        lease_token=HEAD_FENCING_CAPABILITY,
        now=NOW + timedelta(minutes=1),
        lease_until=NOW + timedelta(minutes=6),
    )
    return catalog.commit_ready_representation(
        base,
        owner_id="head-worker",
        lease_token=HEAD_FENCING_CAPABILITY,
        expected_revision=acquired.representation.revision,
        disposition=IngestionDisposition.COMMITTED,
    )
