"""Protocol and stable error tests for F011 visual provider boundaries."""

from __future__ import annotations

from typing import cast

from openardp.adapters.visual_policy import LocalOnlyVisualPolicy
from openardp.domain.evidence import EvidenceProjection
from openardp.ports.visual import (
    UnsupportedVisualMedia,
    VisualCancelled,
    VisualConflict,
    VisualDependencyUnavailable,
    VisualEncryptedInput,
    VisualError,
    VisualGeometryMismatch,
    VisualIntegrityError,
    VisualInterpretationUnavailable,
    VisualMalformedInput,
    VisualProcessCrashed,
    VisualResourceLimitExceeded,
    VisualTargetUnavailable,
    VisualTimedOut,
)


def test_visual_error_codes_are_stable_body_free_machine_values() -> None:
    """Expose a closed sanitized failure taxonomy without source details."""
    errors: tuple[type[VisualError], ...] = (
        UnsupportedVisualMedia,
        VisualCancelled,
        VisualConflict,
        VisualDependencyUnavailable,
        VisualEncryptedInput,
        VisualGeometryMismatch,
        VisualIntegrityError,
        VisualInterpretationUnavailable,
        VisualMalformedInput,
        VisualProcessCrashed,
        VisualResourceLimitExceeded,
        VisualTargetUnavailable,
        VisualTimedOut,
    )
    codes = tuple(error.code for error in errors)
    assert codes == tuple(sorted(set(codes)))
    assert all(code.isascii() and code.replace("_", "").isalnum() for code in codes)


def test_default_rights_policy_is_conservative_and_provider_independent() -> None:
    """Keep the trusted built-in decision closed even without document metadata."""
    policy = LocalOnlyVisualPolicy()
    result = policy.evaluate(cast(EvidenceProjection, object()))
    assert result.scope.value == "local_only"
    assert result.export_allowed is False
    assert result.license_id is None
    assert result.restriction_codes == ("license_unverified",)
    assert result.policy_provider.name == "openardp-local-policy"
