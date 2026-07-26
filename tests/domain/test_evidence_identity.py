"""Golden behavior for F006 purpose-specific identities."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from openardp.domain.identity import (
    evidence_projection_id,
    evidence_reference_id,
    native_representation_id,
)

SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
ROOT = Path(__file__).parents[2]


def test_evidence_identity_domains_are_deterministic_and_distinct() -> None:
    """Keep insertion order irrelevant and purpose domains distinct."""
    native = native_representation_id(
        source_version_id=SHA_A,
        native_artifact_id=SHA_B,
        native_artifact_media_type="application/json",
        provider_name="synthetic",
        provider_version="1.0.0",
        provider_profile="default",
        provider_profile_version="0.1.0",
        provider_config_hash=SHA_C,
    )
    anchor_a = {
        "anchor_type": "text_span",
        "coordinate_system": "unicode_code_points",
        "start": 0,
        "end": 4,
        "text_length": 4,
    }
    anchor_b = {
        "text_length": 4,
        "end": 4,
        "start": 0,
        "coordinate_system": "unicode_code_points",
        "anchor_type": "text_span",
    }
    reference_a = evidence_reference_id(
        source_version_id=SHA_A,
        native_representation_id=native,
        anchor=anchor_a,
    )
    reference_b = evidence_reference_id(
        source_version_id=SHA_A,
        native_representation_id=native,
        anchor=anchor_b,
    )
    projection = evidence_projection_id(
        source_version_id=SHA_A,
        native_representation_id=native,
        evidence_reference_id=reference_a,
        retrieval_artifact_id=SHA_B,
        retrieval_media_type="text/plain",
        parent_projection_id=None,
        ordinal=0,
        generator_name="synthetic",
        generator_version="1.0.0",
        generator_config_hash=SHA_C,
    )
    assert reference_a == reference_b
    assert len({native, reference_a, projection}) == 3


def test_evidence_reference_identity_is_stable_across_fresh_processes() -> None:
    """Reproduce one reviewed identity outside the current interpreter state."""
    code = """
from openardp.domain.identity import evidence_reference_id
print(evidence_reference_id(
    source_version_id="sha256:" + "a" * 64,
    native_representation_id="sha256:72182f254c13df619e08d78ba8f0a10f67e9b43e764aacfbb83243ab1a3b3465",
    anchor={
        "anchor_type": "text_span",
        "coordinate_system": "unicode_code_points",
        "start": 5,
        "end": 12,
        "text_length": 20,
    },
))
"""
    expected = "sha256:795c2d7373b6847fcea398809a9fef9a9030fcaa77808a927eea7a8d4e42f076"
    for _ in range(10):
        completed = subprocess.run(  # noqa: S603 - fixed interpreter and literal test code
            [sys.executable, "-c", code],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        assert completed.stdout.strip() == expected
