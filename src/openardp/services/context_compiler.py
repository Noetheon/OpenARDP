"""Deterministic bounded context compilation with body-free selection receipts."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import JsonValue, ValidationError

from openardp.adapters.context_estimators import fixed_point_measure
from openardp.domain.block import ContentBlock
from openardp.domain.common import ContentRole, Sensitivity, validate_json
from openardp.domain.context import ContextMode, EvidenceRepresentation, VersionScope
from openardp.domain.context_compilation import (
    CONTEXT_ALGORITHM_NAME,
    CONTEXT_ALGORITHM_VERSION,
    PROVENANCE_TARGET_PERCENT,
    RESPONSE_RESERVE_PERCENT,
    AlgorithmIdentity,
    BudgetLedger,
    CandidateFreshness,
    ContextBlockProvenance,
    ContextBundleBudget,
    ContextBundleNotice,
    ContextBundleV020,
    ContextCandidate,
    ContextCompilationCommit,
    ContextCompilationRecord,
    ContextCompilationResult,
    ContextCompilationScope,
    ContextCompileLimits,
    ContextCompileRequest,
    ContextEvidenceItem,
    ContextMissingEvidence,
    ContextProjectionProvenance,
    ContextSelectionPolicy,
    ContextSelectionTrace,
    CorpusSnapshot,
    ReceiptDecision,
    ReceiptNotice,
    SelectionOutcome,
    SelectionReceipt,
    UntrustedContentEnvelope,
    context_policy_digest,
    task_digest,
)
from openardp.domain.identity import (
    CANONICALIZATION_ALGORITHM,
    IDENTITY_VERSION,
    SELECTION_RECEIPT_DOMAIN,
    canonical_json_bytes,
    canonical_sha256,
    context_bundle_id,
    context_compilation_fingerprint,
    selection_receipt_id,
)
from openardp.domain.ingestion import RepresentationScope
from openardp.domain.search import MAX_QUERY_ITEMS, MAX_TERM_CHARACTERS
from openardp.domain.storage import StoredObject
from openardp.ports.catalog import (
    CatalogError,
    ContextCatalog,
    ContextCompilationConflict,
    RepresentationNotFound,
)
from openardp.ports.context import (
    CancellationCheck,
    ContextCandidateSource,
    ContextCompilationCancelled,
    ContextCompilationFailure,
    ContextConfigurationMismatch,
    ContextEstimator,
    ContextIntegrityFailure,
    ContextLimitExceeded,
    ContextNotFound,
)
from openardp.ports.object_store import ObjectStore, ObjectStoreError

_LOGGER = logging.getLogger("openardp.context_compiler")

_SENSITIVITY_RANK = {
    Sensitivity.PUBLIC: 0,
    Sensitivity.INTERNAL: 1,
    Sensitivity.CONFIDENTIAL: 2,
    Sensitivity.RESTRICTED: 3,
    Sensitivity.UNKNOWN: 4,
}

_MODE_PREFERRED: dict[ContextMode, frozenset[EvidenceRepresentation]] = {
    ContextMode.SUMMARY: frozenset({EvidenceRepresentation.SUMMARY}),
    ContextMode.EXACT: frozenset({EvidenceRepresentation.EXACT}),
    ContextMode.NUMERIC: frozenset(
        {EvidenceRepresentation.EXACT, EvidenceRepresentation.STRUCTURED}
    ),
    ContextMode.VISUAL: frozenset({EvidenceRepresentation.VISUAL_HANDLE}),
    ContextMode.VERIFICATION: frozenset({EvidenceRepresentation.EXACT}),
    ContextMode.MIXED: frozenset({EvidenceRepresentation.EXACT, EvidenceRepresentation.STRUCTURED}),
}


def _never_cancel() -> bool:
    return False


def _failure_code(error: BaseException) -> str:
    """Reduce any failure to its sanitized closed diagnostic code."""
    if isinstance(error, ContextCompilationFailure):
        return str(error) or type(error).__name__
    return type(error).__name__


def _duration_ms(started: float) -> int:
    """Return one integer millisecond duration for operational timing logs."""
    return int((time.monotonic() - started) * 1000)


def _log_failure(operation: str, started: float, error: BaseException) -> None:
    """Log one body-free failure line with operation, code and timing only."""
    _LOGGER.warning(
        "context %s failed: code=%s duration_ms=%d",
        operation,
        _failure_code(error),
        _duration_ms(started),
    )


def context_algorithm_identity() -> AlgorithmIdentity:
    """Return the exact deterministic lexical-context algorithm identity."""
    return AlgorithmIdentity(
        name=CONTEXT_ALGORITHM_NAME,
        version=CONTEXT_ALGORITHM_VERSION,
        config_hash=canonical_sha256(
            {
                "algorithm": CONTEXT_ALGORITHM_NAME,
                "version": CONTEXT_ALGORITHM_VERSION,
                "max_lexical_items": MAX_QUERY_ITEMS,
                "max_lexical_item_characters": MAX_TERM_CHARACTERS,
                "ordering": [
                    "high_value_desc",
                    "term_coverage_desc",
                    "occurrences_desc",
                    "scope_asc",
                    "source_order_asc",
                    "representation_asc",
                    "evidence_id_asc",
                ],
                "response_reserve_percent": RESPONSE_RESERVE_PERCENT,
                "provenance_target_percent": PROVENANCE_TARGET_PERCENT,
            }
        ),
    )


def required_representations(policy: ContextSelectionPolicy) -> set[EvidenceRepresentation]:
    """Derive honest evidence requirements from explicit policy or mode defaults."""
    if policy.required_evidence:
        return set(policy.required_evidence)
    return set(_MODE_PREFERRED[policy.mode])


def candidate_total_order_key(candidate: ContextCandidate) -> tuple[object, ...]:
    """Return the documented deterministic total order key for one candidate."""
    return (
        not candidate.high_value,
        -candidate.term_coverage,
        -candidate.occurrences,
        str(candidate.scope.document_id),
        candidate.scope.version_id,
        candidate.scope.representation_id,
        candidate.source_order,
        candidate.representation.value,
        candidate.evidence_id,
    )


@dataclass(frozen=True, slots=True)
class ClassifiedCandidates:
    """Policy-classified discovery partition before budget selection."""

    ordered: tuple[ContextCandidate, ...]
    rejected: tuple[tuple[ContextCandidate, str], ...]
    stale: tuple[ContextCandidate, ...]


def classify_candidates(
    candidates: tuple[ContextCandidate, ...],
    policy: ContextSelectionPolicy,
) -> ClassifiedCandidates:
    """Partition every discovered subject exactly once under the declared policy."""
    valid: list[ContextCandidate] = []
    rejected: list[tuple[ContextCandidate, str]] = []
    stale: list[ContextCandidate] = []
    seen: set[tuple[str, ...]] = set()
    maximum_rank = _SENSITIVITY_RANK[policy.maximum_sensitivity]
    for candidate in candidates:
        if candidate.freshness is not CandidateFreshness.CURRENT:
            stale.append(candidate)
            continue
        if candidate.trust.zone not in policy.allowed_trust_zones:
            rejected.append((candidate, "trust_zone_not_allowed"))
            continue
        if _SENSITIVITY_RANK[candidate.trust.sensitivity] > maximum_rank:
            rejected.append((candidate, "sensitivity_exceeded"))
            continue
        key = (
            str(candidate.scope.document_id),
            candidate.scope.version_id,
            candidate.scope.representation_id,
            candidate.evidence_id,
            candidate.representation.value,
        )
        if key in seen:
            rejected.append((candidate, "duplicate_candidate"))
            continue
        seen.add(key)
        high_value = candidate.representation in _MODE_PREFERRED[policy.mode]
        valid.append(candidate.model_copy(update={"high_value": high_value}))
    valid.sort(key=candidate_total_order_key)
    return ClassifiedCandidates(
        ordered=tuple(valid),
        rejected=tuple(rejected),
        stale=tuple(stale),
    )


@dataclass(frozen=True, slots=True)
class PersistedCompilation:
    """Verified compile result together with its immutable catalog record."""

    result: ContextCompilationResult
    record: ContextCompilationRecord


def receipt_object_bytes(receipt: SelectionReceipt) -> bytes:
    """Serialize the canonical identity envelope whose SHA-256 is the receipt ID."""
    envelope: dict[str, JsonValue] = {
        "canonicalization": CANONICALIZATION_ALGORITHM,
        "domain": SELECTION_RECEIPT_DOMAIN,
        "identity_version": IDENTITY_VERSION,
        "payload": receipt.model_dump(mode="json", exclude={"receipt_id"}),
    }
    return canonical_json_bytes(envelope)


def bundle_object_bytes(bundle: ContextBundleV020) -> bytes:
    """Serialize the complete canonical ContextBundle 0.2.0 handoff bytes."""
    return canonical_json_bytes(bundle.model_dump(mode="json"))


class ContextCompilerService:
    """Compile deterministic bounded evidence bundles plus body-free receipts."""

    def __init__(
        self,
        object_store: ObjectStore,
        catalog: ContextCatalog,
        estimator: ContextEstimator,
        candidate_sources: tuple[ContextCandidateSource, ...],
        *,
        algorithm: AlgorithmIdentity | None = None,
    ) -> None:
        """Bind provider-neutral ports and one exact estimator/algorithm identity."""
        self._object_store = object_store
        self._catalog = catalog
        self._estimator = estimator
        self._candidate_sources = candidate_sources
        self._algorithm = algorithm or context_algorithm_identity()

    def compile(
        self,
        request: ContextCompileRequest,
        *,
        cancel: CancellationCheck = _never_cancel,
    ) -> ContextCompilationResult:
        """Compile one bounded deterministic bundle and receipt without persistence."""
        started = time.monotonic()
        try:
            result = self._compile(request, cancel)
        except Exception as error:
            _log_failure("compile", started, error)
            raise
        receipt = result.receipt
        _LOGGER.debug(
            "context compile ok: receipt_id=%s bundle_id=%s selected=%d omitted=%d "
            "rejected=%d stale=%d truncated=%s budget_used=%d duration_ms=%d",
            receipt.receipt_id,
            result.bundle.bundle_id,
            len(receipt.selected),
            len(receipt.omitted),
            len(receipt.rejected),
            len(receipt.stale),
            receipt.truncated,
            receipt.budget.bundle_used,
            _duration_ms(started),
        )
        return result

    def _compile(
        self,
        request: ContextCompileRequest,
        cancel: CancellationCheck,
    ) -> ContextCompilationResult:
        """Validate identity bindings and compile against the resolved snapshot."""
        if cancel():
            raise ContextCompilationCancelled("cancelled_before_snapshot")
        if self._estimator.identity != request.estimator:
            raise ContextConfigurationMismatch("estimator_mismatch")
        snapshot = self._resolve_snapshot(request)
        return self._compile_with_snapshot(request, snapshot, cancel)

    def _compile_with_snapshot(
        self,
        request: ContextCompileRequest,
        snapshot: CorpusSnapshot,
        cancel: CancellationCheck,
    ) -> ContextCompilationResult:
        """Compile against one exact caller-supplied corpus snapshot."""
        if cancel():
            raise ContextCompilationCancelled("cancelled_before_discovery")
        discovered: list[ContextCandidate] = []
        truncated = False
        for source in self._candidate_sources:
            discovered.extend(source.discover(request.task, snapshot, request.limits, cancel))
            # Truncate after every source so combined discovery can never
            # allocate beyond the configured discovery bound.
            if len(discovered) > request.limits.max_discovered:
                del discovered[request.limits.max_discovered :]
                truncated = True
        if cancel():
            raise ContextCompilationCancelled("cancelled_before_selection")
        classified = classify_candidates(tuple(discovered), request.policy)
        ordered = classified.ordered
        if len(ordered) > request.limits.max_candidates:
            ordered = ordered[: request.limits.max_candidates]
            truncated = True

        limit = request.budget_limit
        reserve = (limit + 9) // 10
        ceiling = limit - reserve
        base_used = fixed_point_measure(
            lambda usage: self._canonical_bundle_bytes(
                request,
                snapshot,
                (),
                (),
                (),
                usage,
            ),
            self._estimator,
        )
        if base_used > ceiling:
            raise ContextLimitExceeded("base_bundle_exceeds_budget")

        selected: list[tuple[ContextCandidate, ContextEvidenceItem, int]] = []
        omitted: list[tuple[ContextCandidate, int]] = []
        used = base_used
        for candidate in ordered:
            if cancel():
                raise ContextCompilationCancelled("cancelled_during_selection")
            item = self._build_item(candidate)
            tentative: tuple[ContextEvidenceItem, ...] = (
                *tuple(entry[1] for entry in selected),
                item,
            )

            def measure(
                builder_usage: int,
                items: tuple[ContextEvidenceItem, ...] = tentative,
            ) -> bytes:
                return self._canonical_bundle_bytes(
                    request,
                    snapshot,
                    items,
                    (),
                    (),
                    builder_usage,
                )

            usage = fixed_point_measure(measure, self._estimator)
            if usage <= ceiling:
                selected.append((candidate, item, usage - used))
                used = usage
            else:
                omitted.append((candidate, usage - used))

        missing, receipt_notices = _missing_evidence(request.policy, selected)
        if truncated:
            receipt_notices.append(ReceiptNotice(code="discovery_truncated"))
        warnings: tuple[ContextBundleNotice, ...] = ()
        if truncated:
            warnings = (
                ContextBundleNotice(
                    code="discovery_truncated",
                    message="Discovery or evaluation was truncated at configured limits.",
                ),
            )
        if missing:
            final_missing = tuple(missing)
            used = fixed_point_measure(
                lambda usage: self._canonical_bundle_bytes(
                    request,
                    snapshot,
                    tuple(entry[1] for entry in selected),
                    final_missing,
                    warnings,
                    usage,
                ),
                self._estimator,
            )
            if used > ceiling:
                raise ContextLimitExceeded("bundle_exceeds_budget")

        decision_count = (
            len(selected) + len(omitted) + len(classified.rejected) + len(classified.stale)
        )
        if decision_count > request.limits.max_decisions:
            raise ContextLimitExceeded("max_decisions_exceeded")

        ledger = BudgetLedger(
            unit=request.estimator.unit,
            limit=limit,
            response_reserved=reserve,
            bundle_ceiling=ceiling,
            provenance_target=reserve,
            base_bundle_used=base_used,
            selected_incremental_used=used - base_used,
            bundle_used=used,
            remaining=ceiling - used,
        )
        bundle = self._build_bundle(
            request,
            snapshot,
            tuple(selected),
            tuple(missing),
            warnings,
            used,
        )
        receipt = self._build_receipt(
            request,
            snapshot,
            ledger,
            tuple(selected),
            tuple(omitted),
            classified,
            truncated,
            tuple(receipt_notices),
        )
        return ContextCompilationResult(bundle=bundle, receipt=receipt)

    def compile_and_persist(
        self,
        request: ContextCompileRequest,
        *,
        cancel: CancellationCheck = _never_cancel,
    ) -> PersistedCompilation:
        """Compile, publish both CAS objects and atomically link them in one commit."""
        started = time.monotonic()
        try:
            return self._compile_and_persist(request, cancel, started)
        except Exception as error:
            _log_failure("compile_and_persist", started, error)
            raise

    def _compile_and_persist(
        self,
        request: ContextCompileRequest,
        cancel: CancellationCheck,
        started: float,
    ) -> PersistedCompilation:
        """Publish, checkpoint and commit without exposing partial state."""
        if cancel():
            raise ContextCompilationCancelled("cancelled_before_persist")
        result = self._compile(request, cancel)
        receipt_bytes = receipt_object_bytes(result.receipt)
        bundle_bytes = bundle_object_bytes(result.bundle)
        try:
            receipt_object = self._object_store.put_chunks((receipt_bytes,))
            bundle_object = self._object_store.put_chunks((bundle_bytes,))
        except ObjectStoreError as error:
            raise ContextIntegrityFailure("compilation_object_publication_failed") from error
        if receipt_object.object_id != result.receipt.receipt_id:
            raise ContextIntegrityFailure("receipt_object_identity_mismatch")
        _read_verified(self._object_store, receipt_object)
        _read_verified(self._object_store, bundle_object)
        if cancel():
            # The immutable pre-published objects stay unreachable recovery
            # candidates; no catalog-visible compilation can exist yet.
            raise ContextCompilationCancelled("cancelled_before_commit")
        commit = ContextCompilationCommit(
            record=self._compilation_record(result, receipt_object, bundle_object),
            scopes=tuple(
                ContextCompilationScope(
                    receipt_id=result.receipt.receipt_id,
                    ordinal=index,
                    scope=scope,
                )
                for index, scope in enumerate(result.receipt.corpus_snapshot)
            ),
        )
        # A commit failure here leaves the immutable CAS objects as unreachable
        # recovery candidates and exposes no compilation row.
        try:
            record = self._catalog.commit_context_compilation(commit)
        except ContextCompilationConflict as error:
            raise ContextIntegrityFailure("compilation_commit_conflict") from error
        except RepresentationNotFound as error:
            raise ContextIntegrityFailure("compilation_scope_root_missing") from error
        except CatalogError as error:
            raise ContextIntegrityFailure("compilation_commit_failed") from error
        verified_commit, verified = self._load_verified(record.receipt_id)
        if verified_commit != commit:
            raise ContextIntegrityFailure("persisted_compilation_diverged")
        _LOGGER.debug(
            "context compilation persisted: receipt_id=%s bundle_id=%s "
            "receipt_object=%s bundle_object=%s duration_ms=%d",
            record.receipt_id,
            record.bundle_id,
            record.receipt_object.object_id,
            record.bundle_object.object_id,
            _duration_ms(started),
        )
        return PersistedCompilation(result=verified, record=record)

    def load_verified(self, receipt_id: str) -> ContextCompilationResult:
        """Return one persisted compilation only after complete verification."""
        started = time.monotonic()
        try:
            _commit, result = self._load_verified(receipt_id)
        except Exception as error:
            _log_failure("load_verified", started, error)
            raise
        _LOGGER.debug(
            "context compilation loaded: receipt_id=%s bundle_id=%s duration_ms=%d",
            receipt_id,
            result.bundle.bundle_id,
            _duration_ms(started),
        )
        return result

    def replay(
        self,
        task: str,
        receipt_id: str,
        *,
        cancel: CancellationCheck = _never_cancel,
    ) -> ContextCompilationResult:
        """Recompile the recorded exact snapshot and require byte-identical output."""
        started = time.monotonic()
        try:
            result = self._replay(task, receipt_id, cancel)
        except Exception as error:
            _log_failure("replay", started, error)
            raise
        _LOGGER.debug(
            "context replay ok: receipt_id=%s bundle_id=%s duration_ms=%d",
            receipt_id,
            result.bundle.bundle_id,
            _duration_ms(started),
        )
        return result

    def _replay(
        self,
        task: str,
        receipt_id: str,
        cancel: CancellationCheck,
    ) -> ContextCompilationResult:
        """Verify, guard identities and recompile the pinned exact snapshot."""
        if cancel():
            raise ContextCompilationCancelled("cancelled_before_replay")
        commit, result = self._load_verified(receipt_id)
        receipt = result.receipt
        if task_digest(task) != receipt.task_digest:
            raise ContextConfigurationMismatch("task_mismatch")
        if self._estimator.identity != receipt.estimator:
            raise ContextConfigurationMismatch("estimator_mismatch")
        if self._algorithm != receipt.algorithm:
            raise ContextConfigurationMismatch("algorithm_mismatch")
        snapshot = CorpusSnapshot(
            scopes=tuple(scope.scope for scope in commit.scopes),
            created_at=receipt.created_at,
        )
        document_ids = tuple(sorted({scope.scope.document_id for scope in commit.scopes}, key=str))
        request = ContextCompileRequest(
            task=task,
            document_ids=document_ids,
            budget_limit=commit.record.budget_limit,
            estimator=receipt.estimator,
            policy=receipt.policy,
            limits=ContextCompileLimits(),
        )
        recompiled = self._compile_with_snapshot(request, snapshot, cancel)
        if bundle_object_bytes(recompiled.bundle) != bundle_object_bytes(result.bundle):
            raise ContextConfigurationMismatch("replay_bundle_diverged")
        if receipt_object_bytes(recompiled.receipt) != receipt_object_bytes(result.receipt):
            raise ContextConfigurationMismatch("replay_receipt_diverged")
        return result

    def _load_verified(
        self,
        receipt_id: str,
    ) -> tuple[ContextCompilationCommit, ContextCompilationResult]:
        """Load rows and objects and verify every identity, count and scope fact."""
        try:
            commit = self._catalog.load_context_compilation(receipt_id)
        except CatalogError as error:
            raise ContextIntegrityFailure("compilation_row_invalid") from error
        if commit is None:
            raise ContextNotFound("compilation_missing")
        record = commit.record
        receipt = self._verified_receipt_object(record)
        bundle = self._verified_bundle_object(record)
        try:
            result = ContextCompilationResult(bundle=bundle, receipt=receipt)
        except ValidationError as error:
            raise ContextIntegrityFailure("compilation_aggregate_mismatch") from error
        self._verify_compilation_facts(commit, result)
        return commit, result

    def _verified_receipt_object(self, record: ContextCompilationRecord) -> SelectionReceipt:
        """Verify the receipt CAS object digest, envelope and canonical identity."""
        payload = _read_verified(self._object_store, record.receipt_object)
        try:
            envelope = json.loads(payload)
        except json.JSONDecodeError as error:
            raise ContextIntegrityFailure("receipt_object_not_json") from error
        if not isinstance(envelope, dict) or set(envelope) != {
            "canonicalization",
            "domain",
            "identity_version",
            "payload",
        }:
            raise ContextIntegrityFailure("receipt_object_envelope_invalid")
        if (
            envelope["canonicalization"] != CANONICALIZATION_ALGORITHM
            or envelope["domain"] != SELECTION_RECEIPT_DOMAIN
            or envelope["identity_version"] != IDENTITY_VERSION
        ):
            raise ContextIntegrityFailure("receipt_object_envelope_mismatch")
        if canonical_json_bytes(envelope) != payload:
            raise ContextIntegrityFailure("receipt_object_noncanonical")
        body = envelope["payload"]
        if not isinstance(body, dict):
            raise ContextIntegrityFailure("receipt_object_payload_invalid")
        try:
            return validate_json(
                SelectionReceipt,
                canonical_json_bytes({**body, "receipt_id": record.receipt_object.object_id}),
            )
        except (ValidationError, ValueError) as error:
            raise ContextIntegrityFailure("receipt_object_invalid") from error

    def _verified_bundle_object(self, record: ContextCompilationRecord) -> ContextBundleV020:
        """Verify the bundle CAS object digest, model identity and canonical shape."""
        payload = _read_verified(self._object_store, record.bundle_object)
        try:
            bundle = validate_json(ContextBundleV020, payload)
        except (ValidationError, ValueError) as error:
            raise ContextIntegrityFailure("bundle_object_invalid") from error
        if canonical_json_bytes(bundle.model_dump(mode="json")) != payload:
            raise ContextIntegrityFailure("bundle_object_noncanonical")
        return bundle

    def _verify_compilation_facts(
        self,
        commit: ContextCompilationCommit,
        result: ContextCompilationResult,
    ) -> None:
        """Cross-check row, scope, decision and budget facts against the objects."""
        record = commit.record
        receipt = result.receipt
        bundle = result.bundle
        if (
            record.bundle_id != bundle.bundle_id
            or record.task_digest != receipt.task_digest
            or record.algorithm != receipt.algorithm
            or record.estimator != receipt.estimator
            or record.policy_digest != receipt.policy_digest
            or record.budget_limit != receipt.budget.limit
            or record.budget_unit != receipt.budget.unit
            or record.created_at != receipt.created_at
        ):
            raise ContextIntegrityFailure("compilation_row_mismatch")
        counts = (
            (record.selected_count, len(receipt.selected)),
            (record.omitted_count, len(receipt.omitted)),
            (record.rejected_count, len(receipt.rejected)),
            (record.stale_count, len(receipt.stale)),
        )
        if any(expected != actual for expected, actual in counts):
            raise ContextIntegrityFailure("compilation_count_mismatch")
        if tuple(scope.scope for scope in commit.scopes) != tuple(receipt.corpus_snapshot):
            raise ContextIntegrityFailure("compilation_scope_mismatch")
        for scope in commit.scopes:
            try:
                persisted = self._catalog.load_representation(
                    RepresentationScope(
                        document_id=scope.scope.document_id,
                        version_id=scope.scope.version_id,
                        representation_id=scope.scope.representation_id,
                    )
                )
            except CatalogError as error:
                raise ContextIntegrityFailure("compilation_scope_unreadable") from error
            if persisted is None:
                raise ContextIntegrityFailure("compilation_scope_missing")
        if len(bundle.items) != len(receipt.selected):
            raise ContextIntegrityFailure("compilation_decision_mismatch")
        for index, (decision, item) in enumerate(zip(receipt.selected, bundle.items, strict=True)):
            if (
                decision.final_order != index
                or _item_evidence_id(item) != decision.evidence_id
                or _item_scope(item) != decision.scope
                or item.representation != decision.representation
                or item.trust.role is not ContentRole.DATA
                or item.trust.instruction_execution_allowed
            ):
                raise ContextIntegrityFailure("compilation_decision_mismatch")
        ledger = receipt.budget
        reserve = (ledger.limit + 9) // 10
        if (
            ledger.response_reserved != reserve
            or ledger.bundle_ceiling != ledger.limit - reserve
            or ledger.bundle_used > ledger.bundle_ceiling
            or ledger.remaining != ledger.bundle_ceiling - ledger.bundle_used
            or ledger.bundle_used != ledger.base_bundle_used + ledger.selected_incremental_used
        ):
            raise ContextIntegrityFailure("compilation_budget_mismatch")

    @staticmethod
    def _compilation_record(
        result: ContextCompilationResult,
        receipt_object: StoredObject,
        bundle_object: StoredObject,
    ) -> ContextCompilationRecord:
        """Build the immutable body-free catalog row with its recomputed fingerprint."""
        receipt = result.receipt
        payload: dict[str, Any] = {
            "receipt_id": receipt.receipt_id,
            "receipt_object": receipt_object,
            "bundle_object": bundle_object,
            "bundle_id": result.bundle.bundle_id,
            "task_digest": receipt.task_digest,
            "algorithm": receipt.algorithm,
            "estimator": receipt.estimator,
            "policy_digest": receipt.policy_digest,
            "budget_limit": receipt.budget.limit,
            "budget_unit": receipt.budget.unit,
            "created_at": receipt.created_at,
            "selected_count": len(receipt.selected),
            "omitted_count": len(receipt.omitted),
            "rejected_count": len(receipt.rejected),
            "stale_count": len(receipt.stale),
        }
        draft = ContextCompilationRecord.model_construct(
            row_fingerprint="sha256:" + "0" * 64,
            **payload,
        )
        identity_payload = draft.model_dump(mode="json", exclude={"row_fingerprint"})
        payload["row_fingerprint"] = context_compilation_fingerprint(identity_payload)
        return ContextCompilationRecord.model_validate(payload)

    def _resolve_snapshot(self, request: ContextCompileRequest) -> CorpusSnapshot:
        """Resolve each requested document to one exact current READY scope."""
        try:
            return self._resolve_snapshot_rows(request)
        except CatalogError as error:
            raise ContextIntegrityFailure("catalog_read_failed") from error

    def _resolve_snapshot_rows(self, request: ContextCompileRequest) -> CorpusSnapshot:
        """Read head rows and map absent scopes to closed not-found codes."""
        scopes: list[VersionScope] = []
        observed: list[datetime] = []
        for document_id in request.document_ids:
            if self._catalog.get_document(document_id) is None:
                raise ContextNotFound("document_missing")
            head = self._catalog.get_document_head(document_id)
            if head is None:
                raise ContextNotFound("ready_head_missing")
            scopes.append(
                VersionScope(
                    document_id=head.scope.document_id,
                    version_id=head.scope.version_id,
                    representation_id=head.scope.representation_id,
                )
            )
            observed.append(head.last_ingested_at)
        return CorpusSnapshot(scopes=tuple(scopes), created_at=max(observed))

    def _build_item(self, candidate: ContextCandidate) -> ContextEvidenceItem:
        """Build one verified handle or delimited untrusted-data item."""
        if candidate.representation is EvidenceRepresentation.VISUAL_HANDLE:
            if candidate.artifact_handle is None or candidate.artifact_id is None:
                raise ContextIntegrityFailure("selected_visual_handle_invalid")
            return ContextEvidenceItem(
                provenance=candidate.provenance,
                representation=candidate.representation,
                artifact_handle=candidate.artifact_handle,
                artifact_id=candidate.artifact_id,
                reason=candidate.reason_code,
                trust=candidate.trust,
            )
        if isinstance(candidate.provenance, ContextBlockProvenance):
            content = self._block_content(candidate)
        else:
            content = self._projection_content(candidate)
        return ContextEvidenceItem(
            provenance=candidate.provenance,
            representation=candidate.representation,
            content=content,
            reason=candidate.reason_code,
            trust=candidate.trust,
        )

    def _block_content(self, candidate: ContextCandidate) -> UntrustedContentEnvelope:
        """Reverify one F002 block object and enclose its exact content as data."""
        if candidate.body_object is None:
            raise ContextIntegrityFailure("selected_block_body_missing")
        payload = _read_verified(self._object_store, candidate.body_object)
        try:
            block = validate_json(ContentBlock, payload)
        except (ValidationError, ValueError) as error:
            raise ContextIntegrityFailure("selected_block_invalid") from error
        provenance = candidate.provenance
        if (
            not isinstance(provenance, ContextBlockProvenance)
            or block.block_id != provenance.block_id
            or str(block.document_id) != str(provenance.document_id)
            or block.version_id != provenance.version_id
            or block.representation_id != provenance.representation_id
        ):
            raise ContextIntegrityFailure("selected_block_mismatch")
        if block.text is not None:
            return UntrustedContentEnvelope(media_type="text/plain", body=block.text)
        if block.structured is not None:
            return UntrustedContentEnvelope(
                media_type="application/json",
                body=block.structured,
            )
        raise ContextIntegrityFailure("selected_block_without_content")

    def _projection_content(self, candidate: ContextCandidate) -> UntrustedContentEnvelope:
        """Reverify one F006 retrieval body and enclose it as data."""
        provenance = candidate.provenance
        if not isinstance(provenance, ContextProjectionProvenance):
            raise ContextIntegrityFailure("selected_projection_mismatch")
        if candidate.body_object is None or candidate.body_media_type is None:
            raise ContextIntegrityFailure("selected_projection_body_missing")
        payload = _read_verified(self._object_store, candidate.body_object)
        try:
            body = payload.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ContextIntegrityFailure("selected_projection_not_utf8") from error
        if candidate.body_media_type == "application/json":
            try:
                value: JsonValue = json.loads(body)
                if canonical_json_bytes(value) != payload:
                    raise ValueError
            except (json.JSONDecodeError, TypeError, ValueError) as error:
                raise ContextIntegrityFailure("selected_projection_noncanonical_json") from error
            return UntrustedContentEnvelope(media_type="application/json", body=value)
        return UntrustedContentEnvelope(media_type="text/plain", body=body)

    def _canonical_bundle_bytes(
        self,
        request: ContextCompileRequest,
        snapshot: CorpusSnapshot,
        items: tuple[ContextEvidenceItem, ...],
        missing: tuple[ContextMissingEvidence, ...],
        warnings: tuple[ContextBundleNotice, ...],
        usage: int,
    ) -> bytes:
        """Serialize the canonical bundle with a fixed-width placeholder identity."""
        trace = tuple(
            ContextSelectionTrace(
                evidence_id=_item_evidence_id(item),
                final_order=index,
                reason_code=item.reason,
            )
            for index, item in enumerate(items)
        )
        draft = ContextBundleV020.model_construct(
            schema_version="0.2.0",
            bundle_id=UUID(int=0),
            created_at=snapshot.created_at,
            query=request.task,
            mode=request.policy.mode,
            # Measurement drafts must tolerate usage above the budget limit so
            # the fixed point converges honestly; only the final validated
            # bundle may persist, and admission guarantees it fits.
            budget=ContextBundleBudget.model_construct(
                unit=request.estimator.unit,
                limit=request.budget_limit,
                estimated_used=usage,
                estimator=request.estimator,
                actual_used=usage,
            ),
            versions=snapshot.scopes,
            items=items,
            selection_trace=trace,
            warnings=warnings,
            missing_evidence=missing,
            extensions={},
        )
        return canonical_json_bytes(draft.model_dump(mode="json"))

    def _build_bundle(
        self,
        request: ContextCompileRequest,
        snapshot: CorpusSnapshot,
        selected: tuple[tuple[ContextCandidate, ContextEvidenceItem, int], ...],
        missing: tuple[ContextMissingEvidence, ...],
        warnings: tuple[ContextBundleNotice, ...],
        used: int,
    ) -> ContextBundleV020:
        """Assemble the immutable bundle with its recomputed UUIDv5 identity."""
        items = tuple(entry[1] for entry in selected)
        trace = tuple(
            ContextSelectionTrace(
                evidence_id=_item_evidence_id(item),
                final_order=index,
                reason_code=item.reason,
            )
            for index, item in enumerate(items)
        )
        payload: dict[str, Any] = {
            "schema_version": "0.2.0",
            "created_at": snapshot.created_at,
            "query": request.task,
            "mode": request.policy.mode,
            "budget": ContextBundleBudget(
                unit=request.estimator.unit,
                limit=request.budget_limit,
                estimated_used=used,
                estimator=request.estimator,
                actual_used=used,
            ),
            "versions": snapshot.scopes,
            "items": items,
            "selection_trace": trace,
            "warnings": warnings,
            "missing_evidence": missing,
            "extensions": {},
        }
        draft = ContextBundleV020.model_construct(bundle_id=UUID(int=0), **payload)
        identity_payload = draft.model_dump(mode="json", exclude={"bundle_id"})
        payload["bundle_id"] = context_bundle_id(identity_payload)
        return ContextBundleV020.model_validate(payload)

    def _build_receipt(
        self,
        request: ContextCompileRequest,
        snapshot: CorpusSnapshot,
        ledger: BudgetLedger,
        selected: tuple[tuple[ContextCandidate, ContextEvidenceItem, int], ...],
        omitted: tuple[tuple[ContextCandidate, int], ...],
        classified: ClassifiedCandidates,
        truncated: bool,
        notices: tuple[ReceiptNotice, ...],
    ) -> SelectionReceipt:
        """Assemble the body-free receipt with its recomputed SHA-256 identity."""
        selected_decisions = tuple(
            _decision(candidate, SelectionOutcome.SELECTED, cost, final_order=index)
            for index, (candidate, _item, cost) in enumerate(selected)
        )
        omitted_decisions = tuple(
            _decision(candidate, SelectionOutcome.OMITTED, cost) for candidate, cost in omitted
        )
        rejected_decisions = tuple(
            _decision(candidate, SelectionOutcome.REJECTED, None, reason_code=reason)
            for candidate, reason in classified.rejected
        )
        stale_decisions = tuple(
            _decision(
                candidate,
                SelectionOutcome.STALE,
                None,
                reason_code="stale_freshness_excluded",
            )
            for candidate in classified.stale
        )
        payload: dict[str, Any] = {
            "contract_version": "0.1.0",
            "stability": "experimental",
            "identity_version": 1,
            "created_at": snapshot.created_at,
            "task_digest": task_digest(request.task),
            "algorithm": self._algorithm,
            "estimator": request.estimator,
            "policy": request.policy,
            "policy_digest": context_policy_digest(request.policy),
            "corpus_snapshot": snapshot.scopes,
            "budget": ledger,
            "selected": selected_decisions,
            "omitted": omitted_decisions,
            "rejected": rejected_decisions,
            "stale": stale_decisions,
            "truncated": truncated,
            "notices": notices,
            "extensions": {},
        }
        draft = SelectionReceipt.model_construct(receipt_id="sha256:" + "0" * 64, **payload)
        identity_payload = draft.model_dump(mode="json", exclude={"receipt_id"})
        payload["receipt_id"] = selection_receipt_id(identity_payload)
        return SelectionReceipt.model_validate(payload)


def _item_evidence_id(item: ContextEvidenceItem) -> str:
    provenance = item.provenance
    if isinstance(provenance, ContextBlockProvenance):
        return str(provenance.block_id)
    return provenance.evidence_projection_id


def _candidate_object_cost(candidate: ContextCandidate) -> int:
    """Return the verified body or descriptor object length used for receipt costing."""
    value = candidate.body_object or candidate.cost_object
    if value is None:
        raise ContextIntegrityFailure("candidate_cost_object_missing")
    return value.byte_length


def _decision(
    candidate: ContextCandidate,
    outcome: SelectionOutcome,
    cost: int | None,
    *,
    reason_code: str | None = None,
    final_order: int | None = None,
) -> ReceiptDecision:
    """Project one classified candidate into its body-free receipt decision."""
    return ReceiptDecision(
        outcome=outcome,
        evidence_id=candidate.evidence_id,
        scope=candidate.scope,
        representation=candidate.representation,
        reason_code=reason_code if reason_code is not None else candidate.reason_code,
        high_value=candidate.high_value,
        term_coverage=candidate.term_coverage,
        occurrences=candidate.occurrences,
        source_order=candidate.source_order,
        estimated_cost=(cost if cost is not None else _candidate_object_cost(candidate)),
        final_order=final_order,
    )


def _missing_evidence(
    policy: ContextSelectionPolicy,
    selected: list[tuple[ContextCandidate, ContextEvidenceItem, int]],
) -> tuple[list[ContextMissingEvidence], list[ReceiptNotice]]:
    """Report unsatisfied requirements and visual escalation honestly."""
    required = required_representations(policy)
    satisfied = {entry[1].representation for entry in selected}
    missing: list[ContextMissingEvidence] = []
    notices: list[ReceiptNotice] = []
    if not (required & satisfied):
        for representation in sorted(required, key=lambda item: item.value):
            missing.append(
                ContextMissingEvidence(
                    evidence_type=representation,
                    reason_code="required_evidence_unavailable",
                )
            )
    if EvidenceRepresentation.VISUAL_HANDLE in required and (
        EvidenceRepresentation.VISUAL_HANDLE not in satisfied
    ):
        if not any(item.evidence_type is EvidenceRepresentation.VISUAL_HANDLE for item in missing):
            missing.append(
                ContextMissingEvidence(
                    evidence_type=EvidenceRepresentation.VISUAL_HANDLE,
                    reason_code="visual_evidence_required",
                )
            )
        notices.append(ReceiptNotice(code="visual_evidence_required"))
    return missing, notices


def _read_verified(object_store: ObjectStore, stored: StoredObject) -> bytes:
    """Read one object only after digest, length and shape verification."""
    try:
        verified = object_store.verify(stored.object_id, expected_length=stored.byte_length)
        payload = b"".join(object_store.iter_chunks(verified.object_id))
    except ObjectStoreError as error:
        raise ContextIntegrityFailure("selected_object_invalid") from error
    if len(payload) != verified.byte_length:
        raise ContextIntegrityFailure("selected_object_length_changed")
    return payload


def _item_scope(item: ContextEvidenceItem) -> VersionScope:
    """Return the exact corpus scope of one persisted evidence item."""
    provenance = item.provenance
    return VersionScope(
        document_id=provenance.document_id,
        version_id=provenance.version_id,
        representation_id=provenance.representation_id,
    )


__all__ = [
    "ClassifiedCandidates",
    "ContextCompilerService",
    "PersistedCompilation",
    "bundle_object_bytes",
    "candidate_total_order_key",
    "classify_candidates",
    "context_algorithm_identity",
    "receipt_object_bytes",
    "required_representations",
]
