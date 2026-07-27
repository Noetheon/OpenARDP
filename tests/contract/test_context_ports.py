"""Structural contracts for provider-neutral F008 context boundaries."""

from __future__ import annotations

import inspect

from openardp.ports.catalog import (
    ContextCatalog,
    ContextCompilationConflict,
    ContextCompilationNotFound,
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
    RichContextCandidateSource,
    TextContextCandidateSource,
)


def test_context_ports_are_narrow_runtime_protocols() -> None:
    """Expose replaceable estimators and candidate sources without provider types."""
    assert ContextEstimator._is_runtime_protocol
    assert ContextCandidateSource._is_runtime_protocol
    assert TextContextCandidateSource._is_runtime_protocol
    assert RichContextCandidateSource._is_runtime_protocol
    assert set(inspect.signature(ContextEstimator.measure).parameters) == {"self", "payload"}
    assert isinstance(ContextEstimator.identity, property)
    assert set(inspect.signature(ContextCandidateSource.discover).parameters) == {
        "self",
        "task",
        "snapshot",
        "limits",
        "cancel",
    }


def test_context_candidate_sources_specialize_one_shared_port() -> None:
    """Keep text and rich discovery behind the same narrow verified boundary."""
    assert issubclass(TextContextCandidateSource, ContextCandidateSource)
    assert issubclass(RichContextCandidateSource, ContextCandidateSource)


def test_context_catalog_port_is_additive_and_atomic() -> None:
    """Extend persistence with compilation commit, load and list shapes only."""
    assert ContextCatalog._is_runtime_protocol
    assert set(inspect.signature(ContextCatalog.commit_context_compilation).parameters) == {
        "self",
        "commit",
    }
    assert set(inspect.signature(ContextCatalog.load_context_compilation).parameters) == {
        "self",
        "receipt_id",
    }
    assert set(inspect.signature(ContextCatalog.list_context_compilations).parameters) == {"self"}


def test_context_failures_are_sanitized_and_typed() -> None:
    """Provide stable categories without provider exceptions or sensitive fields."""
    errors = (
        ContextCompilationCancelled("cancelled"),
        ContextIntegrityFailure("index_incomplete"),
        ContextLimitExceeded("candidate_limit"),
        ContextConfigurationMismatch("estimator_mismatch"),
        ContextNotFound("compilation_missing"),
    )
    assert all(isinstance(error, ContextCompilationFailure) for error in errors)
    assert all("docling" not in type(error).__module__.casefold() for error in errors)
    assert CancellationCheck.__module__ == "openardp.ports.context"


def test_context_catalog_failures_stay_distinct_from_compiler_failures() -> None:
    """Keep persistence conflicts separate from sanitized compilation categories."""
    assert not issubclass(ContextCompilationConflict, ContextCompilationFailure)
    assert not issubclass(ContextCompilationNotFound, ContextCompilationFailure)
