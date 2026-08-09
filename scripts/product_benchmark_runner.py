"""Offline execution and evidence publication for the F020 maintainer benchmark."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
import time
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any, NoReturn, cast
from uuid import UUID

from pydantic import JsonValue

from openardp.adapters.context_candidates import TextLexicalCandidateSource
from openardp.adapters.context_estimators import Utf8ByteEstimator
from openardp.adapters.isolated_docling import IsolatedDoclingAdapter
from openardp.adapters.isolated_parser import IsolatedParserAdapter
from openardp.adapters.local_source import LocalSource
from openardp.adapters.local_workspace import LocalWorkspace
from openardp.adapters.product_benchmarks import (
    BenchmarkInputs,
    GeneratedCorpus,
    corpus_token,
    generate_text_corpus,
    load_benchmark_inputs,
)
from openardp.adapters.text_parser import TextParserAdapter
from openardp.domain.common import Sensitivity
from openardp.domain.context import ContextMode
from openardp.domain.context_compilation import ContextCompileRequest, ContextSelectionPolicy
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.ingestion import SourceFreshness, TextMediaType
from openardp.domain.product_benchmark import (
    BenchmarkMetric,
    BenchmarkObservation,
    BenchmarkPhase,
    BenchmarkProfile,
    BenchmarkTreatment,
    MetricSummary,
    ObservationStatus,
    ValueDecision,
    make_observation,
)
from openardp.domain.rich_ingestion import ModelBundleManifest, RichMediaType
from openardp.ports.context import ContextLimitExceeded
from openardp.ports.parser import ParserError, RichParserModelAssetsRequired
from openardp.services.context_compiler import (
    ContextCompilerService,
    bundle_object_bytes,
    receipt_object_bytes,
)
from openardp.services.document_query import DocumentQueryService
from openardp.services.ingestion import IngestionService
from openardp.services.release_benchmarks import environment_profile
from openardp.services.rich_evidence import RichEvidenceService
from openardp.services.rich_ingestion import RichIngestionService
from openardp.services.search import SearchService

_RUN_VERSION = "0.1.0"
_RESULT_NAMES = (
    "decision.json",
    "observations.json",
    "report.md",
    "run-manifest.json",
    "summary.json",
)


@dataclass(frozen=True, slots=True)
class _Timed:
    elapsed_ns: int
    cpu_ns: int
    value: object


@dataclass(frozen=True, slots=True)
class _TextServices:
    workspace: LocalWorkspace
    ingestion: IngestionService
    query: DocumentQueryService
    search: SearchService
    context: ContextCompilerService


@dataclass(frozen=True, slots=True)
class ProductBenchmarkResult:
    """Published result handles and the derived decision."""

    output: Path
    decision: ValueDecision
    observations: tuple[BenchmarkObservation, ...]
    summaries: tuple[MetricSummary, ...]


def _timed(operation: Callable[[], object]) -> _Timed:
    started = time.monotonic_ns()
    cpu_started = time.process_time_ns()
    value = operation()
    return _Timed(
        elapsed_ns=time.monotonic_ns() - started,
        cpu_ns=time.process_time_ns() - cpu_started,
        value=value,
    )


def _workspace_size(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            total += path.stat().st_size
    return total


def _peak_rss_bytes() -> int | None:
    """Return the portable process high-water RSS proxy when the host exposes it."""
    try:
        import resource

        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (ImportError, OSError, ValueError):
        return None
    if value < 0:
        return None
    return value if sys.platform == "darwin" else value * 1024


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _services(root: Path) -> _TextServices:
    workspace = LocalWorkspace.initialize(root, now=datetime.now(UTC))
    ingestion = IngestionService(
        workspace.object_store,
        workspace.catalog,
        IsolatedParserAdapter(),
        source_factory=LocalSource,
    )
    query = DocumentQueryService(
        workspace.object_store,
        workspace.catalog,
        source_factory=LocalSource,
        representation_verifier=ingestion.verify_ready_representation,
    )
    search = SearchService(
        workspace.object_store,
        workspace.catalog,
        source_factory=LocalSource,
    )
    context = ContextCompilerService(
        workspace.object_store,
        workspace.catalog,
        Utf8ByteEstimator(),
        (TextLexicalCandidateSource(workspace.object_store, workspace.catalog),),
    )
    return _TextServices(workspace, ingestion, query, search, context)


def _observation(
    inputs: BenchmarkInputs,
    environment_id: str,
    profile: BenchmarkProfile,
    workload_id: str,
    treatment: BenchmarkTreatment,
    phase: BenchmarkPhase,
    metric: BenchmarkMetric,
    repetition: int,
    value: int | float,
) -> BenchmarkObservation:
    return make_observation(
        protocol_id=inputs.protocol_id,
        corpus_id=inputs.corpus_id,
        policy_id=inputs.policy_id,
        environment_id=environment_id,
        profile=profile,
        workload_id=workload_id,
        treatment=treatment,
        phase=phase,
        metric=metric,
        unit=inputs.protocol.metrics[metric],
        repetition=repetition,
        value=value,
    )


def _unavailable(
    inputs: BenchmarkInputs,
    environment_id: str,
    profile: BenchmarkProfile,
    workload_id: str,
    treatment: BenchmarkTreatment,
    phase: BenchmarkPhase,
    metric: BenchmarkMetric,
    reason: str,
) -> BenchmarkObservation:
    return make_observation(
        protocol_id=inputs.protocol_id,
        corpus_id=inputs.corpus_id,
        policy_id=inputs.policy_id,
        environment_id=environment_id,
        profile=profile,
        workload_id=workload_id,
        treatment=treatment,
        phase=phase,
        metric=metric,
        unit=inputs.protocol.metrics[metric],
        repetition=0,
        status=ObservationStatus.UNAVAILABLE,
        reason_code=reason,
    )


def _append_timing(
    destination: list[BenchmarkObservation],
    inputs: BenchmarkInputs,
    environment_id: str,
    profile: BenchmarkProfile,
    workload_id: str,
    treatment: BenchmarkTreatment,
    phase: BenchmarkPhase,
    repetition: int,
    measured: _Timed,
) -> None:
    destination.extend(
        (
            _observation(
                inputs,
                environment_id,
                profile,
                workload_id,
                treatment,
                phase,
                BenchmarkMetric.LATENCY,
                repetition,
                measured.elapsed_ns,
            ),
            _observation(
                inputs,
                environment_id,
                profile,
                workload_id,
                treatment,
                phase,
                BenchmarkMetric.CPU_TIME,
                repetition,
                measured.cpu_ns,
            ),
        )
    )


def _raw_search(source_bytes: bytes, token: str) -> tuple[int, int | None]:
    parsed = TextParserAdapter().parse((source_bytes,), media_type=TextMediaType.PLAIN.value)
    matches = [block for block in parsed.blocks if token in block.text]
    return len(matches), matches[0].line_start if matches else None


def _native_search(path: Path, token: str) -> tuple[int, int | None]:
    raw = json.loads(path.read_bytes())
    if not isinstance(raw, list):
        raise ValueError("persisted native baseline is malformed")
    matches = [
        item
        for item in raw
        if isinstance(item, dict)
        and isinstance(item.get("text"), str)
        and token in cast(str, item["text"])
    ]
    line = matches[0].get("line_start") if matches else None
    return len(matches), line if isinstance(line, int) else None


def _correctness(
    *,
    match_count: int,
    line_start: int | None,
    expected_line: int,
) -> tuple[float, float, float, float]:
    correct = match_count == 1 and line_start == expected_line
    value = 1.0 if correct else 0.0
    return value, value, value, value


def _prepare_native(source_bytes: bytes, destination: Path) -> None:
    parsed = TextParserAdapter().parse((source_bytes,), media_type=TextMediaType.PLAIN.value)
    value = [
        {"line_start": item.line_start, "ordinal": index, "text": item.text}
        for index, item in enumerate(parsed.blocks)
    ]
    _atomic_write(destination, canonical_json_bytes(cast(JsonValue, value)))


def _run_search_treatment(
    observations: list[BenchmarkObservation],
    *,
    inputs: BenchmarkInputs,
    environment_id: str,
    corpus: GeneratedCorpus,
    treatment: BenchmarkTreatment,
    search: Callable[[str], tuple[int, int | None]],
) -> None:
    repetitions = inputs.protocol.repetitions
    warmups = inputs.protocol.warmup_repetitions
    for ordinal in inputs.corpus.profiles[corpus.profile].query_ordinals:
        token = corpus_token(inputs.corpus.seed, ordinal)
        workload = f"query-{corpus.profile.value}-{ordinal:06d}"
        for _ in range(warmups):
            search(token)
        last: tuple[int, int | None] = (0, None)
        for repetition in range(repetitions):
            measured = _timed(partial(search, token))
            last = cast(tuple[int, int | None], measured.value)
            _append_timing(
                observations,
                inputs,
                environment_id,
                corpus.profile,
                workload,
                treatment,
                BenchmarkPhase.SEARCH,
                repetition,
                measured,
            )
        precision, recall, reciprocal_rank, anchor = _correctness(
            match_count=last[0],
            line_start=last[1],
            expected_line=ordinal * 2 + 1,
        )
        for metric, value in (
            (BenchmarkMetric.PRECISION, precision),
            (BenchmarkMetric.RECALL, recall),
            (BenchmarkMetric.RECIPROCAL_RANK, reciprocal_rank),
            (BenchmarkMetric.ANCHOR_CORRECTNESS, anchor),
        ):
            observations.append(
                _observation(
                    inputs,
                    environment_id,
                    corpus.profile,
                    workload,
                    treatment,
                    BenchmarkPhase.SEARCH,
                    metric,
                    0,
                    value,
                )
            )


def _run_text_profile(
    inputs: BenchmarkInputs,
    environment_id: str,
    profile: BenchmarkProfile,
    root: Path,
) -> tuple[list[BenchmarkObservation], dict[str, JsonValue]]:
    corpus = generate_text_corpus(inputs, profile, root / "corpus")
    source_bytes = corpus.source.read_bytes()
    observations: list[BenchmarkObservation] = []
    facts: dict[str, JsonValue] = {
        "block_count": corpus.block_count,
        "source_bytes": corpus.source_bytes,
        "source_sha256": corpus.source_sha256,
    }
    observations.append(
        _observation(
            inputs,
            environment_id,
            profile,
            f"corpus-{profile.value}",
            BenchmarkTreatment.RAW_REPARSE,
            BenchmarkPhase.PREPARE,
            BenchmarkMetric.SOURCE_BYTES,
            0,
            corpus.source_bytes,
        )
    )
    raw_prepare = _timed(
        lambda: TextParserAdapter().parse((source_bytes,), media_type=TextMediaType.PLAIN.value)
    )
    _append_timing(
        observations,
        inputs,
        environment_id,
        profile,
        f"prepare-{profile.value}",
        BenchmarkTreatment.RAW_REPARSE,
        BenchmarkPhase.PREPARE,
        0,
        raw_prepare,
    )
    _run_search_treatment(
        observations,
        inputs=inputs,
        environment_id=environment_id,
        corpus=corpus,
        treatment=BenchmarkTreatment.RAW_REPARSE,
        search=lambda token: _raw_search(source_bytes, token),
    )

    native_path = root / "native.json"
    native_prepare = _timed(lambda: _prepare_native(source_bytes, native_path))
    _append_timing(
        observations,
        inputs,
        environment_id,
        profile,
        f"prepare-{profile.value}",
        BenchmarkTreatment.PERSISTED_NATIVE,
        BenchmarkPhase.PREPARE,
        0,
        native_prepare,
    )
    observations.append(
        _observation(
            inputs,
            environment_id,
            profile,
            f"native-{profile.value}",
            BenchmarkTreatment.PERSISTED_NATIVE,
            BenchmarkPhase.PREPARE,
            BenchmarkMetric.NATIVE_BYTES,
            0,
            native_path.stat().st_size,
        )
    )
    _run_search_treatment(
        observations,
        inputs=inputs,
        environment_id=environment_id,
        corpus=corpus,
        treatment=BenchmarkTreatment.PERSISTED_NATIVE,
        search=lambda token: _native_search(native_path, token),
    )

    services = _services(root / "workspace")
    open_prepare = _timed(lambda: services.ingestion.ingest(corpus.source))
    ingest_result = cast(Any, open_prepare.value)
    if ingest_result.block_count != corpus.block_count or not ingest_result.parser_invoked:
        raise ValueError("OpenARDP cold ingestion did not produce the exact corpus")
    _append_timing(
        observations,
        inputs,
        environment_id,
        profile,
        f"prepare-{profile.value}",
        BenchmarkTreatment.OPENARDP,
        BenchmarkPhase.PREPARE,
        0,
        open_prepare,
    )
    facts["openardp_prepare_ns"] = open_prepare.elapsed_ns
    facts["raw_prepare_ns"] = raw_prepare.elapsed_ns
    facts["native_prepare_ns"] = native_prepare.elapsed_ns

    def open_search(token: str) -> tuple[int, int | None]:
        result = services.search.search(f'"{token}"')
        return result.returned, result.hits[0].line_start if result.hits else None

    _run_search_treatment(
        observations,
        inputs=inputs,
        environment_id=environment_id,
        corpus=corpus,
        treatment=BenchmarkTreatment.OPENARDP,
        search=open_search,
    )

    for _ in range(inputs.protocol.warmup_repetitions):
        services.query.status(str(corpus.source))
        warmed = services.ingestion.ingest(corpus.source)
        if warmed.scope != ingest_result.scope or warmed.parser_invoked or not warmed.cache_hit:
            raise ValueError("text warm reuse was not identity-stable")
    parser_invocations = 0
    for repetition in range(inputs.protocol.repetitions):
        status_timing = _timed(lambda: services.query.status(str(corpus.source)))
        status = cast(Any, status_timing.value)
        if status.freshness is not SourceFreshness.CURRENT:
            raise ValueError("unchanged source status is not current")
        _append_timing(
            observations,
            inputs,
            environment_id,
            profile,
            f"status-{profile.value}",
            BenchmarkTreatment.OPENARDP,
            BenchmarkPhase.STATUS,
            repetition,
            status_timing,
        )
        reuse_timing = _timed(lambda: services.ingestion.ingest(corpus.source))
        reuse = cast(Any, reuse_timing.value)
        if reuse.scope != ingest_result.scope or not reuse.cache_hit:
            raise ValueError("unchanged text reuse was not identity-stable")
        parser_invocations += int(reuse.parser_invoked)
        _append_timing(
            observations,
            inputs,
            environment_id,
            profile,
            f"reingest-{profile.value}",
            BenchmarkTreatment.OPENARDP,
            BenchmarkPhase.REINGEST,
            repetition,
            reuse_timing,
        )
    observations.append(
        _observation(
            inputs,
            environment_id,
            profile,
            f"reingest-{profile.value}",
            BenchmarkTreatment.OPENARDP,
            BenchmarkPhase.REINGEST,
            BenchmarkMetric.PARSER_INVOCATIONS,
            0,
            parser_invocations,
        )
    )

    context_coverages: list[float] = []
    replay_matches: list[float] = []
    ratios: list[float] = []
    context_budget_status: dict[str, JsonValue] = {}
    context_ordinal = inputs.corpus.profiles[profile].query_ordinals[0]
    context_token = corpus_token(inputs.corpus.seed, context_ordinal)
    document_id = ingest_result.scope.document_id
    for budget in inputs.judgments.budgets:
        workload = f"context-{profile.value}-{budget}"
        request = ContextCompileRequest(
            task=context_token,
            document_ids=(document_id,),
            budget_limit=budget,
            estimator=Utf8ByteEstimator().identity,
            policy=ContextSelectionPolicy(
                mode=ContextMode.EXACT,
                maximum_sensitivity=Sensitivity.UNKNOWN,
            ),
        )
        try:
            for _ in range(inputs.protocol.warmup_repetitions):
                services.context.compile(request)
            persisted = None
            for repetition in range(inputs.protocol.repetitions):
                measured = _timed(partial(services.context.compile_and_persist, request))
                persisted = cast(Any, measured.value)
                _append_timing(
                    observations,
                    inputs,
                    environment_id,
                    profile,
                    workload,
                    BenchmarkTreatment.OPENARDP,
                    BenchmarkPhase.CONTEXT,
                    repetition,
                    measured,
                )
            if persisted is None:
                raise ValueError("context benchmark retained no sample")
            result = persisted.result
            body = bundle_object_bytes(result.bundle)
            selected = result.receipt.budget.selected_incremental_used
            coverage = float(context_token.encode() in body)
            context_coverages.append(coverage)
            ratio = selected / corpus.source_bytes
            ratios.append(ratio)
            observations.extend(
                (
                    _observation(
                        inputs,
                        environment_id,
                        profile,
                        workload,
                        BenchmarkTreatment.OPENARDP,
                        BenchmarkPhase.CONTEXT,
                        BenchmarkMetric.SELECTED_BYTES,
                        0,
                        selected,
                    ),
                    _observation(
                        inputs,
                        environment_id,
                        profile,
                        workload,
                        BenchmarkTreatment.OPENARDP,
                        BenchmarkPhase.CONTEXT,
                        BenchmarkMetric.CONTEXT_COVERAGE,
                        0,
                        coverage,
                    ),
                )
            )
            for repetition in range(inputs.protocol.repetitions):
                replay = _timed(
                    partial(
                        services.context.replay,
                        context_token,
                        persisted.record.receipt_id,
                    )
                )
                replay_result = cast(Any, replay.value)
                identical = float(
                    bundle_object_bytes(replay_result.bundle) == bundle_object_bytes(result.bundle)
                    and receipt_object_bytes(replay_result.receipt)
                    == receipt_object_bytes(result.receipt)
                )
                replay_matches.append(identical)
                _append_timing(
                    observations,
                    inputs,
                    environment_id,
                    profile,
                    workload,
                    BenchmarkTreatment.OPENARDP,
                    BenchmarkPhase.REPLAY,
                    repetition,
                    replay,
                )
            observations.append(
                _observation(
                    inputs,
                    environment_id,
                    profile,
                    workload,
                    BenchmarkTreatment.OPENARDP,
                    BenchmarkPhase.REPLAY,
                    BenchmarkMetric.REPLAY_MATCH,
                    0,
                    min(replay_matches[-inputs.protocol.repetitions :]),
                )
            )
            context_budget_status[str(budget)] = "passed"
        except ContextLimitExceeded:
            context_budget_status[str(budget)] = "base-bundle-exceeds-budget"
            for phase, metric in (
                (BenchmarkPhase.CONTEXT, BenchmarkMetric.LATENCY),
                (BenchmarkPhase.REPLAY, BenchmarkMetric.LATENCY),
            ):
                observations.append(
                    _unavailable(
                        inputs,
                        environment_id,
                        profile,
                        workload,
                        BenchmarkTreatment.OPENARDP,
                        phase,
                        metric,
                        "context-budget-insufficient",
                    )
                )

    # A guarded current-only workflow checks freshness before retrieval. The raw
    # search service intentionally remains a catalog query over the last ingested head.
    edit_ordinal = inputs.corpus.profiles[profile].query_ordinals[-1]
    old_token = corpus_token(inputs.corpus.seed, edit_ordinal)
    new_token = f"replacement-{hashlib.sha256(old_token.encode()).hexdigest()[:16]}"
    corpus.source.write_bytes(source_bytes.replace(old_token.encode(), new_token.encode(), 1))
    changed = services.query.status(str(corpus.source))
    stale_incidents = int(changed.freshness is not SourceFreshness.SOURCE_CHANGED)
    changed_ingest = services.ingestion.ingest(corpus.source)
    old_after = open_search(old_token)
    new_after = open_search(new_token)
    historical = services.search.search(f'"{old_token}"', include_history=True)
    edit_correct = (
        changed_ingest.parser_invoked
        and changed_ingest.scope.version_id != ingest_result.scope.version_id
        and old_after[0] == 0
        and new_after[0] == 1
        and any(hit.scope.version_id == ingest_result.scope.version_id for hit in historical.hits)
    )
    stale_incidents += int(not edit_correct)
    corpus.source.write_bytes(source_bytes)
    reverted_status = services.query.status(str(corpus.source))
    reverted = services.ingestion.ingest(corpus.source)
    old_restored = open_search(old_token)
    new_historical = services.search.search(f'"{new_token}"', include_history=True)
    new_current = open_search(new_token)
    revert_correct = (
        reverted_status.freshness is SourceFreshness.SOURCE_CHANGED
        and reverted.scope == ingest_result.scope
        and reverted.cache_hit
        and not reverted.parser_invoked
        and old_restored[0] == 1
        and new_current[0] == 0
        and any(
            hit.scope.version_id == changed_ingest.scope.version_id for hit in new_historical.hits
        )
    )
    stale_incidents += int(not revert_correct)
    observations.append(
        _observation(
            inputs,
            environment_id,
            profile,
            f"edit-{profile.value}",
            BenchmarkTreatment.OPENARDP,
            BenchmarkPhase.EDIT,
            BenchmarkMetric.STALE_INCIDENTS,
            0,
            stale_incidents,
        )
    )
    workspace_bytes = _workspace_size(services.workspace.root)
    observations.append(
        _observation(
            inputs,
            environment_id,
            profile,
            f"workspace-{profile.value}",
            BenchmarkTreatment.OPENARDP,
            BenchmarkPhase.PREPARE,
            BenchmarkMetric.WORKSPACE_BYTES,
            0,
            workspace_bytes,
        )
    )
    peak_rss = _peak_rss_bytes()
    if peak_rss is not None:
        observations.append(
            _observation(
                inputs,
                environment_id,
                profile,
                f"resource-{profile.value}",
                BenchmarkTreatment.OPENARDP,
                BenchmarkPhase.PREPARE,
                BenchmarkMetric.PEAK_RSS,
                0,
                peak_rss,
            )
        )
    facts["context_coverage"] = min(context_coverages) if context_coverages else 0.0
    facts["replay_match"] = min(replay_matches) if replay_matches else 0.0
    facts["context_selected_native_ratio"] = max(ratios) if ratios else None
    facts["context_budgets"] = context_budget_status
    facts["context_budgets_complete"] = all(
        value == "passed" for value in context_budget_status.values()
    )
    facts["stale_incidents"] = stale_incidents
    facts["unchanged_parser_invocations"] = parser_invocations
    facts["workspace_bytes"] = workspace_bytes
    return observations, facts


def _rich_terms(output: object) -> str:
    return canonical_json_bytes(cast(Any, output)).decode("utf-8", errors="replace")


def _load_native_json(path: Path) -> object:
    return json.loads(path.read_bytes())


def _retrieve_rich_evidence(
    evidence: RichEvidenceService,
    document_id: UUID,
) -> list[str]:
    projections = evidence.list(document_id)
    return [evidence.get(item.evidence_projection_id).body for item in projections]


def _median_ns(values: Sequence[int]) -> int:
    if not values:
        raise ValueError("median requires values")
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) // 2


def _preflight_rich(
    repository_root: Path,
    inputs: BenchmarkInputs,
    *,
    model_root: Path | None,
    model_manifest: ModelBundleManifest | None,
) -> dict[str, IsolatedDoclingAdapter]:
    """Validate rich fixtures and bind provider authority before costly phases."""
    parsers = {
        "docx": IsolatedDoclingAdapter(),
        "pdf": IsolatedDoclingAdapter(
            model_root=model_root,
            model_manifest=model_manifest,
        ),
        "pptx": IsolatedDoclingAdapter(),
    }
    for fixture in inputs.corpus.rich_fixtures:
        if fixture.format not in parsers:
            raise ValueError("unsupported rich fixture format")
        source_bytes = (repository_root / fixture.path).read_bytes()
        digest = "sha256:" + hashlib.sha256(source_bytes).hexdigest()
        if digest != fixture.sha256:
            raise ValueError("rich fixture digest mismatch")
    return parsers


def _run_rich(
    repository_root: Path,
    inputs: BenchmarkInputs,
    environment_id: str,
    root: Path,
    *,
    parsers: Mapping[str, IsolatedDoclingAdapter],
) -> tuple[list[BenchmarkObservation], tuple[str, ...], dict[str, JsonValue]]:
    observations: list[BenchmarkObservation] = []
    available: list[str] = []
    details: dict[str, JsonValue] = {}
    repetitions = inputs.protocol.repetitions
    warmups = inputs.protocol.warmup_repetitions
    for fixture in inputs.corpus.rich_fixtures:
        source = repository_root / fixture.path
        source_bytes = source.read_bytes()
        digest = "sha256:" + hashlib.sha256(source_bytes).hexdigest()
        if digest != fixture.sha256:
            raise ValueError("rich fixture digest mismatch")
        workload = f"rich-{fixture.format}"
        parser = parsers[fixture.format]
        media_type = {
            "docx": RichMediaType.DOCX.value,
            "pdf": RichMediaType.PDF.value,
            "pptx": RichMediaType.PPTX.value,
        }[fixture.format]
        try:
            for _ in range(warmups):
                parser.parse((source_bytes,), media_type=media_type)
            raw_samples: list[int] = []
            output = None
            for repetition in range(repetitions):
                raw = _timed(partial(parser.parse, (source_bytes,), media_type=media_type))
                output = cast(Any, raw.value)
                raw_samples.append(raw.elapsed_ns)
                _append_timing(
                    observations,
                    inputs,
                    environment_id,
                    BenchmarkProfile.FULL,
                    workload,
                    BenchmarkTreatment.RAW_REPARSE,
                    BenchmarkPhase.PREPARE,
                    repetition,
                    raw,
                )
            if output is None:
                raise ValueError("rich raw treatment retained no sample")
            expected = inputs.judgments.rich_expected_terms[fixture.format]
            raw_text = _rich_terms(output.model_dump(mode="json"))
            raw_correct = all(term in raw_text for term in expected)
            native = root / f"{fixture.format}-native.json"
            _atomic_write(native, output.canonical_native_bytes)
            for _ in range(warmups):
                _load_native_json(native)
            native_samples: list[int] = []
            native_value: object = {}
            for repetition in range(repetitions):
                loaded = _timed(partial(_load_native_json, native))
                native_value = loaded.value
                native_samples.append(loaded.elapsed_ns)
                _append_timing(
                    observations,
                    inputs,
                    environment_id,
                    BenchmarkProfile.FULL,
                    workload,
                    BenchmarkTreatment.PERSISTED_NATIVE,
                    BenchmarkPhase.NATIVE_LOAD,
                    repetition,
                    loaded,
                )
            native_correct = all(term in _rich_terms(native_value) for term in expected)
            for treatment, correct in (
                (BenchmarkTreatment.RAW_REPARSE, raw_correct),
                (BenchmarkTreatment.PERSISTED_NATIVE, native_correct),
            ):
                observations.append(
                    _observation(
                        inputs,
                        environment_id,
                        BenchmarkProfile.FULL,
                        workload,
                        treatment,
                        BenchmarkPhase.EVIDENCE,
                        BenchmarkMetric.ANCHOR_CORRECTNESS,
                        0,
                        float(correct),
                    )
                )
            observations.extend(
                (
                    _observation(
                        inputs,
                        environment_id,
                        BenchmarkProfile.FULL,
                        workload,
                        BenchmarkTreatment.RAW_REPARSE,
                        BenchmarkPhase.PREPARE,
                        BenchmarkMetric.SOURCE_BYTES,
                        0,
                        len(source_bytes),
                    ),
                    _observation(
                        inputs,
                        environment_id,
                        BenchmarkProfile.FULL,
                        workload,
                        BenchmarkTreatment.PERSISTED_NATIVE,
                        BenchmarkPhase.NATIVE_LOAD,
                        BenchmarkMetric.NATIVE_BYTES,
                        0,
                        native.stat().st_size,
                    ),
                )
            )

            workspace = LocalWorkspace.initialize(
                root / f"{fixture.format}-workspace", now=datetime.now(UTC)
            )
            ingestion = RichIngestionService(
                workspace.object_store,
                workspace.catalog,
                parser,
                source_factory=LocalSource,
            )
            evidence = RichEvidenceService(
                workspace.object_store,
                workspace.catalog,
                representation_verifier=ingestion.verify_ready_representation,
            )
            prepared = _timed(partial(ingestion.ingest, source))
            ingested = cast(Any, prepared.value)
            _append_timing(
                observations,
                inputs,
                environment_id,
                BenchmarkProfile.FULL,
                workload,
                BenchmarkTreatment.OPENARDP,
                BenchmarkPhase.PREPARE,
                0,
                prepared,
            )
            for _ in range(warmups):
                warmed = ingestion.ingest(source)
                if warmed.parser_invoked or warmed.scope != ingested.scope:
                    raise ValueError("rich warm reuse was not identity-stable")
            parser_calls = 0
            reuse_samples: list[int] = []
            for repetition in range(inputs.protocol.repetitions):
                reused = _timed(partial(ingestion.ingest, source))
                result = cast(Any, reused.value)
                parser_calls += int(result.parser_invoked)
                if result.scope != ingested.scope or not result.cache_hit:
                    raise ValueError("rich reuse was not identity-stable")
                reuse_samples.append(reused.elapsed_ns)
                _append_timing(
                    observations,
                    inputs,
                    environment_id,
                    BenchmarkProfile.FULL,
                    workload,
                    BenchmarkTreatment.OPENARDP,
                    BenchmarkPhase.REINGEST,
                    repetition,
                    reused,
                )

            for _ in range(warmups):
                _retrieve_rich_evidence(evidence, ingested.scope.document_id)
            evidence_samples: list[int] = []
            bodies: list[str] = []
            for repetition in range(repetitions):
                retrieved = _timed(
                    partial(_retrieve_rich_evidence, evidence, ingested.scope.document_id)
                )
                bodies = cast(list[str], retrieved.value)
                evidence_samples.append(retrieved.elapsed_ns)
                _append_timing(
                    observations,
                    inputs,
                    environment_id,
                    BenchmarkProfile.FULL,
                    workload,
                    BenchmarkTreatment.OPENARDP,
                    BenchmarkPhase.EVIDENCE,
                    repetition,
                    retrieved,
                )
            correct = all(any(term in body for body in bodies) for term in expected)
            workspace_bytes = _workspace_size(workspace.root)
            observations.extend(
                (
                    _observation(
                        inputs,
                        environment_id,
                        BenchmarkProfile.FULL,
                        workload,
                        BenchmarkTreatment.OPENARDP,
                        BenchmarkPhase.REINGEST,
                        BenchmarkMetric.PARSER_INVOCATIONS,
                        0,
                        parser_calls,
                    ),
                    _observation(
                        inputs,
                        environment_id,
                        BenchmarkProfile.FULL,
                        workload,
                        BenchmarkTreatment.OPENARDP,
                        BenchmarkPhase.EVIDENCE,
                        BenchmarkMetric.ANCHOR_CORRECTNESS,
                        0,
                        float(correct),
                    ),
                    _observation(
                        inputs,
                        environment_id,
                        BenchmarkProfile.FULL,
                        workload,
                        BenchmarkTreatment.OPENARDP,
                        BenchmarkPhase.PREPARE,
                        BenchmarkMetric.WORKSPACE_BYTES,
                        0,
                        workspace_bytes,
                    ),
                )
            )
            complete_correct = raw_correct and native_correct and correct and parser_calls == 0
            if complete_correct:
                available.append(fixture.format)
            raw_median = _median_ns(raw_samples)
            native_median = _median_ns(native_samples)
            reuse_median = _median_ns(reuse_samples)
            break_even_raw = (
                max(1, math.ceil(prepared.elapsed_ns / (raw_median - reuse_median)))
                if raw_median > reuse_median
                else None
            )
            break_even_native = (
                max(1, math.ceil(prepared.elapsed_ns / (native_median - reuse_median)))
                if native_median > reuse_median
                else None
            )
            details[fixture.format] = {
                "available": complete_correct,
                "break_even_vs_persisted_native": break_even_native,
                "break_even_vs_raw_reparse": break_even_raw,
                "evidence_count": ingested.evidence_count,
                "evidence_p50_ns": _median_ns(evidence_samples),
                "native_bytes": len(output.canonical_native_bytes),
                "native_load_p50_ns": native_median,
                "openardp_prepare_ns": prepared.elapsed_ns,
                "openardp_reuse_p50_ns": reuse_median,
                "parser_invocations_on_reuse": parser_calls,
                "raw_reparse_p50_ns": raw_median,
                "source_bytes": len(source_bytes),
                "workspace_bytes": workspace_bytes,
            }
        except RichParserModelAssetsRequired:
            for treatment, phase in (
                (BenchmarkTreatment.RAW_REPARSE, BenchmarkPhase.PREPARE),
                (BenchmarkTreatment.PERSISTED_NATIVE, BenchmarkPhase.NATIVE_LOAD),
                (BenchmarkTreatment.OPENARDP, BenchmarkPhase.PREPARE),
            ):
                observations.append(
                    _unavailable(
                        inputs,
                        environment_id,
                        BenchmarkProfile.FULL,
                        workload,
                        treatment,
                        phase,
                        BenchmarkMetric.LATENCY,
                        "pdf-model-bundle-unavailable",
                    )
                )
            details[fixture.format] = {
                "available": False,
                "reason_code": "pdf-model-bundle-unavailable",
            }
        except ParserError:
            for treatment, phase in (
                (BenchmarkTreatment.RAW_REPARSE, BenchmarkPhase.PREPARE),
                (BenchmarkTreatment.PERSISTED_NATIVE, BenchmarkPhase.NATIVE_LOAD),
                (BenchmarkTreatment.OPENARDP, BenchmarkPhase.PREPARE),
            ):
                observations.append(
                    _unavailable(
                        inputs,
                        environment_id,
                        BenchmarkProfile.FULL,
                        workload,
                        treatment,
                        phase,
                        BenchmarkMetric.LATENCY,
                        "rich-parser-unavailable",
                    )
                )
            details[fixture.format] = {
                "available": False,
                "reason_code": "rich-parser-unavailable",
            }
    peak_rss = _peak_rss_bytes()
    if peak_rss is not None:
        observations.append(
            _observation(
                inputs,
                environment_id,
                BenchmarkProfile.FULL,
                "resource-rich",
                BenchmarkTreatment.OPENARDP,
                BenchmarkPhase.PREPARE,
                BenchmarkMetric.PEAK_RSS,
                0,
                peak_rss,
            )
        )
    return observations, tuple(sorted(available)), details


def _summaries(
    inputs: BenchmarkInputs,
    observations: Sequence[BenchmarkObservation],
) -> tuple[MetricSummary, ...]:
    grouped: defaultdict[tuple[object, ...], list[BenchmarkObservation]] = defaultdict(list)
    for item in observations:
        if (
            item.metric in {BenchmarkMetric.LATENCY, BenchmarkMetric.CPU_TIME}
            and item.status is ObservationStatus.PASSED
        ):
            grouped[
                (
                    item.profile,
                    item.workload_id,
                    item.treatment,
                    item.phase,
                    item.metric,
                )
            ].append(item)
    summaries = []
    for values in grouped.values():
        if len(values) >= inputs.policy.sample_policy.minimum_timing_samples:
            try:
                from scripts.product_benchmark_evaluation import summarize_timing
            except ModuleNotFoundError:
                from product_benchmark_evaluation import summarize_timing

            summaries.append(
                summarize_timing(
                    values,
                    minimum_samples=inputs.policy.sample_policy.minimum_timing_samples,
                    bootstrap_resamples=inputs.protocol.bootstrap_resamples,
                )
            )
    return tuple(
        sorted(
            summaries,
            key=lambda item: (
                item.profile.value,
                item.workload_id,
                item.treatment.value,
                item.phase.value,
                item.metric.value,
            ),
        )
    )


def _minimum_ratio(observations: Sequence[BenchmarkObservation], metric: BenchmarkMetric) -> float:
    values = [
        float(item.value)
        for item in observations
        if item.metric is metric
        and item.status is ObservationStatus.PASSED
        and item.value is not None
    ]
    return min(values) if values else 0.0


def _sum_metric(observations: Sequence[BenchmarkObservation], metric: BenchmarkMetric) -> int:
    return sum(
        int(item.value)
        for item in observations
        if item.metric is metric
        and item.status is ObservationStatus.PASSED
        and item.value is not None
    )


def _summary_p95(
    summaries: Sequence[MetricSummary],
    *,
    profile: BenchmarkProfile,
    phase: BenchmarkPhase,
) -> int | None:
    values = [
        item.p95
        for item in summaries
        if item.profile is profile
        and item.phase is phase
        and item.treatment is BenchmarkTreatment.OPENARDP
        and item.metric is BenchmarkMetric.LATENCY
    ]
    return max(values) if values else None


def _search_p50(
    summaries: Sequence[MetricSummary],
    *,
    profile: BenchmarkProfile,
    treatment: BenchmarkTreatment,
) -> int | None:
    values = [
        item.p50
        for item in summaries
        if item.profile is profile
        and item.phase is BenchmarkPhase.SEARCH
        and item.treatment is treatment
        and item.metric is BenchmarkMetric.LATENCY
    ]
    return max(values) if values else None


def _break_even(facts: dict[str, JsonValue], summaries: Sequence[MetricSummary]) -> int | None:
    raw = _search_p50(
        summaries,
        profile=BenchmarkProfile.REFERENCE,
        treatment=BenchmarkTreatment.RAW_REPARSE,
    )
    openardp = _search_p50(
        summaries,
        profile=BenchmarkProfile.REFERENCE,
        treatment=BenchmarkTreatment.OPENARDP,
    )
    preparation = facts.get("openardp_prepare_ns")
    if raw is None or openardp is None or not isinstance(preparation, int) or raw <= openardp:
        return None
    return max(1, math.ceil(preparation / (raw - openardp)))


def _fact_number(facts: dict[str, JsonValue], key: str, default: float = 0.0) -> float:
    value = facts.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return float(value)


def _fact_int(facts: dict[str, JsonValue], key: str) -> int:
    value = facts.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value


def _timing_cell(facts: dict[str, JsonValue], key: str) -> str:
    value = facts.get(key)
    return f"{value / 1_000_000:.3f}" if isinstance(value, int) else "-"


def _manifest_entry(path: Path) -> dict[str, JsonValue]:
    data = path.read_bytes()
    return {
        "byte_length": len(data),
        "name": path.name,
        "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
    }


def _unique_pairs(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
    value: dict[str, JsonValue] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate benchmark JSON member")
        value[key] = item
    return value


def _reject_constant(_value: str) -> NoReturn:
    raise ValueError("non-finite benchmark JSON number")


def _load_result_json(path: Path, *, maximum_bytes: int) -> JsonValue:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise ValueError("benchmark result file is unsafe")
    data = path.read_bytes()
    try:
        value = cast(
            JsonValue,
            json.loads(
                data,
                object_pairs_hook=_unique_pairs,
                parse_constant=_reject_constant,
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("benchmark result JSON is malformed") from error
    if data != canonical_json_bytes(value) + b"\n":
        raise ValueError("benchmark result JSON is not canonical")
    return value


def _render_report(summary: dict[str, JsonValue], decision: ValueDecision) -> str:
    raw_metrics = summary["decision_metrics"]
    raw_facts = summary["profile_facts"]
    raw_rich = summary["rich"]
    raw_summaries = summary["summaries"]
    if (
        not isinstance(raw_metrics, dict)
        or not isinstance(raw_facts, dict)
        or not isinstance(raw_rich, dict)
        or not isinstance(raw_summaries, list)
    ):
        raise ValueError("benchmark report input is malformed")
    metrics = raw_metrics
    lines = [
        "# OpenARDP product-value benchmark",
        "",
        f"**Outcome:** `{decision.outcome.value}`",
        "",
        "This result is workload-bounded and does not replace the inherited "
        "F015 release `NO-GO` decision.",
        "",
        "## Decision metrics",
        "",
        "| Metric | Observed |",
        "|---|---:|",
    ]
    for key in sorted(metrics):
        lines.append(f"| `{key}` | `{metrics[key]}` |")
    lines.extend(("", "## Decision reasons", ""))
    if decision.reason_codes:
        lines.extend(f"- `{item}`" for item in decision.reason_codes)
    else:
        lines.append("- None")
    lines.extend(
        (
            "",
            "## Observed workload facts",
            "",
            "| Profile | Blocks | Source MiB | Workspace MiB | Context budgets |",
            "|---|---:|---:|---:|---|",
        )
    )
    for profile_name in sorted(raw_facts):
        value = raw_facts[profile_name]
        if not isinstance(value, dict):
            raise ValueError("benchmark report profile facts are malformed")
        budgets = value.get("context_budgets", {})
        budget_text = (
            ", ".join(f"{key}: {item}" for key, item in budgets.items())
            if isinstance(budgets, dict)
            else "invalid"
        )
        lines.append(
            "| "
            f"`{profile_name}` | {_fact_int(value, 'block_count'):,} | "
            f"{_fact_number(value, 'source_bytes') / 1_048_576:.2f} | "
            f"{_fact_number(value, 'workspace_bytes') / 1_048_576:.2f} | "
            f"{budget_text} |"
        )

    lines.extend(
        (
            "",
            "## Retained timing summaries",
            "",
            "Wall-clock values are milliseconds. Each row below has seven retained samples; "
            "cold preparation and the process high-water RSS proxy are retained separately "
            "as one-time observations.",
            "",
            "| Profile | Workload | Treatment | Phase | p50 ms | p95 ms | MAD ms |",
            "|---|---|---|---|---:|---:|---:|",
        )
    )
    for raw in raw_summaries:
        if not isinstance(raw, dict) or raw.get("metric") != BenchmarkMetric.LATENCY.value:
            continue
        p50 = raw.get("p50")
        p95 = raw.get("p95")
        mad = raw.get("median_absolute_deviation")
        if not all(isinstance(item, int) for item in (p50, p95, mad)):
            raise ValueError("benchmark report timing summary is malformed")
        lines.append(
            f"| `{raw.get('profile')}` | `{raw.get('workload_id')}` | "
            f"`{raw.get('treatment')}` | `{raw.get('phase')}` | "
            f"{cast(int, p50) / 1_000_000:.3f} | {cast(int, p95) / 1_000_000:.3f} | "
            f"{cast(int, mad) / 1_000_000:.3f} |"
        )

    lines.extend(("", "## Comparative findings", ""))
    for profile_name in ("reference", "scale"):
        search_by_treatment: dict[str, list[int]] = defaultdict(list)
        for raw in raw_summaries:
            if (
                isinstance(raw, dict)
                and raw.get("profile") == profile_name
                and raw.get("phase") == BenchmarkPhase.SEARCH.value
                and raw.get("metric") == BenchmarkMetric.LATENCY.value
                and isinstance(raw.get("treatment"), str)
                and isinstance(raw.get("p50"), int)
            ):
                search_by_treatment[cast(str, raw["treatment"])].append(cast(int, raw["p50"]))
        if set(search_by_treatment) == {item.value for item in BenchmarkTreatment}:
            raw_p50 = max(search_by_treatment[BenchmarkTreatment.RAW_REPARSE.value])
            native_p50 = max(search_by_treatment[BenchmarkTreatment.PERSISTED_NATIVE.value])
            open_p50 = max(search_by_treatment[BenchmarkTreatment.OPENARDP.value])
            lines.append(
                f"- `{profile_name}` worst-query p50: raw reparse {raw_p50 / 1e6:.3f} ms, "
                f"persisted native {native_p50 / 1e6:.3f} ms, OpenARDP {open_p50 / 1e6:.3f} ms. "
                f"OpenARDP is {raw_p50 / max(open_p50, 1):.1f}x faster than raw reparse "
                f"and {open_p50 / max(native_p50, 1):.1f}x the persisted-native latency."
            )
    for profile_name in sorted(raw_facts):
        value = raw_facts[profile_name]
        if isinstance(value, dict):
            source_size = _fact_number(value, "source_bytes")
            workspace_size = _fact_number(value, "workspace_bytes")
            if source_size > 0:
                lines.append(
                    f"- `{profile_name}` workspace amplification: "
                    f"{workspace_size / source_size:.1f}x source bytes."
                )
    lines.append(
        "- Rich persisted-native loading is the lower-bound latency baseline; a null "
        "break-even against it means verified OpenARDP reuse did not become faster in the "
        "declared horizon."
    )

    lines.extend(("", "## Rich-document capability", ""))
    lines.extend(
        (
            "| Format | Available | Evidence | Raw p50 ms | Native p50 ms | "
            "OpenARDP reuse p50 ms | Break-even vs raw/native | Limitation |",
            "|---|---|---:|---:|---:|---:|---|---|",
        )
    )
    for format_name in sorted(raw_rich):
        value = raw_rich[format_name]
        if not isinstance(value, dict):
            raise ValueError("benchmark report rich facts are malformed")

        lines.append(
            f"| `{format_name}` | `{value.get('available')}` | "
            f"{value.get('evidence_count', '-')} | {_timing_cell(value, 'raw_reparse_p50_ns')} | "
            f"{_timing_cell(value, 'native_load_p50_ns')} | "
            f"{_timing_cell(value, 'openardp_reuse_p50_ns')} | "
            f"{value.get('break_even_vs_raw_reparse', '-')} / "
            f"{value.get('break_even_vs_persisted_native', '-')} | "
            f"`{value.get('reason_code', 'none')}` |"
        )

    lines.extend(("", "## Policy checks", ""))
    lines.extend(("| Check | Status | Expected | Observed |", "|---|---|---:|---:|"))
    for check in decision.checks:
        lines.append(
            f"| `{check.check_id}` | `{check.status.value}` | `{check.expected}` | "
            f"`{check.observed}` |"
        )

    lines.extend(
        (
            "",
            "## Interpretation",
            "",
            "Observed facts: exact search and source anchors, changed-source replacement, "
            "unchanged parser avoidance, context coverage for budgets that can hold the safe "
            "envelope, receipt replay, storage and local timings come directly from the raw "
            "observations.",
            "",
            "Observed disadvantages: the preparation and workspace figures expose OpenARDP's "
            "one-time persistence cost; failed latency and completeness checks above remain "
            "visible. Insufficient context budgets and unavailable rich formats are not treated "
            "as successful measurements.",
            "",
            "Policy-derived conclusion: break-even is calculated only for the measured repeated "
            "exact-lookup workload. It is not a forecast for semantic question answering or an "
            "arbitrary production corpus.",
            "",
            "Untested conditions include private or adversarial real-world corpora, external "
            "model answer quality, PDF conversion without the required offline assets, other "
            "hardware classes and concurrent multi-user operation.",
            "",
            "The raw-reparse baseline reparses the exact source for every lookup. The "
            "persisted-native baseline loads a canonical parsed JSON snapshot for every lookup. "
            "OpenARDP uses its production isolated parser, content-addressed store, SQLite "
            "catalog, FTS search, freshness status, context receipts and replay.",
            "",
            "No external model or network evaluator is used. Source bodies, task text, "
            "hostnames, usernames, credentials and absolute paths are not recorded.",
            "",
        )
    )
    return "\n".join(lines)


def _derive_decision_metrics(
    *,
    profile: BenchmarkProfile,
    profile_facts: dict[str, dict[str, JsonValue]],
    rich_formats: Sequence[str],
    observations: Sequence[BenchmarkObservation],
    summaries: Sequence[MetricSummary],
) -> dict[str, object]:
    reference = profile_facts.get("reference", {})
    scale = profile_facts.get("scale", {})
    return {
        "anchor_correctness": _minimum_ratio(observations, BenchmarkMetric.ANCHOR_CORRECTNESS),
        "context_coverage": min(
            (_fact_number(value, "context_coverage") for value in profile_facts.values()),
            default=0.0,
        ),
        "precision": _minimum_ratio(observations, BenchmarkMetric.PRECISION),
        "recall": _minimum_ratio(observations, BenchmarkMetric.RECALL),
        "replay_match": min(
            (_fact_number(value, "replay_match") for value in profile_facts.values()),
            default=0.0,
        ),
        "stale_incidents": _sum_metric(observations, BenchmarkMetric.STALE_INCIDENTS),
        "unchanged_parser_invocations": _sum_metric(
            observations, BenchmarkMetric.PARSER_INVOCATIONS
        ),
        "reference_blocks": _fact_int(reference, "block_count"),
        "scale_blocks": _fact_int(scale, "block_count"),
        "search_p95_ns_at_100k": _summary_p95(
            summaries,
            profile=BenchmarkProfile.SCALE,
            phase=BenchmarkPhase.SEARCH,
        ),
        "status_p95_ns": _summary_p95(
            summaries,
            profile=(BenchmarkProfile.REFERENCE if reference else BenchmarkProfile.SMOKE),
            phase=BenchmarkPhase.STATUS,
        ),
        "context_selected_native_ratio": max(
            (
                _fact_number(value, "context_selected_native_ratio")
                for value in profile_facts.values()
                if value.get("context_selected_native_ratio") is not None
            ),
            default=None,
        ),
        "break_even": _break_even(reference, summaries),
        "rich_formats": list(sorted(set(rich_formats))),
        "complete": (
            profile is BenchmarkProfile.FULL
            and len(set(rich_formats)) == 3
            and all(
                value.get("context_budgets_complete") is True for value in profile_facts.values()
            )
        ),
    }


def execute_product_benchmark(
    repository_root: Path,
    *,
    profile: BenchmarkProfile,
    output: Path,
    model_root: Path | None = None,
    model_manifest: ModelBundleManifest | None = None,
) -> ProductBenchmarkResult:
    """Execute a fresh bounded offline run and atomically publish its evidence."""
    root = repository_root.resolve(strict=True)
    inputs = load_benchmark_inputs(root / "benchmarks/product-value/v0.1.0")
    if output.exists():
        raise FileExistsError("benchmark output already exists")
    rich_parsers: Mapping[str, IsolatedDoclingAdapter] | None = None
    if profile in {BenchmarkProfile.REFERENCE, BenchmarkProfile.FULL}:
        rich_parsers = _preflight_rich(
            root,
            inputs,
            model_root=model_root,
            model_manifest=model_manifest,
        )
    environment = environment_profile(reference_timing=True)
    environment_value = environment.model_dump(mode="json")
    environment_id = canonical_sha256(environment_value)
    run_parent = output.parent
    run_parent.mkdir(parents=True, exist_ok=True)
    # LocalSource deliberately rejects hidden path components, so the isolated
    # staging root must be visible even though it is atomically renamed at publish.
    temporary = Path(tempfile.mkdtemp(prefix=f"{output.name}-stage-", dir=run_parent))
    work = Path(tempfile.mkdtemp(prefix="f020-work-", dir=run_parent))
    started_ns = time.monotonic_ns()
    observations: list[BenchmarkObservation] = []
    profile_facts: dict[str, dict[str, JsonValue]] = {}
    selected_profiles = {
        BenchmarkProfile.SMOKE: (BenchmarkProfile.SMOKE,),
        BenchmarkProfile.REFERENCE: (BenchmarkProfile.REFERENCE,),
        BenchmarkProfile.SCALE: (BenchmarkProfile.SCALE,),
        BenchmarkProfile.FULL: (BenchmarkProfile.REFERENCE, BenchmarkProfile.SCALE),
    }[profile]
    try:
        for selected in selected_profiles:
            observed, facts = _run_text_profile(
                inputs,
                environment_id,
                selected,
                work / selected.value,
            )
            observations.extend(observed)
            profile_facts[selected.value] = facts
        rich_formats: tuple[str, ...] = ()
        rich_details: dict[str, JsonValue] = {}
        if profile in {BenchmarkProfile.REFERENCE, BenchmarkProfile.FULL}:
            if rich_parsers is None:  # pragma: no cover - guarded by profile selection above
                raise ValueError("rich parser preflight missing")
            rich_observations, rich_formats, rich_details = _run_rich(
                root,
                inputs,
                environment_id,
                work / "rich",
                parsers=rich_parsers,
            )
            observations.extend(rich_observations)
        summaries = _summaries(inputs, observations)
        decision_metrics = _derive_decision_metrics(
            profile=profile,
            profile_facts=profile_facts,
            rich_formats=rich_formats,
            observations=observations,
            summaries=summaries,
        )
        try:
            from scripts.product_benchmark_evaluation import decide_value
        except ModuleNotFoundError:
            from product_benchmark_evaluation import decide_value

        decision = decide_value(inputs, decision_metrics)
        observation_value = [item.model_dump(mode="json") for item in observations]
        summary_value: dict[str, JsonValue] = {
            "benchmark_version": _RUN_VERSION,
            "decision_metrics": cast(dict[str, JsonValue], decision_metrics),
            "environment": environment_value,
            "environment_id": environment_id,
            "profile": profile.value,
            "profile_facts": cast(dict[str, JsonValue], profile_facts),
            "rich": rich_details,
            "summaries": [item.model_dump(mode="json") for item in summaries],
        }
        # Render every projection from the same canonical JSON-normalized value
        # that readers validate (JCS normalizes integral floats to integers).
        summary_value = cast(dict[str, JsonValue], json.loads(canonical_json_bytes(summary_value)))
        _atomic_write(
            temporary / "observations.json",
            canonical_json_bytes(cast(JsonValue, observation_value)) + b"\n",
        )
        _atomic_write(temporary / "summary.json", canonical_json_bytes(summary_value) + b"\n")
        _atomic_write(
            temporary / "decision.json",
            canonical_json_bytes(decision.model_dump(mode="json")) + b"\n",
        )
        _atomic_write(temporary / "report.md", _render_report(summary_value, decision).encode())
        shutil.rmtree(work)
        duration_ns = time.monotonic_ns() - started_ns
        if duration_ns > inputs.protocol.resource_limits.maximum_run_seconds * 1_000_000_000:
            raise ValueError("benchmark run exceeded time limit")
        manifest: dict[str, JsonValue] = {
            "benchmark_version": _RUN_VERSION,
            "corpus_id": inputs.corpus_id,
            "duration_ns": duration_ns,
            "environment_id": environment_id,
            "files": [
                _manifest_entry(temporary / name)
                for name in _RESULT_NAMES
                if name != "run-manifest.json"
            ],
            "judgments_id": inputs.judgments_id,
            "policy_id": inputs.policy_id,
            "profile": profile.value,
            "protocol_id": inputs.protocol_id,
        }
        manifest["run_id"] = canonical_sha256(manifest)
        _atomic_write(temporary / "run-manifest.json", canonical_json_bytes(manifest) + b"\n")
        result_bytes = sum((temporary / name).stat().st_size for name in _RESULT_NAMES)
        if result_bytes > inputs.protocol.resource_limits.maximum_result_bytes:
            raise ValueError("benchmark result exceeds output limit")
        os.replace(temporary, output)
        return ProductBenchmarkResult(output, decision, tuple(observations), summaries)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)
        raise


def validate_product_benchmark(repository_root: Path, output: Path) -> ProductBenchmarkResult:
    """Validate published identities, hashes, summaries, decision and report drift."""
    root = repository_root.resolve(strict=True)
    inputs = load_benchmark_inputs(root / "benchmarks/product-value/v0.1.0")
    if output.is_symlink() or not output.is_dir():
        raise ValueError("benchmark output must be a regular directory")
    names = tuple(sorted(path.name for path in output.iterdir()))
    if names != _RESULT_NAMES:
        raise ValueError("benchmark result inventory is incomplete or unexpected")
    maximum = inputs.protocol.resource_limits.maximum_result_bytes
    if any(
        (output / name).is_symlink()
        or not (output / name).is_file()
        or (output / name).stat().st_size > maximum
        for name in names
    ):
        raise ValueError("benchmark result file is unsafe")
    files = {name: (output / name).read_bytes() for name in names}
    if sum(len(value) for value in files.values()) > maximum:
        raise ValueError("benchmark result exceeds output limit")
    forbidden = (b"/Users/", b"C:\\Users\\", b"umutgoksular", b"needle-")
    if any(marker in value for marker in forbidden for value in files.values()):
        raise ValueError("benchmark result contains a forbidden privacy value")

    manifest_value = _load_result_json(output / "run-manifest.json", maximum_bytes=maximum)
    if not isinstance(manifest_value, dict):
        raise ValueError("benchmark manifest is malformed")
    manifest = dict(manifest_value)
    run_id = manifest.pop("run_id", None)
    if run_id != canonical_sha256(manifest):
        raise ValueError("benchmark run identity mismatch")
    if set(manifest) != {
        "benchmark_version",
        "corpus_id",
        "duration_ns",
        "environment_id",
        "files",
        "judgments_id",
        "policy_id",
        "profile",
        "protocol_id",
    }:
        raise ValueError("benchmark manifest members are unexpected")
    if (
        manifest["benchmark_version"] != _RUN_VERSION
        or manifest["protocol_id"] != inputs.protocol_id
        or manifest["corpus_id"] != inputs.corpus_id
        or manifest["judgments_id"] != inputs.judgments_id
        or manifest["policy_id"] != inputs.policy_id
    ):
        raise ValueError("benchmark manifest input binding mismatch")
    duration = manifest["duration_ns"]
    if (
        isinstance(duration, bool)
        or not isinstance(duration, int)
        or duration < 0
        or duration > inputs.protocol.resource_limits.maximum_run_seconds * 1_000_000_000
    ):
        raise ValueError("benchmark duration is outside the frozen limit")
    raw_entries = manifest["files"]
    if not isinstance(raw_entries, list):
        raise ValueError("benchmark file inventory is malformed")
    entries: list[dict[str, JsonValue]] = []
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict):
            raise ValueError("benchmark file inventory row is malformed")
        entries.append(raw_entry)
    if {cast(str, item.get("name")) for item in entries} != set(names) - {"run-manifest.json"}:
        raise ValueError("benchmark file inventory is incomplete")
    for entry in entries:
        path = output / cast(str, entry["name"])
        if _manifest_entry(path) != entry:
            raise ValueError("benchmark result digest mismatch")

    raw_observations = _load_result_json(output / "observations.json", maximum_bytes=maximum)
    if not isinstance(raw_observations, list) or not raw_observations:
        raise ValueError("benchmark observations are malformed")
    observations = tuple(
        BenchmarkObservation.model_validate_json(canonical_json_bytes(item))
        for item in raw_observations
    )
    if len({item.observation_id for item in observations}) != len(observations):
        raise ValueError("benchmark observation identities are duplicate")
    expected_binding = (
        inputs.protocol_id,
        inputs.corpus_id,
        inputs.policy_id,
        manifest["environment_id"],
    )
    if any(
        (item.protocol_id, item.corpus_id, item.policy_id, item.environment_id) != expected_binding
        for item in observations
    ):
        raise ValueError("benchmark observation binding mismatch")
    if any(
        item.metric is BenchmarkMetric.WORKSPACE_BYTES
        and item.status is ObservationStatus.PASSED
        and cast(int, item.value) > inputs.protocol.resource_limits.maximum_workspace_bytes
        for item in observations
    ):
        raise ValueError("benchmark workspace exceeded frozen limit")

    summary_json = _load_result_json(output / "summary.json", maximum_bytes=maximum)
    if not isinstance(summary_json, dict) or set(summary_json) != {
        "benchmark_version",
        "decision_metrics",
        "environment",
        "environment_id",
        "profile",
        "profile_facts",
        "rich",
        "summaries",
    }:
        raise ValueError("benchmark summary is malformed")
    raw_summary = summary_json
    if (
        raw_summary["benchmark_version"] != _RUN_VERSION
        or raw_summary["environment_id"] != manifest["environment_id"]
        or canonical_sha256(raw_summary["environment"]) != manifest["environment_id"]
        or raw_summary["profile"] != manifest["profile"]
    ):
        raise ValueError("benchmark summary binding mismatch")
    raw_summaries = raw_summary["summaries"]
    if not isinstance(raw_summaries, list):
        raise ValueError("benchmark timing summaries are malformed")
    summaries = tuple(
        MetricSummary.model_validate_json(canonical_json_bytes(item)) for item in raw_summaries
    )
    recomputed = _summaries(inputs, observations)
    if summaries != recomputed:
        raise ValueError("benchmark summaries drifted from observations")

    raw_profile_facts = raw_summary["profile_facts"]
    raw_rich = raw_summary["rich"]
    if not isinstance(raw_profile_facts, dict) or not isinstance(raw_rich, dict):
        raise ValueError("benchmark aggregate facts are malformed")
    profile_facts: dict[str, dict[str, JsonValue]] = {}
    for key, value in raw_profile_facts.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            raise ValueError("benchmark profile facts are malformed")
        profile_facts[key] = value
        workspace_bytes = value.get("workspace_bytes")
        if isinstance(workspace_bytes, int) and (
            workspace_bytes > inputs.protocol.resource_limits.maximum_workspace_bytes
        ):
            raise ValueError("benchmark workspace exceeded frozen limit")
    rich_formats = tuple(
        key
        for key, value in raw_rich.items()
        if isinstance(key, str) and isinstance(value, dict) and value.get("available") is True
    )
    try:
        profile = BenchmarkProfile(cast(str, raw_summary["profile"]))
    except ValueError as error:
        raise ValueError("benchmark profile is unsupported") from error
    derived_metrics = _derive_decision_metrics(
        profile=profile,
        profile_facts=profile_facts,
        rich_formats=rich_formats,
        observations=observations,
        summaries=summaries,
    )
    if canonical_json_bytes(cast(JsonValue, derived_metrics)) != canonical_json_bytes(
        raw_summary["decision_metrics"]
    ):
        raise ValueError("benchmark decision metrics drifted from raw evidence")

    decision_bytes = output / "decision.json"
    _load_result_json(decision_bytes, maximum_bytes=maximum)
    decision = ValueDecision.model_validate_json(decision_bytes.read_bytes())
    try:
        from scripts.product_benchmark_evaluation import decide_value
    except ModuleNotFoundError:
        from product_benchmark_evaluation import decide_value

    if not isinstance(raw_summary["decision_metrics"], dict):
        raise ValueError("benchmark decision metrics are malformed")
    recomputed_decision = decide_value(inputs, raw_summary["decision_metrics"])
    if decision != recomputed_decision:
        raise ValueError("benchmark decision drifted from metrics")
    if (output / "report.md").read_text(encoding="utf-8") != _render_report(raw_summary, decision):
        raise ValueError("benchmark report drifted from evidence")
    return ProductBenchmarkResult(output, decision, observations, summaries)


__all__ = [
    "ProductBenchmarkResult",
    "execute_product_benchmark",
    "validate_product_benchmark",
]
