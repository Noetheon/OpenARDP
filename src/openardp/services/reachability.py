"""Read-only comparison of catalog roots with verified object-store state."""

from __future__ import annotations

from datetime import datetime

from openardp.domain.storage import (
    ReachabilityIssue,
    ReachabilityIssueCode,
    ReachabilityReport,
    StoreAnomaly,
    StoreAnomalyCode,
)
from openardp.ports.catalog import Catalog
from openardp.ports.object_store import ObjectStore


class ReachabilityService:
    """Classify verified objects and inconsistencies without deletion authority."""

    def __init__(self, object_store: ObjectStore, catalog: Catalog) -> None:
        """Bind provider-neutral read ports for one advisory analysis."""
        self._object_store = object_store
        self._catalog = catalog

    def analyze(self, *, observed_at: datetime) -> ReachabilityReport:
        """Compare one catalog snapshot with a later verified CAS inventory."""
        snapshot = self._catalog.reference_snapshot(observed_at=observed_at)
        inventory = self._object_store.inventory()
        roots = set(snapshot.object_ids)
        verified = {item.object_id: item for item in inventory.objects}
        anomalies_by_object: dict[str, list[StoreAnomaly]] = {}
        for anomaly in inventory.anomalies:
            if anomaly.object_id is not None:
                anomalies_by_object.setdefault(anomaly.object_id, []).append(anomaly)

        issues: list[ReachabilityIssue] = []
        for object_id in sorted(roots - verified.keys()):
            object_anomalies = anomalies_by_object.get(object_id, [])
            corrupt = next(
                (
                    anomaly
                    for anomaly in object_anomalies
                    if anomaly.code is StoreAnomalyCode.CORRUPT_OBJECT
                ),
                None,
            )
            unsafe = next(
                (
                    anomaly
                    for anomaly in object_anomalies
                    if anomaly.code is StoreAnomalyCode.UNSAFE_ENTRY
                ),
                None,
            )
            if corrupt is not None:
                issues.append(
                    ReachabilityIssue(
                        code=ReachabilityIssueCode.CORRUPT_REFERENCE,
                        object_id=object_id,
                        relative_location=corrupt.relative_location,
                    )
                )
            elif unsafe is not None:
                issues.append(
                    ReachabilityIssue(
                        code=ReachabilityIssueCode.UNSAFE_STORE_ENTRY,
                        object_id=object_id,
                        relative_location=unsafe.relative_location,
                    )
                )
            else:
                issues.append(
                    ReachabilityIssue(
                        code=ReachabilityIssueCode.MISSING_REFERENCE,
                        object_id=object_id,
                    )
                )

        for anomaly in inventory.anomalies:
            if anomaly.object_id in roots:
                continue
            issues.append(self._issue_from_anomaly(anomaly))

        reachable = tuple(item for item in inventory.objects if item.object_id in roots)
        candidates = tuple(item for item in inventory.objects if item.object_id not in roots)
        return ReachabilityReport(
            observed_at=observed_at,
            catalog_schema_version=snapshot.catalog_schema_version,
            reachable=reachable,
            candidates=candidates,
            inconsistencies=tuple(sorted(set(issues), key=self._issue_key)),
        )

    @staticmethod
    def _issue_from_anomaly(anomaly: StoreAnomaly) -> ReachabilityIssue:
        mapping = {
            StoreAnomalyCode.MALFORMED_ENTRY: ReachabilityIssueCode.MALFORMED_STORE_ENTRY,
            StoreAnomalyCode.UNSAFE_ENTRY: ReachabilityIssueCode.UNSAFE_STORE_ENTRY,
            StoreAnomalyCode.CORRUPT_OBJECT: ReachabilityIssueCode.CORRUPT_STORE_OBJECT,
            StoreAnomalyCode.STAGING_RESIDUE: ReachabilityIssueCode.STAGING_RESIDUE,
        }
        return ReachabilityIssue(
            code=mapping[anomaly.code],
            object_id=anomaly.object_id,
            relative_location=anomaly.relative_location,
        )

    @staticmethod
    def _issue_key(issue: ReachabilityIssue) -> tuple[str, str, str]:
        return issue.code.value, issue.object_id or "", issue.relative_location or ""
