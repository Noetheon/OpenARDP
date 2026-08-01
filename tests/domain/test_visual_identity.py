"""Golden and fresh-process tests for F011 persisted identity domains."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from openardp.domain.identity import visual_evidence_id, visual_raster_id

ROOT = Path(__file__).parents[2]
VECTORS = ROOT / "tests" / "fixtures" / "visual" / "identity" / "identity-vectors.json"


def _vectors() -> dict[str, object]:
    return json.loads(VECTORS.read_text(encoding="utf-8"))


def _identities(vectors: dict[str, object]) -> tuple[str, str]:
    recipe = vectors["recipe"]
    target = vectors["target_anchor"]
    resolved = vectors["resolved_region"]
    transform = vectors["transform"]
    usage = vectors["usage_policy"]
    assert isinstance(recipe, dict)
    assert isinstance(target, dict)
    assert isinstance(resolved, dict)
    assert isinstance(transform, dict)
    assert isinstance(usage, dict)
    raster = visual_raster_id(
        source_version_id=str(vectors["source_version_id"]),
        representation_id=str(vectors["representation_id"]),
        native_representation_id=str(vectors["native_representation_id"]),
        page_number=int(str(vectors["page_number"])),
        recipe=recipe,  # type: ignore[arg-type]
    )
    visual = visual_evidence_id(
        source_version_id=str(vectors["source_version_id"]),
        representation_id=str(vectors["representation_id"]),
        native_representation_id=str(vectors["native_representation_id"]),
        evidence_reference_id=str(vectors["evidence_reference_id"]),
        evidence_projection_id=str(vectors["evidence_projection_id"]),
        target_anchor=target,  # type: ignore[arg-type]
        resolved_region=resolved,  # type: ignore[arg-type]
        raster_id=raster,
        transform=transform,  # type: ignore[arg-type]
        crop_object_id=str(vectors["crop_object_id"]),
        crop_media_type=str(vectors["crop_media_type"]),
        recipe=recipe,  # type: ignore[arg-type]
        usage_policy=usage,  # type: ignore[arg-type]
    )
    return raster, visual


def test_visual_identities_match_reviewed_vectors() -> None:
    """Pin the two ADR-0012 identity envelopes to reviewed values."""
    vectors = _vectors()
    assert _identities(vectors) == (
        vectors["raster_id"],
        vectors["visual_evidence_id"],
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ({"source_version_id": "invalid"}, "source_version_id"),
        ({"page_number": 0}, "page_number"),
        ({"crop_object_id": "bad"}, "crop_object_id"),
    ),
)
def test_visual_identity_helpers_reject_malformed_inputs(
    mutation: dict[str, object],
    message: str,
) -> None:
    """Reject malformed identity fields rather than coercing or omitting them."""
    vectors = {**_vectors(), **mutation}
    with pytest.raises(ValueError, match=message):
        _identities(vectors)


def test_visual_identities_are_stable_across_fresh_processes() -> None:
    """Reproduce both vectors twenty times under varied hash seeds."""
    code = """
import json
import sys
from pathlib import Path
from openardp.domain.identity import visual_evidence_id, visual_raster_id
v = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
r = visual_raster_id(
    source_version_id=v['source_version_id'],
    representation_id=v['representation_id'],
    native_representation_id=v['native_representation_id'],
    page_number=v['page_number'],
    recipe=v['recipe'],
)
e = visual_evidence_id(
    source_version_id=v['source_version_id'],
    representation_id=v['representation_id'],
    native_representation_id=v['native_representation_id'],
    evidence_reference_id=v['evidence_reference_id'],
    evidence_projection_id=v['evidence_projection_id'],
    target_anchor=v['target_anchor'],
    resolved_region=v['resolved_region'],
    raster_id=r,
    transform=v['transform'],
    crop_object_id=v['crop_object_id'],
    crop_media_type=v['crop_media_type'],
    recipe=v['recipe'],
    usage_policy=v['usage_policy'],
)
print(json.dumps([r, e]))
"""
    expected = list(_identities(_vectors()))
    for seed in range(20):
        completed = subprocess.run(  # noqa: S603 - fixed interpreter and test-owned code
            [sys.executable, "-c", code, str(VECTORS)],
            check=True,
            capture_output=True,
            env={**os.environ, "PYTHONHASHSEED": str(seed)},
            text=True,
        )
        assert json.loads(completed.stdout) == expected
