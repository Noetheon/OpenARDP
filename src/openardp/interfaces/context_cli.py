"""CLI-specific context compile/replay orchestration."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
from typing import Protocol
from uuid import UUID

from openardp.adapters.context_estimators import (
    ConservativeTokenEstimator,
    UnicodeCharacterEstimator,
    Utf8ByteEstimator,
)
from openardp.adapters.e5_semantic import IsolatedE5SemanticProvider
from openardp.adapters.local_workspace import LocalWorkspace
from openardp.domain.common import Sensitivity
from openardp.domain.context import ContextMode
from openardp.domain.context_compilation import (
    AlgorithmIdentity,
    ContextCompilationResult,
    ContextCompileRequest,
    ContextSelectionPolicy,
)
from openardp.interfaces.context_composition import (
    RetrievalProfile,
    retrieval_profile_for_algorithm,
)
from openardp.ports.context import ContextConfigurationMismatch, ContextEstimator
from openardp.ports.semantic_retrieval import SemanticRetrievalProvider
from openardp.services.context_compiler import ContextCompilerService


class ContextCommandUsageError(ValueError):
    """Bounded CLI usage failure suitable for the stable public envelope."""


class ContextCompilerFactory(Protocol):
    """Compose a compiler for one explicit profile and optional replay identity."""

    def __call__(
        self,
        workspace: LocalWorkspace,
        estimator: ContextEstimator,
        *,
        algorithm: AlgorithmIdentity | None = None,
        profile: RetrievalProfile = RetrievalProfile.LEXICAL,
        provider: SemanticRetrievalProvider | None = None,
    ) -> ContextCompilerService: ...


def estimator_for(unit: str) -> ContextEstimator:
    """Resolve one exact built-in estimator for the bounded CLI unit name."""
    if unit == "characters":
        return UnicodeCharacterEstimator()
    if unit == "tokens":
        return ConservativeTokenEstimator()
    return Utf8ByteEstimator()


def receipt_identity(value: str) -> str:
    """Validate one exact selection-receipt identity without inspecting state."""
    digest = value.removeprefix("sha256:")
    if (
        len(digest) != 64
        or len(value) != 71
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ContextCommandUsageError("receipt identifier is invalid")
    return value


def context_summary(
    result: ContextCompilationResult,
    *,
    replayed: bool,
    include_bundle: bool,
) -> dict[str, object]:
    """Project one compile/replay result into bounded handles and accounting."""
    receipt = result.receipt
    summary: dict[str, object] = {
        "bundle_id": str(result.bundle.bundle_id),
        "receipt_id": receipt.receipt_id,
        "persisted": True,
        "replayed": replayed,
        "created_at": receipt.model_dump(mode="json")["created_at"],
        "mode": receipt.policy.mode.value,
        "estimator": receipt.estimator,
        "scopes": receipt.corpus_snapshot,
        "budget": receipt.budget,
        "counts": {
            "selected": len(receipt.selected),
            "omitted": len(receipt.omitted),
            "rejected": len(receipt.rejected),
            "stale": len(receipt.stale),
        },
        "truncated": receipt.truncated,
        "notices": receipt.notices,
        "warnings": result.bundle.warnings,
        "missing_evidence": result.bundle.missing_evidence,
    }
    if include_bundle:
        summary["bundle"] = result.bundle
    return summary


def semantic_configuration(arguments: argparse.Namespace) -> tuple[Path, Path] | None:
    """Return one explicit all-or-none local semantic configuration."""
    bundle = arguments.semantic_bundle
    source_lock = arguments.semantic_source_lock
    if (bundle is None) != (source_lock is None):
        raise ContextCommandUsageError("semantic bundle and source lock must be provided together")
    if bundle is None or source_lock is None:
        return None
    return Path(bundle), Path(source_lock)


def open_semantic_provider(configuration: tuple[Path, Path]) -> IsolatedE5SemanticProvider:
    """Construct one exact lazy provider from trusted local process configuration."""
    bundle, source_lock = configuration
    return IsolatedE5SemanticProvider(bundle, expected_source_lock=source_lock)


def _document_ids(values: list[str]) -> tuple[UUID, ...]:
    try:
        return tuple(sorted({UUID(str(value)) for value in values}, key=str))
    except ValueError:
        raise ContextCommandUsageError("identifier must be a UUID") from None


def compile_context_command(
    workspace: LocalWorkspace,
    arguments: argparse.Namespace,
    compiler_factory: ContextCompilerFactory,
    *,
    provider_factory: Callable[
        [tuple[Path, Path]], SemanticRetrievalProvider
    ] = open_semantic_provider,
) -> object:
    """Compile or replay one explicit profile and close optional provider state."""
    estimator = estimator_for(str(arguments.unit or "bytes"))
    task = str(arguments.task)
    configuration = semantic_configuration(arguments)
    provider: SemanticRetrievalProvider | None = None
    try:
        if arguments.replay is not None:
            if arguments.document or arguments.budget is not None or arguments.mode is not None:
                raise ContextCommandUsageError(
                    "replay accepts only task, unit, receipt and store options"
                )
            receipt_id = receipt_identity(str(arguments.replay))
            loaded = compiler_factory(workspace, estimator).load_verified(receipt_id)
            persisted_profile = retrieval_profile_for_algorithm(loaded.receipt.algorithm)
            requested_profile = (
                RetrievalProfile(str(arguments.retrieval_profile))
                if arguments.retrieval_profile is not None
                else persisted_profile
            )
            if requested_profile is not persisted_profile:
                raise ContextConfigurationMismatch("retrieval_profile_mismatch")
            if persisted_profile is RetrievalProfile.SEMANTIC:
                if configuration is None:
                    raise ContextCommandUsageError(
                        "semantic replay requires bundle and source lock"
                    )
                provider = provider_factory(configuration)
            elif configuration is not None:
                raise ContextCommandUsageError("lexical replay rejects semantic configuration")
            result = compiler_factory(
                workspace,
                estimator,
                algorithm=loaded.receipt.algorithm,
                profile=persisted_profile,
                provider=provider,
            ).replay(task, receipt_id)
            return context_summary(
                result,
                replayed=True,
                include_bundle=bool(arguments.include_bundle),
            )
        profile = RetrievalProfile(str(arguments.retrieval_profile or RetrievalProfile.LEXICAL))
        if profile is RetrievalProfile.SEMANTIC:
            if configuration is None:
                raise ContextCommandUsageError("semantic profile requires bundle and source lock")
            provider = provider_factory(configuration)
        elif configuration is not None:
            raise ContextCommandUsageError("lexical profile rejects semantic configuration")
        if not arguments.document:
            raise ContextCommandUsageError("at least one document is required")
        if arguments.budget is None:
            raise ContextCommandUsageError("a budget is required")
        request = ContextCompileRequest(
            task=task,
            document_ids=_document_ids(arguments.document),
            budget_limit=int(arguments.budget),
            estimator=estimator.identity,
            policy=ContextSelectionPolicy(
                mode=ContextMode(str(arguments.mode or "mixed")),
                maximum_sensitivity=Sensitivity.UNKNOWN,
            ),
        )
        persisted = compiler_factory(
            workspace,
            estimator,
            profile=profile,
            provider=provider,
        ).compile_and_persist(request)
        return context_summary(
            persisted.result,
            replayed=False,
            include_bundle=bool(arguments.include_bundle),
        )
    finally:
        if provider is not None:
            provider.close()


__all__ = [
    "ContextCommandUsageError",
    "compile_context_command",
    "context_summary",
    "estimator_for",
    "open_semantic_provider",
    "receipt_identity",
    "semantic_configuration",
]
