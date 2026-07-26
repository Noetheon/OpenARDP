"""Security boundary tests for F007 model bundles and rich values."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from openardp.adapters.docling_native import (
    convert_docling_bytes,
    validate_model_bundle,
)
from openardp.domain.rich_ingestion import (
    ModelBundleFile,
    ModelBundleManifest,
    RichMediaType,
    RichParseOutput,
    RichParserLimits,
)
from openardp.ports.parser import (
    InvalidRichParserOutput,
    RichParserDependencyUnavailable,
    RichParserModelAssetsInvalid,
    RichParserModelAssetsRequired,
    RichParserResourceLimitExceeded,
)


def _manifest_for(path: str, payload: bytes) -> ModelBundleManifest:
    return ModelBundleManifest(
        bundle_name="reviewed",
        bundle_version="1",
        files=(
            ModelBundleFile(
                path=path,
                sha256="sha256:" + hashlib.sha256(payload).hexdigest(),
                byte_length=len(payload),
                license_id="Apache-2.0",
            ),
        ),
    )


@pytest.mark.parametrize(
    "path",
    (
        "/absolute/model.bin",
        "../escape.bin",
        "models/../escape.bin",
        "models\\escape.bin",
        "./model.bin",
        "models//model.bin",
        "models/\x00model.bin",
    ),
)
def test_model_bundle_paths_are_relative_posix_and_traversal_free(path: str) -> None:
    """Reject local authority expansion before any model-file access."""
    with pytest.raises(ValidationError, match="path"):
        ModelBundleFile(
            path=path,
            sha256="sha256:" + "a" * 64,
            byte_length=1,
            license_id="Apache-2.0",
        )


def test_model_manifest_rejects_duplicate_paths_and_unsafe_license_values() -> None:
    """Require one reviewable identity and license fact per relative model path."""
    file = ModelBundleFile(
        path="models/model.bin",
        sha256="sha256:" + "a" * 64,
        byte_length=1,
        license_id="Apache-2.0",
    )
    with pytest.raises(ValidationError, match="unique"):
        ModelBundleManifest(
            schema_version="0.1.0",
            bundle_name="bundle",
            bundle_version="1",
            files=(file, file),
        )
    with pytest.raises(ValidationError):
        ModelBundleFile(
            path="models/model.bin",
            sha256="sha256:" + "a" * 64,
            byte_length=1,
            license_id="secret\nbody",
        )


@pytest.mark.parametrize("value", (math.nan, math.inf, -math.inf, 9_007_199_254_740_992))
def test_native_document_rejects_non_interoperable_json(value: float | int) -> None:
    """Keep provider output inside the strict I-JSON/JCS boundary."""
    with pytest.raises((ValidationError, ValueError)):
        RichParseOutput(
            media_type=RichMediaType.DOCX,
            native_document={"unsafe": value},
            candidates=(),
            component_versions=(),
        )


def test_model_bundle_validation_is_streamed_exact_and_symlink_safe(
    tmp_path: Path,
) -> None:
    """Accept exact regular files and reject every path or content substitution."""
    payload = b"reviewed model bytes"
    model = tmp_path / "models" / "model.bin"
    model.parent.mkdir()
    model.write_bytes(payload)
    manifest = _manifest_for("models/model.bin", payload)

    assert validate_model_bundle(tmp_path, manifest) == tmp_path

    model.write_bytes(payload + b"x")
    with pytest.raises(RichParserModelAssetsInvalid):
        validate_model_bundle(tmp_path, manifest)

    model.write_bytes(b"x" * len(payload))
    with pytest.raises(RichParserModelAssetsInvalid):
        validate_model_bundle(tmp_path, manifest)

    model.unlink()
    target = tmp_path / "target.bin"
    target.write_bytes(payload)
    model.symlink_to(target)
    with pytest.raises(RichParserModelAssetsInvalid):
        validate_model_bundle(tmp_path, manifest)


def test_model_bundle_validation_rejects_missing_and_non_directory_roots(
    tmp_path: Path,
) -> None:
    """Reject absent and regular-file roots before inspecting manifest paths."""
    manifest = ModelBundleManifest(
        bundle_name="empty",
        bundle_version="1",
        files=(),
    )
    with pytest.raises(RichParserModelAssetsInvalid):
        validate_model_bundle(tmp_path / "missing", manifest)

    regular_file = tmp_path / "regular"
    regular_file.write_bytes(b"x")
    with pytest.raises(RichParserModelAssetsInvalid):
        validate_model_bundle(regular_file, manifest)


def test_conversion_guards_fail_before_provider_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Classify invalid input, bounds, assets and versions without provider work."""
    limits = RichParserLimits(max_source_bytes=1)
    with pytest.raises(InvalidRichParserOutput):
        convert_docling_bytes(  # type: ignore[arg-type]
            "not bytes",
            media_type=RichMediaType.DOCX,
            limits=limits,
        )
    with pytest.raises(RichParserResourceLimitExceeded):
        convert_docling_bytes(
            b"xx",
            media_type=RichMediaType.DOCX,
            limits=limits,
        )
    with pytest.raises(RichParserModelAssetsRequired):
        convert_docling_bytes(
            b"x",
            media_type=RichMediaType.PDF,
            limits=limits,
        )
    with pytest.raises(RichParserModelAssetsInvalid):
        convert_docling_bytes(
            b"x",
            media_type=RichMediaType.DOCX,
            limits=limits,
            model_root=tmp_path,
        )

    monkeypatch.setattr(
        "openardp.adapters.docling_native.importlib.metadata.version",
        lambda _distribution: "0.0.0",
    )
    with pytest.raises(RichParserDependencyUnavailable):
        convert_docling_bytes(
            b"x",
            media_type=RichMediaType.DOCX,
            limits=limits,
        )
