"""Conservative trusted local usage policy for visual evidence."""

from __future__ import annotations

from openardp.domain.common import ComponentDescriptor
from openardp.domain.evidence import EvidenceProjection
from openardp.domain.identity import canonical_sha256
from openardp.domain.visual import VisualUsagePolicy, VisualUsageScope


class LocalOnlyVisualPolicy:
    """Deny export unless a future explicit trusted policy implementation allows it."""

    _provider = ComponentDescriptor(
        name="openardp-local-policy",
        version="1.0.0",
        profile="closed-default",
    )
    _config_hash = canonical_sha256(
        {
            "export_allowed": False,
            "license_id": None,
            "restriction_codes": ["license_unverified"],
            "scope": "local_only",
        }
    )

    def evaluate(self, projection: EvidenceProjection) -> VisualUsagePolicy:
        """Return a document-metadata-independent local-only policy."""
        del projection
        return VisualUsagePolicy(
            scope=VisualUsageScope.LOCAL_ONLY,
            export_allowed=False,
            license_id=None,
            restriction_codes=("license_unverified",),
            policy_provider=self._provider,
            policy_config_hash=self._config_hash,
        )


__all__ = ["LocalOnlyVisualPolicy"]
